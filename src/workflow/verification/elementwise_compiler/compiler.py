"""One-command compiler from an explicit Neon/RVV C pair to frozen artifacts."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
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

from .capability_registry import verify_capability_refs
from .emit import EmittedStack, emit_stack
from .external_conditions import (
    ExternalConditionRequest,
    audit_external_condition,
    audit_local_unconditional_claim,
    source_pair_sha256,
)
from .intrinsics import ResolvedIntrinsicSet, resolve_intrinsics
from .recognize import PairRecognition, recognize_pair
from .schema import (
    Architecture,
    ArtifactKind,
    GeneratedArtifact,
    ExternalConditionEvidence,
    ExternalConditionRef,
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
    external_condition: ExternalConditionRequest | None = None

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
    external_condition: ExternalConditionEvidence


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


def _module_path(source_root: Path, module: str) -> Path | None:
    """Resolve a repository Python module without importing mutable code."""

    relative = Path(*module.split("."))
    module_path = (source_root / relative).with_suffix(".py")
    if module_path.is_file():
        return module_path
    package_path = source_root / relative / "__init__.py"
    return package_path if package_path.is_file() else None


def _module_name(source_root: Path, path: Path) -> str:
    relative = path.relative_to(source_root)
    parts = list(relative.with_suffix("").parts)
    if parts[-1] == "__init__":
        parts.pop()
    return ".".join(parts)


def _local_imports(source_root: Path, path: Path) -> set[Path]:
    """Return statically imported verification modules for one source file."""

    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except (OSError, UnicodeError, SyntaxError) as error:
        raise CompilerError(f"cannot inspect compiler dependency: {path}") from error
    current = _module_name(source_root, path)
    package = current if path.name == "__init__.py" else current.rpartition(".")[0]
    discovered: set[Path] = set()

    def add(module: str) -> None:
        if not module.startswith("workflow.verification"):
            return
        resolved = _module_path(source_root, module)
        if resolved is not None:
            discovered.add(resolved)

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                package_parts = package.split(".") if package else []
                keep = len(package_parts) - (node.level - 1)
                if keep < 0:
                    raise CompilerError(f"invalid relative import in {path}")
                prefix = ".".join(package_parts[:keep])
                base = ".".join(filter(None, (prefix, node.module or "")))
            else:
                base = node.module or ""
            add(base)
            for alias in node.names:
                add(".".join(filter(None, (base, alias.name))))
    return discovered


def _compiler_dependencies(root: Path) -> tuple[Path, ...]:
    """Compute the exact static Python closure that can generate the stack.

    Proof search, counterexample search, corpus orchestration, and result
    publication are deliberately outside this closure. Editing those consumers
    must not invalidate a generated ProgramManifest.
    """

    source_root = root / "src"
    entry = source_root / "workflow/verification/elementwise_compiler/compiler.py"
    if not entry.is_file():
        raise CompilerError(f"compiler dependency is absent: {entry}")
    pending = [entry]
    # Importing a submodule executes each existing package initializer first.
    relative = entry.relative_to(source_root)
    for depth in range(1, len(relative.parts) - 1):
        initializer = source_root.joinpath(*relative.parts[:depth], "__init__.py")
        if initializer.is_file():
            pending.append(initializer)
    dependencies: set[Path] = set()
    while pending:
        path = pending.pop()
        if path in dependencies:
            continue
        dependencies.add(path)
        pending.extend(_local_imports(source_root, path) - dependencies)
    return tuple(sorted(dependencies, key=lambda path: path.relative_to(root).as_posix()))


def _compiler_digest(root: Path) -> str:
    records = []
    for path in _compiler_dependencies(root):
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
    sources = (
        _source_artifact(neon, Architecture.NEON, root),
        _source_artifact(rvv, Architecture.RVV, root),
    )
    source_binding = source_pair_sha256(sources)
    if request.external_condition is not None:
        external_condition = audit_external_condition(
            root,
            (request.neon_source, request.rvv_source),
            source_binding,
            request.external_condition,
        )
    else:
        external_condition = audit_local_unconditional_claim(
            root,
            (request.neon_source, request.rvv_source),
            source_binding,
            (request.neon_function, request.rvv_function),
        )
    external_ref = ExternalConditionRef(
        "ExternalCondition.json",
        external_condition.sha256,
        external_condition.status,
    )
    manifest = ProgramManifest(
        compiler_sha256=_compiler_digest(root),
        sources=sources,
        contracts=recognition.contracts,
        intrinsic_capabilities=intrinsics.refs,
        layout=recognition.layout,
        schedules=recognition.schedules,
        local_assertions=recognition.local_assertions,
        consumed_effects_sha256=recognition.consumed_effects_sha256,
        external_condition=external_ref,
    )
    stack = emit_stack(
        neon,
        rvv,
        recognition,
        manifest,
        namespace=request.namespace,
        neon_registry=intrinsics.neon_registry,
        rvv_registry=intrinsics.rvv_registry,
        external_condition=external_condition,
    )
    manifest_path = output / "ProgramManifest.json"
    models_path = output / "Models.lean"
    spec_path = output / "Spec.lean"
    _atomic_write(manifest_path, canonical_json(manifest.to_record(), pretty=True))
    _atomic_write(
        output / "ExternalCondition.json",
        canonical_json(external_condition.to_record(), pretty=True),
    )
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
    capability_refs = tuple(
        sorted(
            (
                *intrinsics.refs,
                recognition.layout_capability.ref,
                *(item.ref for item in recognition.schedule_capabilities),
            ),
            key=lambda item: (item.capability_id, item.version, item.sha256),
        )
    )
    verify_capability_refs(root, capability_refs)
    legacy_capabilities = output / "Capabilities"
    if legacy_capabilities.exists():
        if not legacy_capabilities.is_dir():
            raise CompilerError("legacy Capabilities output is not a directory")
        shutil.rmtree(legacy_capabilities)
    index = {
        "artifact_kind": "elementwise-generated-stack",
        "schema_version": 2,
        "namespace": request.namespace,
        "target_claim": stack.target_theorem,
        "manifest": {
            "path": "ProgramManifest.json",
            "sha256": manifest.sha256,
        },
        "models": models.to_record(),
        "spec": spec.to_record(),
        "capabilities": [item.to_record() for item in capability_refs],
    }
    index["external_condition"] = {
        "path": "ExternalCondition.json",
        "sha256": external_condition.sha256,
        "status": external_condition.status.value,
    }
    index["stack_sha256"] = canonical_sha256(index)
    artifact_index_path = output / "ArtifactIndex.json"
    _atomic_write(artifact_index_path, canonical_json(index, pretty=True))
    compilation = Compilation(
        manifest,
        recognition,
        intrinsics,
        stack,
        manifest_path,
        models,
        spec,
        artifact_index_path,
        external_condition,
    )
    # Multi-phase consistency is a mandatory compiler audit, not a corpus-only
    # post-processing step.  The lazy import avoids a module cycle with proof.py.
    from .counterexamples import audit_cross_phase

    audit_cross_phase(root, compilation)
    return compilation


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
    parser.add_argument("--external-upstream-root", type=Path)
    parser.add_argument("--external-registration", type=Path)
    arguments = parser.parse_args(argv)
    if (arguments.external_upstream_root is None) != (
        arguments.external_registration is None
    ):
        parser.error(
            "--external-upstream-root and --external-registration must be provided together"
        )
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
            external_condition=(
                ExternalConditionRequest(
                    arguments.external_upstream_root,
                    arguments.external_registration,
                )
                if arguments.external_upstream_root is not None
                and arguments.external_registration is not None
                else None
            ),
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
