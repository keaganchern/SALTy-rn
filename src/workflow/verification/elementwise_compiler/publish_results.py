"""Publish a minimal, validated result projection from the ignored build tree."""

from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from .schema import (
    CounterexampleWitness,
    ExternalConditionEvidence,
    ExternalConditionStatus,
    Result,
    ResultStatus,
    canonical_json,
    canonical_sha256,
)


class PublishResultsError(RuntimeError):
    """The build tree is incomplete, inconsistent, or contains stale files."""


_COMMON_FILES = frozenset(
    {
        "ArtifactIndex.json",
        "CrossPhaseAudit.json",
        "ExternalCondition.json",
        "Models.lean",
        "ProgramManifest.json",
        "ProgramStatus.json",
        "Spec.lean",
    }
)
_PROOF_FILES = frozenset({"Proof.lean", "ProofTask.json", "Result.json"})
_COUNTEREXAMPLE_FILES = frozenset(
    {"Counterexample.lean", "Counterexample.json", "Result.json"}
)


def _json_object(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise PublishResultsError(f"cannot read JSON artifact {path}: {error}") from error
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise PublishResultsError(f"JSON artifact is not an object: {path}")
    return value


def _check_content_digest(record: Mapping[str, Any], field: str, subject: str) -> None:
    unsigned = dict(record)
    stored = unsigned.pop(field, None)
    if stored != canonical_sha256(unsigned):
        raise PublishResultsError(f"{subject} digest disagrees with its contents")


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


def _counterexample_summary(witness: CounterexampleWitness, relative_path: str) -> dict[str, Any]:
    return {
        "path": relative_path,
        "sha256": witness.sha256,
        "claim": witness.claim,
        "parameters": dict(witness.parameter_values),
        "inputs": list(witness.input_values),
        "left_output": witness.left_output,
        "right_output": witness.right_output,
    }


def _final_status(
    program_id: str,
    source: Path,
    status: dict[str, Any],
) -> tuple[dict[str, Any], frozenset[str]]:
    if status.get("program_id") != program_id:
        raise PublishResultsError(f"program status identity mismatch: {program_id}")
    if status.get("artifact_index") is None:
        if status.get("status") != ResultStatus.LAYOUT_UNRECOGNIZED.value:
            raise PublishResultsError(f"deferred program has an invalid status: {program_id}")
        return status, frozenset({"ProgramStatus.json"})

    result_path = source / "Result.json"
    if result_path.is_file():
        result = Result.from_record(_json_object(result_path))
        status["status"] = result.status.value
        status["status_layer"] = "lean-checked-terminal"
        status["detail"] = result.detail
        if result.status is ResultStatus.VERIFIED_VALUE:
            status["counterexample"] = None
            return status, _COMMON_FILES | _PROOF_FILES
        if result.status is ResultStatus.COUNTEREXAMPLE:
            witness = CounterexampleWitness.from_record(
                _json_object(source / "Counterexample.json")
            )
            if result.counterexample_sha256 != witness.sha256:
                raise PublishResultsError(
                    f"counterexample Result binding is invalid: {program_id}"
                )
            status["counterexample"] = _counterexample_summary(
                witness, f"programs/{program_id}/Counterexample.json"
            )
            return status, _COMMON_FILES | _COUNTEREXAMPLE_FILES
        raise PublishResultsError(
            f"published Result has a non-terminal status: {program_id}"
        )

    external = ExternalConditionEvidence.from_record(
        _json_object(source / "ExternalCondition.json")
    )
    if external.status is not ExternalConditionStatus.REQUIRED_MISSING:
        raise PublishResultsError(
            f"program has neither a terminal result nor an external blocker: {program_id}"
        )
    status["status"] = ResultStatus.EXTERNAL_CONDITION_MISSING.value
    status["status_layer"] = "typed-generated"
    status["detail"] = external.detail
    status["counterexample"] = None
    return status, _COMMON_FILES


def publish_curated_results(
    build_root: str | Path,
    destination_root: str | Path,
) -> dict[str, Any]:
    """Validate the full build and replace the curated projection atomically."""

    source = Path(build_root).resolve()
    destination = Path(destination_root).resolve()
    report = _json_object(source / "CorpusReport.json")
    registry = _json_object(source / "CapabilityRegistry.json")
    _check_content_digest(report, "report_sha256", "corpus report")
    _check_content_digest(registry, "registry_sha256", "capability registry")
    programs = report.get("programs")
    if not isinstance(programs, list) or len(programs) != 20:
        raise PublishResultsError("corpus report must contain exactly 20 discovered programs")

    staged = Path(
        tempfile.mkdtemp(prefix=f".{destination.name}.", dir=destination.parent)
    )
    published_programs: list[dict[str, Any]] = []
    program_file_count = 0
    try:
        shutil.copy2(source / "CapabilityRegistry.json", staged / "CapabilityRegistry.json")
        for reported in programs:
            if not isinstance(reported, dict) or not isinstance(
                reported.get("program_id"), str
            ):
                raise PublishResultsError("corpus report contains a malformed program")
            program_id = reported["program_id"]
            source_program = source / "programs" / program_id
            if not source_program.is_dir():
                raise PublishResultsError(f"program output is absent: {program_id}")
            if any(path.is_dir() for path in source_program.iterdir()):
                raise PublishResultsError(
                    f"program output contains a nested directory: {program_id}"
                )
            status, expected = _final_status(
                program_id,
                source_program,
                _json_object(source_program / "ProgramStatus.json"),
            )
            actual = frozenset(path.name for path in source_program.iterdir() if path.is_file())
            if actual != expected:
                raise PublishResultsError(
                    f"program file set is stale: {program_id}; "
                    f"missing={sorted(expected - actual)!r}, extra={sorted(actual - expected)!r}"
                )
            target_program = staged / "programs" / program_id
            target_program.mkdir(parents=True)
            for name in sorted(expected - {"ProgramStatus.json"}):
                shutil.copy2(source_program / name, target_program / name)
            _atomic_write(
                target_program / "ProgramStatus.json",
                canonical_json(status, pretty=True),
            )
            published = dict(status)
            published["program_status"] = f"programs/{program_id}/ProgramStatus.json"
            published_programs.append(published)
            program_file_count += len(expected)

        outcome_counts = Counter(str(item["status"]) for item in published_programs)
        scalar_counts = {
            status: outcome_counts[status]
            for status in (
                ResultStatus.VERIFIED_VALUE.value,
                ResultStatus.COUNTEREXAMPLE.value,
                ResultStatus.EXTERNAL_CONDITION_MISSING.value,
            )
        }
        if scalar_counts != {
            ResultStatus.VERIFIED_VALUE.value: 2,
            ResultStatus.COUNTEREXAMPLE.value: 10,
            ResultStatus.EXTERNAL_CONDITION_MISSING.value: 7,
        }:
            raise PublishResultsError(
                f"unexpected scalar outcome split: {scalar_counts!r}"
            )
        if outcome_counts[ResultStatus.LAYOUT_UNRECOGNIZED.value] != 1:
            raise PublishResultsError("expected exactly one deferred grouped-layout program")
        if program_file_count != 170:
            raise PublishResultsError(
                f"curated program projection must contain 170 files, got {program_file_count}"
            )

        report.pop("report_sha256", None)
        report["programs"] = published_programs
        report["status_counts"] = dict(sorted(outcome_counts.items()))
        report["scalar_outcome_counts"] = scalar_counts
        report["counterexample_count"] = scalar_counts[ResultStatus.COUNTEREXAMPLE.value]
        report["report_sha256"] = canonical_sha256(report)
        _atomic_write(staged / "CorpusReport.json", canonical_json(report, pretty=True))

        if destination.exists():
            if not destination.is_dir():
                raise PublishResultsError("curated result destination is not a directory")
            shutil.rmtree(destination)
        staged.replace(destination)
    finally:
        if staged.exists():
            shutil.rmtree(staged)
    return {
        "program_file_count": program_file_count,
        "scalar_outcome_counts": scalar_counts,
        "deferred_grouped_layout": 1,
        "report_sha256": report["report_sha256"],
    }


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--build-root", type=Path, required=True)
    parser.add_argument("--destination-root", type=Path, required=True)
    arguments = parser.parse_args(argv)
    result = publish_curated_results(arguments.build_root, arguments.destination_root)
    print(canonical_json(result))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
