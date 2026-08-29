"""One-command compiler from an explicit Neon/RVV C pair to frozen artifacts."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence

from workflow.verification.lean_backend.frontend import (
    KernelExtraction,
    parse_kernel_explicit,
)
from workflow.verification.lean_backend.intrinsic_index import (
    CANONICAL_INTRINSIC_INDEX,
    CanonicalIntrinsicIndex,
)
from workflow.verification.lean_backend.schema import Architecture as BackendArchitecture

from .capabilities import IntrinsicCapability
from .emit import EmittedStack, emit_stack
from .intrinsics import ResolvedIntrinsicSet, resolve_intrinsics
from .recognize import PairRecognition, recognize_pair
from .schema import (
    Architecture,
    ArtifactKind,
    GeneratedArtifact,
    ProgramManifest,
    SourceArtifact,
    canonical_json,
    canonical_sha256,
)


class CompilerError(RuntimeError):
    """The artifact compiler cannot complete its fail-closed pipeline."""


@dataclass(frozen=True, slots=True)
class CompilerRequest:
    repository_root: Path
    neon_source: Path
    rvv_source: Path
    neon_function: str
    rvv_function: str
    neon_facade: Path
    rvv_facade: Path
    neon_target: str
    rvv_target: str
    namespace: str
    output_directory: Path
    clang: str = "clang"

    def __post_init__(self) -> None:
        for value, label in (
            (self.neon_function, "Neon function"),
            (self.rvv_function, "RVV function"),
            (self.neon_target, "Neon target"),
            (self.rvv_target, "RVV target"),
            (self.namespace, "Lean namespace"),
            (self.clang, "Clang executable"),
        ):
            if not value or value.strip() != value:
                raise CompilerError(f"{label} must be explicitly provided")
        if re.fullmatch(
            r"[A-Za-z_][A-Za-z0-9_']*(?:\.[A-Za-z_][A-Za-z0-9_']*)*",
            self.namespace,
        ) is None:
            raise CompilerError(f"invalid Lean namespace {self.namespace!r}")


@dataclass(frozen=True, slots=True)
class Compilation:
    manifest: ProgramManifest
    recognition: PairRecognition
    intrinsics: ResolvedIntrinsicSet
    stack: EmittedStack
    manifest_path: Path
    models: GeneratedArtifact
    spec: GeneratedArtifact
    artifact_index_path: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _relative(path: Path, root: Path, field: str) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise CompilerError(f"{field} must be inside repository root: {path}") from error


def _compiler_digest(root: Path) -> str:
    package = root / "src/workflow/verification/elementwise_compiler"
    dependencies = [
        root / "src/workflow/verification/lean_backend/frontend.py",
        root / "src/workflow/verification/lean_backend/case_emit.py",
        root / "src/workflow/verification/lean_backend/emit_lean.py",
        root / "src/workflow/verification/lean_backend/model_profiles.py",
        root / "src/workflow/verification/lean_backend/intrinsic_index.py",
        root / "src/workflow/verification/lean_backend/descriptor.py",
        root / "src/workflow/verification/lean_backend/schema.py",
    ]
    dependencies.extend(sorted(package.glob("*.py")))
    records = []
    for path in dependencies:
        if not path.is_file():
            raise CompilerError(f"compiler dependency is absent: {path}")
        records.append({"path": _relative(path, root, "compiler dependency"), "sha256": _sha256(path)})
    return canonical_sha256(records)


def _source_artifact(
    extraction: KernelExtraction,
    architecture: Architecture,
    repository_root: Path,
) -> SourceArtifact:
    return SourceArtifact(
        architecture,
        _relative(Path(extraction.source_path), repository_root, "source"),
        extraction.function_name,
        extraction.source_sha256,
        _relative(Path(extraction.facade_path), repository_root, "facade"),
        extraction.facade_sha256,
        extraction.preprocessed_sha256,
    )


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        temporary.replace(path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


def _capability_filename(capability_id: str, sha256: str) -> str:
    stem = re.sub(r"[^A-Za-z0-9_.-]+", "_", capability_id)
    return f"{stem}-{sha256[:16]}.json"


def _write_capabilities(
    output: Path,
    intrinsics: tuple[IntrinsicCapability, ...],
    recognition: PairRecognition,
) -> tuple[dict[str, str], ...]:
    documents = [
        *(capability.to_record() for capability in intrinsics),
        recognition.layout_capability.to_record(),
        *(capability.to_record() for capability in recognition.schedule_capabilities),
    ]
    records: list[dict[str, str]] = []
    for document in sorted(documents, key=lambda item: str(item["capability_id"])):
        digest = str(document["capability_sha256"])
        relative = Path("Capabilities") / _capability_filename(
            str(document["capability_id"]), digest
        )
        _atomic_write(output / relative, canonical_json(document, pretty=True))
        records.append(
            {
                "capability_id": str(document["capability_id"]),
                "path": relative.as_posix(),
                "sha256": digest,
            }
        )
    return tuple(records)


def _parse(request: CompilerRequest) -> tuple[KernelExtraction, KernelExtraction]:
    neon = parse_kernel_explicit(
        request.neon_source,
        architecture=BackendArchitecture.NEON,
        function_name=request.neon_function,
        facade=request.neon_facade,
        target_triple=request.neon_target,
        clang=request.clang,
    )
    rvv = parse_kernel_explicit(
        request.rvv_source,
        architecture=BackendArchitecture.RVV,
        function_name=request.rvv_function,
        facade=request.rvv_facade,
        target_triple=request.rvv_target,
        clang=request.clang,
    )
    return neon, rvv


def compile_pair(
    request: CompilerRequest,
    *,
    intrinsic_index: CanonicalIntrinsicIndex = CANONICAL_INTRINSIC_INDEX,
) -> Compilation:
    root = request.repository_root.resolve()
    output = request.output_directory.resolve()
    neon, rvv = _parse(request)
    recognition = recognize_pair(neon, rvv, repository_root=root)
    intrinsics = resolve_intrinsics(
        neon,
        rvv,
        repository_root=root,
        index=intrinsic_index,
    )
    manifest = ProgramManifest(
        compiler_sha256=_compiler_digest(root),
        sources=(
            _source_artifact(neon, Architecture.NEON, root),
            _source_artifact(rvv, Architecture.RVV, root),
        ),
        contracts=recognition.contracts,
        intrinsic_capabilities=intrinsics.refs,
        layout=recognition.layout,
        schedules=recognition.schedules,
        local_assertions=recognition.local_assertions,
        consumed_effects_sha256=recognition.consumed_effects_sha256,
    )
    stack = emit_stack(
        neon,
        rvv,
        recognition,
        manifest,
        namespace=request.namespace,
        neon_registry=intrinsics.neon_registry,
        rvv_registry=intrinsics.rvv_registry,
    )
    manifest_path = output / "ProgramManifest.json"
    models_path = output / "Models.lean"
    spec_path = output / "Spec.lean"
    _atomic_write(manifest_path, canonical_json(manifest.to_record(), pretty=True))
    _atomic_write(models_path, stack.models_text)
    models = GeneratedArtifact(
        ArtifactKind.MODELS,
        "Models.lean",
        _sha256(models_path),
        manifest.sha256,
    )
    _atomic_write(spec_path, stack.spec_text)
    spec = GeneratedArtifact(
        ArtifactKind.SPEC,
        "Spec.lean",
        _sha256(spec_path),
        models.sha256,
    )
    capabilities = _write_capabilities(output, intrinsics.capabilities, recognition)
    index = {
        "artifact_kind": "elementwise-generated-stack",
        "schema_version": 1,
        "namespace": request.namespace,
        "manifest": {
            "path": "ProgramManifest.json",
            "sha256": manifest.sha256,
        },
        "models": models.to_record(),
        "spec": spec.to_record(),
        "capabilities": list(capabilities),
    }
    index["stack_sha256"] = canonical_sha256(index)
    artifact_index_path = output / "ArtifactIndex.json"
    _atomic_write(artifact_index_path, canonical_json(index, pretty=True))
    return Compilation(
        manifest,
        recognition,
        intrinsics,
        stack,
        manifest_path,
        models,
        spec,
        artifact_index_path,
    )


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--neon-source", type=Path, required=True)
    parser.add_argument("--rvv-source", type=Path, required=True)
    parser.add_argument("--neon-function", required=True)
    parser.add_argument("--rvv-function", required=True)
    parser.add_argument("--neon-facade", type=Path, required=True)
    parser.add_argument("--rvv-facade", type=Path, required=True)
    parser.add_argument("--neon-target", required=True)
    parser.add_argument("--rvv-target", required=True)
    parser.add_argument("--namespace", required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    parser.add_argument("--clang", default="clang")
    arguments = parser.parse_args(argv)
    result = compile_pair(
        CompilerRequest(
            repository_root=arguments.repository_root,
            neon_source=arguments.neon_source,
            rvv_source=arguments.rvv_source,
            neon_function=arguments.neon_function,
            rvv_function=arguments.rvv_function,
            neon_facade=arguments.neon_facade,
            rvv_facade=arguments.rvv_facade,
            neon_target=arguments.neon_target,
            rvv_target=arguments.rvv_target,
            namespace=arguments.namespace,
            output_directory=arguments.output_directory,
            clang=arguments.clang,
        )
    )
    print(
        json.dumps(
            {
                "manifest_sha256": result.manifest.sha256,
                "models_sha256": result.models.sha256,
                "spec_sha256": result.spec.sha256,
                "artifact_index": str(result.artifact_index_path),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
