"""Freeze, delegate, and check one generated elementwise Lean proof task.

The proof agent may create or replace only ``Proof.lean``.  Acceptance hashes the
protected artifact closure before and after Lean checking.  This is an integrity
gate; it is not an operating-system sandbox for the delegated process.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .lean_safety import FORBIDDEN_LEAN_IDENTIFIERS, strip_lean_comments_and_strings
from .capability_registry import verify_capability_refs
from .schema import (
    ArtifactKind,
    CapabilityRef,
    CounterexampleWitness,
    CrossPhaseAudit,
    CrossPhaseAuditStatus,
    ExternalConditionEvidence,
    ExternalConditionStatus,
    GeneratedArtifact,
    ProgramManifest,
    ProofTask,
    Result,
    ResultStatus,
    canonical_json,
    canonical_sha256,
)
from .external_conditions import source_pair_sha256, verify_external_condition
from .lean_check import (
    ALLOWED_AXIOMS,
    LeanCheckError,
    Toolchain as _Toolchain,
    _checked_axioms,
    _command,
    _compile,
    _resolve_toolchain,
    _stage,
)


_IDENTIFIER_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_']*")
ProofGateError = LeanCheckError


@dataclass(frozen=True, slots=True)
class ProofRun:
    task: ProofTask
    result: Result
    task_path: Path
    result_path: Path


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", dir=path.parent
    )
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


def _json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ProofGateError(f"cannot read canonical JSON {path}: {error}") from error
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ProofGateError(f"canonical JSON root must be an object: {path}")
    return value


def _checker_sha256() -> str:
    files = (
        Path(__file__),
        Path(__file__).with_name("schema.py"),
        Path(__file__).with_name("lean_safety.py"),
        Path(__file__).with_name("capability_registry.py"),
    )
    return canonical_sha256(
        {
            "files": [
                {"name": path.name, "sha256": _sha256(path.resolve())} for path in files
            ],
            "allowed_axioms": sorted(ALLOWED_AXIOMS),
            "forbidden_identifiers": sorted(FORBIDDEN_LEAN_IDENTIFIERS),
        }
    )


def _load_index(output: Path) -> dict[str, Any]:
    raw = dict(_json(output / "ArtifactIndex.json"))
    if raw.get("artifact_kind") != "elementwise-generated-stack":
        raise ProofGateError("ArtifactIndex is not an elementwise generated stack")
    stored = raw.pop("stack_sha256", None)
    if stored != canonical_sha256(raw):
        raise ProofGateError("ArtifactIndex stack digest disagrees with contents")
    raw["stack_sha256"] = stored
    return raw


def _write_index(output: Path, index: Mapping[str, Any]) -> None:
    record = dict(index)
    record.pop("stack_sha256", None)
    record["stack_sha256"] = canonical_sha256(record)
    _atomic_write(output / "ArtifactIndex.json", canonical_json(record, pretty=True))


def _artifact(index: Mapping[str, Any], key: str) -> GeneratedArtifact:
    value = index.get(key)
    if not isinstance(value, Mapping):
        raise ProofGateError(f"ArtifactIndex has no {key} artifact")
    return GeneratedArtifact.from_record(value)


def _verify_stack(
    repository_root: Path, output: Path, index: Mapping[str, Any]
) -> tuple[
    ProgramManifest,
    GeneratedArtifact,
    GeneratedArtifact,
    str,
    str,
    ExternalConditionEvidence,
    CrossPhaseAudit,
]:
    manifest = ProgramManifest.from_record(_json(output / "ProgramManifest.json"))
    manifest_index = index.get("manifest")
    if (
        not isinstance(manifest_index, Mapping)
        or manifest_index.get("sha256") != manifest.sha256
    ):
        raise ProofGateError("manifest identity differs from ArtifactIndex")
    models = _artifact(index, "models")
    spec = _artifact(index, "spec")
    if (
        models.parent_sha256 != manifest.sha256
        or _sha256(output / models.path) != models.sha256
    ):
        raise ProofGateError("Models artifact hash chain is invalid")
    if (
        spec.parent_sha256 != models.sha256
        or _sha256(output / spec.path) != spec.sha256
    ):
        raise ProofGateError("Spec artifact hash chain is invalid")
    namespace = index.get("namespace")
    if not isinstance(namespace, str) or not namespace:
        raise ProofGateError("ArtifactIndex has no Lean namespace")
    target_claim = index.get("target_claim")
    if not isinstance(target_claim, str) or re.fullmatch(
        r"[A-Za-z_][A-Za-z0-9_']*", target_claim
    ) is None:
        raise ProofGateError("ArtifactIndex has no valid generated target claim")
    external_index = index.get("external_condition")
    if not isinstance(external_index, Mapping):
        raise ProofGateError("ArtifactIndex has no mandatory external-condition audit")
    external_path = output / manifest.external_condition.path
    external = ExternalConditionEvidence.from_record(_json(external_path))
    if (
        external.sha256 != manifest.external_condition.sha256
        or external.status is not manifest.external_condition.status
        or external_index.get("path") != manifest.external_condition.path
        or external_index.get("sha256") != external.sha256
        or external_index.get("status") != external.status.value
    ):
        raise ProofGateError("external-condition identity differs from manifest/index")
    try:
        verify_external_condition(
            repository_root,
            tuple(repository_root / source.path for source in manifest.sources),
            source_pair_sha256(manifest.sources),
            external,
        )
    except (OSError, ValueError, RuntimeError) as error:
        raise ProofGateError(f"external-condition evidence failed: {error}") from error
    phase_index = index.get("cross_phase_audit")
    if not isinstance(phase_index, Mapping):
        raise ProofGateError("ArtifactIndex has no mandatory cross-phase audit")
    phase = CrossPhaseAudit.from_record(
        _json(output / str(phase_index.get("path", "")))
    )
    if (
        phase_index.get("sha256") != phase.sha256
        or phase_index.get("status") != phase.status.value
        or phase.manifest_sha256 != manifest.sha256
        or phase.models_sha256 != models.sha256
        or phase.spec_sha256 != spec.sha256
    ):
        raise ProofGateError("cross-phase audit identity differs from generated stack")
    counterexample_index = index.get("counterexample")
    if counterexample_index is not None:
        if not isinstance(counterexample_index, Mapping):
            raise ProofGateError("ArtifactIndex counterexample binding is malformed")
        counterexample_path = output / str(counterexample_index.get("path", ""))
        witness = CounterexampleWitness.from_record(_json(counterexample_path))
        lean_path = output / witness.lean_path
        if (
            counterexample_index.get("sha256") != witness.sha256
            or counterexample_index.get("lean_path") != witness.lean_path
            or counterexample_index.get("lean_sha256") != witness.lean_sha256
            or counterexample_index.get("claim") != witness.claim
            or witness.manifest_sha256 != manifest.sha256
            or witness.models_sha256 != models.sha256
            or witness.spec_sha256 != spec.sha256
            or not lean_path.is_file()
            or _sha256(lean_path) != witness.lean_sha256
        ):
            raise ProofGateError("counterexample identity differs from generated stack")
        result_index = index.get("result")
        if not isinstance(result_index, Mapping):
            raise ProofGateError("checked counterexample has no terminal Result binding")
        result = Result.from_record(_json(output / str(result_index.get("path", ""))))
        if (
            result.status is not ResultStatus.COUNTEREXAMPLE
            or result.counterexample_sha256 != witness.sha256
            or result_index.get("sha256") != result.sha256
            or result_index.get("status") != result.status.value
        ):
            raise ProofGateError("counterexample Result identity is invalid")
        phase_claim = f"{namespace}.neonPhaseFunctionsEqualClaim"
        complete_claim = f"{namespace}.{target_claim}"
        if witness.claim == phase_claim:
            if phase.status is not CrossPhaseAuditStatus.COUNTEREXAMPLE:
                raise ProofGateError(
                    "phase counterexample exists without matching cross-phase audit"
                )
        elif witness.claim == complete_claim:
            if phase.status is CrossPhaseAuditStatus.COUNTEREXAMPLE:
                raise ProofGateError(
                    "whole-program counterexample conflicts with phase witness"
                )
        else:
            raise ProofGateError("counterexample does not refute a generated claim")
    elif phase.status is CrossPhaseAuditStatus.COUNTEREXAMPLE:
        raise ProofGateError("cross-phase audit names a missing counterexample")
    raw_capabilities = index.get("capabilities")
    if not isinstance(raw_capabilities, list):
        raise ProofGateError("ArtifactIndex capabilities must be an array")
    try:
        capability_refs = tuple(
            CapabilityRef.from_record(item) for item in raw_capabilities
        )
        expected_refs = tuple(
            sorted(
                (
                    *manifest.intrinsic_capabilities,
                    manifest.layout.capability,
                    *(schedule.capability for schedule in manifest.schedules),
                ),
                key=lambda item: (item.capability_id, item.version, item.sha256),
            )
        )
        if capability_refs != expected_refs:
            raise ProofGateError(
                "ArtifactIndex capability references differ from the manifest"
            )
        verify_capability_refs(repository_root, capability_refs)
    except (TypeError, ValueError) as error:
        raise ProofGateError(f"global capability verification failed: {error}") from error
    return manifest, models, spec, namespace, target_claim, external, phase


def _checked_claim_encoding(
    repository_root: Path,
    output: Path,
    namespace: str,
    claim: str,
    toolchain: _Toolchain,
) -> str:
    temporary, stage, environment = _stage(
        repository_root, output, namespace, toolchain, include_proof=False
    )
    try:
        module_directory = stage.joinpath(*namespace.split("."))
        for name in ("Models.lean", "Spec.lean"):
            completed = _compile(
                toolchain, stage, environment, module_directory / name, emit_olean=True
            )
            if completed.returncode != 0:
                raise ProofGateError(
                    f"generated {name} did not elaborate:\n{completed.stdout}{completed.stderr}"
                )
        inspect = stage / "ElementwiseClaimInspect.lean"
        inspect.write_text(
            f"import {namespace}.Spec\n"
            f"#print {claim}\n",
            encoding="utf-8",
        )
        completed = _compile(toolchain, stage, environment, inspect, emit_olean=False)
        if (
            completed.returncode != 0
            or completed.stderr
            or not completed.stdout.strip()
        ):
            raise ProofGateError("Lean could not print the checked generated claim")
        return canonical_sha256(
            {
                "schema": "lean-checked-claim-v1",
                "module": f"{namespace}.Spec",
                "claim": claim,
                "printed_declaration": completed.stdout.strip(),
            }
        )
    finally:
        temporary.cleanup()


def _closure_files(output: Path, index: Mapping[str, Any]) -> tuple[Path, ...]:
    files = {
        output / "ArtifactIndex.json",
        output / "ProgramManifest.json",
        output / "Models.lean",
        output / "Spec.lean",
        output / "ProofTask.json",
        output / "CrossPhaseAudit.json",
    }
    external = index.get("external_condition")
    if external is not None:
        if not isinstance(external, Mapping) or not isinstance(external.get("path"), str):
            raise ProofGateError("ArtifactIndex external-condition binding is malformed")
        files.add(output / str(external["path"]))
    counterexample = index.get("counterexample")
    if counterexample is not None:
        if not isinstance(counterexample, Mapping):
            raise ProofGateError("ArtifactIndex counterexample binding is malformed")
        for key in ("path", "lean_path"):
            path = counterexample.get(key)
            if not isinstance(path, str):
                raise ProofGateError("ArtifactIndex counterexample path is malformed")
            files.add(output / path)
    if any(not path.is_file() for path in files):
        raise ProofGateError("protected proof-task closure is incomplete")
    return tuple(sorted(files))


def _closure_sha256(output: Path, index: Mapping[str, Any]) -> str:
    return canonical_sha256(
        [
            {"path": path.relative_to(output).as_posix(), "sha256": _sha256(path)}
            for path in _closure_files(output, index)
        ]
    )


def prepare_proof_task(
    repository_root: str | Path,
    output_directory: str | Path,
) -> ProofTask:
    """Elaborate the frozen claim and emit its content-addressed proof task."""

    repository = Path(repository_root).resolve()
    output = Path(output_directory).resolve()
    index = _load_index(output)
    manifest, models, spec, namespace, target_claim, external, phase = _verify_stack(
        repository, output, index
    )
    if index.get("counterexample") is not None:
        raise ProofGateError(
            "counterexample: a Lean-checked disagreement forbids proof delegation"
        )
    if (
        external is not None
        and external.status is ExternalConditionStatus.REQUIRED_MISSING
    ):
        raise ProofGateError(
            "external-condition-missing: proof task cannot use an unresolved input condition"
        )
    toolchain = _resolve_toolchain(repository)
    task = ProofTask(
        manifest_sha256=manifest.sha256,
        models=models,
        spec=spec,
        proof_path="Proof.lean",
        module=f"{namespace}.Proof",
        theorem=f"{namespace}.completeValueEquivalence",
        claim=f"{namespace}.{target_claim}",
        elaborated_type_sha256=_checked_claim_encoding(
            repository, output, namespace, f"{namespace}.{target_claim}", toolchain
        ),
        checker_policy_sha256=_checker_sha256(),
        toolchain_sha256=toolchain.sha256,
    )
    _atomic_write(
        output / "ProofTask.json", canonical_json(task.to_record(), pretty=True)
    )
    index["proof_task"] = {
        "path": "ProofTask.json",
        "sha256": task.sha256,
        "proof_path": task.proof_path,
    }
    index.pop("result", None)
    _write_index(output, index)
    return task


def _proof_tokens_are_safe(path: Path) -> bool:
    try:
        stripped = strip_lean_comments_and_strings(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, ValueError):
        return False
    return not (set(_IDENTIFIER_RE.findall(stripped)) & FORBIDDEN_LEAN_IDENTIFIERS)


def _write_result(output: Path, index: dict[str, Any], result: Result) -> Path:
    path = output / "Result.json"
    _atomic_write(path, canonical_json(result.to_record(), pretty=True))
    index["result"] = {
        "path": "Result.json",
        "sha256": result.sha256,
        "status": result.status.value,
    }
    _write_index(output, index)
    return path


def check_proof(
    repository_root: str | Path,
    output_directory: str | Path,
) -> ProofRun:
    """Check the exact frozen task and publish one terminal ``Result.json``."""

    repository = Path(repository_root).resolve()
    output = Path(output_directory).resolve()
    checker_sha = _checker_sha256()
    toolchain = _resolve_toolchain(repository)
    index = _load_index(output)
    task_path = output / "ProofTask.json"
    task: ProofTask
    try:
        manifest, models, spec, namespace, target_claim, external, phase = _verify_stack(
            repository, output, index
        )
        task = ProofTask.from_record(_json(task_path))
        task_index = index.get("proof_task")
        if (
            not isinstance(task_index, Mapping)
            or task_index.get("sha256") != task.sha256
        ):
            raise ProofGateError("ProofTask identity differs from ArtifactIndex")
        if (
            task.manifest_sha256 != manifest.sha256
            or task.models != models
            or task.spec != spec
            or task.claim != f"{namespace}.{target_claim}"
        ):
            raise ProofGateError("ProofTask parent chain differs from generated stack")
        if (
            task.checker_policy_sha256 != checker_sha
            or task.toolchain_sha256 != toolchain.sha256
        ):
            raise ProofGateError("ProofTask checker/toolchain identity is stale")
        checked_claim = _checked_claim_encoding(
            repository, output, namespace, task.claim, toolchain
        )
        if checked_claim != task.elaborated_type_sha256:
            raise ProofGateError(
                "checked generated claim differs from frozen ProofTask"
            )
        start = _closure_sha256(output, index)
    except (OSError, ValueError, ProofGateError) as error:
        placeholder = (
            ProofTask.from_record(_json(task_path)) if task_path.is_file() else None
        )
        result = Result(
            ResultStatus.GENERATION_FAILED,
            None if placeholder is None else placeholder.sha256,
            None,
            checker_sha,
            toolchain.sha256,
            None,
            None,
            f"frozen parent validation failed: {error}",
        )
        result_path = _write_result(output, index, result)
        if placeholder is None:
            raise ProofGateError(result.detail)
        return ProofRun(placeholder, result, task_path, result_path)

    proof_path = output / task.proof_path
    if not proof_path.is_file():
        result = Result(
            ResultStatus.PROOF_SEARCH_FAILED,
            task.sha256,
            None,
            checker_sha,
            toolchain.sha256,
            start,
            start,
            "designated Proof.lean is absent",
        )
        return ProofRun(task, result, task_path, _write_result(output, index, result))
    proof_sha = _sha256(proof_path)
    status = ResultStatus.LEAN_FAILED
    detail = "proof failed"
    if not _proof_tokens_are_safe(proof_path):
        detail = "proof contains a forbidden Lean escape identifier"
    else:
        temporary, stage, environment = _stage(
            repository, output, namespace, toolchain, include_proof=True
        )
        try:
            module_directory = stage.joinpath(*namespace.split("."))
            failure: str | None = None
            for name in ("Models.lean", "Spec.lean", "Proof.lean"):
                completed = _compile(
                    toolchain,
                    stage,
                    environment,
                    module_directory / name,
                    emit_olean=True,
                )
                if completed.returncode != 0:
                    failure = (
                        f"Lean rejected {name}:\n{completed.stdout}{completed.stderr}"
                    )
                    break
            if failure is None:
                audit = stage / "ElementwiseProofAudit.lean"
                claim = task.claim
                audit.write_text(
                    f"import {task.module}\n"
                    f"example : {claim} := {task.theorem}\n"
                    f"#print axioms {task.theorem}\n",
                    encoding="utf-8",
                )
                completed = _compile(
                    toolchain, stage, environment, audit, emit_olean=False
                )
                if completed.returncode != 0:
                    failure = f"Lean theorem audit failed:\n{completed.stdout}{completed.stderr}"
                else:
                    axioms = _checked_axioms(completed.stdout + completed.stderr)
                    unexpected = sorted(axioms - ALLOWED_AXIOMS)
                    if unexpected:
                        failure = f"proof depends on forbidden axioms {unexpected!r}"
            if failure is None:
                status = ResultStatus.VERIFIED_VALUE
                detail = "Lean accepted the frozen value claim and proof policy"
            else:
                detail = failure
        except ProofGateError as error:
            detail = str(error)
        finally:
            temporary.cleanup()
    try:
        _verify_stack(repository, output, index)
        end = _closure_sha256(output, index)
    except (OSError, ValueError, ProofGateError) as error:
        end = None
        status = ResultStatus.LEAN_FAILED
        detail = f"protected external/generated inputs changed: {error}"
    if end != start:
        status = ResultStatus.LEAN_FAILED
        detail = "protected artifact closure changed during proof checking"
    result = Result(
        status,
        task.sha256,
        proof_sha,
        checker_sha,
        toolchain.sha256,
        start,
        end,
        detail.strip() or "proof check failed without diagnostics",
    )
    return ProofRun(task, result, task_path, _write_result(output, index, result))


def run_proof_agent(
    repository_root: str | Path,
    output_directory: str | Path,
    command: Sequence[str],
) -> ProofRun:
    """Run an external proof command and accept only a ``Proof.lean`` change."""

    if not command:
        raise ProofGateError("proof-agent command must be non-empty")
    output = Path(output_directory).resolve()
    index = _load_index(output)
    task = ProofTask.from_record(_json(output / "ProofTask.json"))
    before = {
        path.relative_to(output).as_posix(): _sha256(path)
        for path in output.rglob("*")
        if path.is_file() and path.name not in {"Proof.lean", "Result.json"}
    }
    environment = {**os.environ, "SALTYRN_PROOF_TASK": str(output / "ProofTask.json")}
    completed = _command(command, cwd=output, environment=environment, timeout=600)
    after = {
        path.relative_to(output).as_posix(): _sha256(path)
        for path in output.rglob("*")
        if path.is_file() and path.name not in {"Proof.lean", "Result.json"}
    }
    if completed.returncode != 0 or before != after:
        checker = _checker_sha256()
        toolchain = _resolve_toolchain(Path(repository_root).resolve())
        closure = _closure_sha256(output, index) if before == after else None
        result = Result(
            ResultStatus.PROOF_SEARCH_FAILED,
            task.sha256,
            None,
            checker,
            toolchain.sha256,
            closure,
            closure,
            "proof agent failed or modified a protected artifact",
        )
        return ProofRun(
            task,
            result,
            output / "ProofTask.json",
            _write_result(output, index, result),
        )
    return check_proof(repository_root, output)


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    for operation in ("prepare", "check"):
        child = subparsers.add_parser(operation)
        child.add_argument("--repository-root", type=Path, required=True)
        child.add_argument("--output-directory", type=Path, required=True)
    run = subparsers.add_parser("run-agent")
    run.add_argument("--repository-root", type=Path, required=True)
    run.add_argument("--output-directory", type=Path, required=True)
    run.add_argument("command", nargs=argparse.REMAINDER)
    arguments = parser.parse_args(argv)
    if arguments.operation == "prepare":
        task = prepare_proof_task(arguments.repository_root, arguments.output_directory)
        print(canonical_json(task.to_record()))
        return 0
    if arguments.operation == "check":
        run_result = check_proof(arguments.repository_root, arguments.output_directory)
    else:
        command = tuple(arguments.command)
        if command[:1] == ("--",):
            command = command[1:]
        run_result = run_proof_agent(
            arguments.repository_root, arguments.output_directory, command
        )
    print(canonical_json(run_result.result.to_record()))
    return 0 if run_result.result.status is ResultStatus.VERIFIED_VALUE else 1


if __name__ == "__main__":
    raise SystemExit(_main())
