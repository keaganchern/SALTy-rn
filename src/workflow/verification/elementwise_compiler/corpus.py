"""Discover the scalar-layout elementwise corpus and publish live capability gaps.

Discovery is structural and never starts from a maintained list of case names.
Only programs that pass the typed compiler receive generated artifacts.  Programs
without a complete parse facade or intrinsic semantics remain explicit preflight
records; a lexical inventory is never reported as a proof.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from workflow.verification.lean_backend.frontend import FrontendError
from workflow.verification.lean_backend.intrinsic_index import (
    configured_intrinsic_occurrences,
)
from workflow.verification.lean_backend.schema import Architecture as BackendArchitecture

from .compiler import CompilerError, CompilerRequest, compile_pair
from .counterexamples import CounterexampleError, find_cross_phase_counterexample
from .emit import GenerationError
from .intrinsics import IntrinsicResolutionError
from .external_conditions import (
    ExternalConditionError,
    audit_external_condition,
    discover_request,
    raw_source_pair_sha256,
)
from .recognize import RecognitionError
from .schema import (
    ExternalConditionStatus,
    ResultStatus,
    canonical_json,
    canonical_sha256,
)


_FUNCTION_RE = re.compile(
    r"\bvoid\s+(?P<name>[A-Za-z_][A-Za-z0-9_]*)\s*\((?P<params>.*?)\)"
    r"(?:\s+XNN_[A-Za-z0-9_]+)*\s*\{",
    re.DOTALL,
)
_CALL_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\s*\(")
_ASSERT_RE = re.compile(r"\bassert\s*\((.*?)\)\s*;", re.DOTALL)
_CONTROL_WORDS = frozenset({"assert", "for", "if", "sizeof", "switch", "while"})


class CorpusError(RuntimeError):
    """The corpus or generated report is structurally inconsistent."""


@dataclass(frozen=True, slots=True)
class _Candidate:
    program_id: str
    neon_source: Path
    rvv_source: Path
    neon_function: str
    rvv_function: str
    grouped_layout: bool
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]


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


def _function(source: str) -> tuple[str, str, str]:
    matches = tuple(_FUNCTION_RE.finditer(source))
    if len(matches) != 1:
        raise CorpusError(f"expected one C function, found {len(matches)}")
    match = matches[0]
    return match.group("name"), match.group("params"), source[match.end() :]


def _pointer_streams(parameters: str) -> tuple[tuple[str, ...], tuple[str, ...]]:
    inputs: list[str] = []
    outputs: list[str] = []
    for raw in parameters.split(","):
        parameter = " ".join(raw.split())
        if "*" not in parameter:
            continue
        names = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", parameter)
        if not names:
            continue
        name = names[-1]
        if name == "params" or "void*" in parameter.replace(" ", ""):
            continue
        before_pointer = parameter.split("*", 1)[0]
        (inputs if re.search(r"\bconst\b", before_pointer) else outputs).append(name)
    return tuple(sorted(inputs)), tuple(sorted(outputs))


def _intrinsic_calls(body: str, architecture: BackendArchitecture) -> tuple[str, ...]:
    calls = set()
    for spelling in _CALL_RE.findall(body):
        if spelling in _CONTROL_WORDS or spelling.startswith(("INT", "UINT", "XNN_")):
            continue
        if architecture is BackendArchitecture.NEON:
            if spelling.startswith("v"):
                calls.add(spelling)
        elif spelling.startswith("__riscv_"):
            calls.add(spelling)
    return tuple(sorted(calls))


def _looks_elementwise(
    neon_parameters: str,
    rvv_parameters: str,
    neon_body: str,
    rvv_body: str,
    outputs: tuple[str, ...],
) -> bool:
    return (
        len(outputs) == 1
        and re.search(r"\bsize_t\s+batch\b", neon_parameters) is not None
        and re.search(r"\bsize_t\s+batch\b", rvv_parameters) is not None
        and "__riscv_vsetvl_" in rvv_body
        and bool(re.search(r"\bvld[1-4][A-Za-z0-9_]*\s*\(", neon_body))
        and bool(re.search(r"\bvst[1-4][A-Za-z0-9_]*\s*\(", neon_body))
        and ("while (" in rvv_body or re.search(r"for\s*\([^;]*;\s*batch\s*>\s*0", rvv_body))
    )


def discover_candidates(repository_root: str | Path) -> tuple[_Candidate, ...]:
    """Discover paired elementwise-shaped functions without a name allowlist."""

    root = Path(repository_root).resolve()
    sources = {path.stem: path for path in (root / "kernels/source").glob("*.c")}
    targets = {path.stem: path for path in (root / "kernels/target").glob("*.c")}
    candidates: list[_Candidate] = []
    for program_id in sorted(sources.keys() & targets.keys()):
        neon_text = sources[program_id].read_text(encoding="utf-8")
        rvv_text = targets[program_id].read_text(encoding="utf-8")
        try:
            neon_function, neon_parameters, neon_body = _function(neon_text)
            rvv_function, rvv_parameters, rvv_body = _function(rvv_text)
        except CorpusError:
            continue
        inputs, outputs = _pointer_streams(neon_parameters)
        rvv_inputs, rvv_outputs = _pointer_streams(rvv_parameters)
        if (inputs, outputs) != (rvv_inputs, rvv_outputs):
            continue
        if not _looks_elementwise(
            neon_parameters, rvv_parameters, neon_body, rvv_body, outputs
        ):
            continue
        grouped = bool(re.search(r"\(uintptr_t\).*?\+\s*batch", neon_body))
        candidates.append(
            _Candidate(
                program_id,
                sources[program_id],
                targets[program_id],
                neon_function,
                rvv_function,
                grouped,
                inputs,
                outputs,
            )
        )
    return tuple(candidates)


def _facade_spellings(path: Path) -> frozenset[str]:
    return frozenset(_CALL_RE.findall(path.read_text(encoding="utf-8")))


def _facade_for(
    facades: Iterable[Path],
    neon_calls: tuple[str, ...],
    rvv_calls: tuple[str, ...],
) -> Path | None:
    required = set(neon_calls) | set(rvv_calls)
    matches = [path for path in facades if required <= _facade_spellings(path)]
    return matches[0] if len(matches) == 1 else None


def _entry_assertions(source: str) -> tuple[str, ...]:
    function_match = _FUNCTION_RE.search(source)
    if function_match is None:
        return ()
    body = source[function_match.end() :]
    control_offsets = [
        offset for marker in ("for (", "while (", "if XNN_", "if (")
        if (offset := body.find(marker)) >= 0
    ]
    prefix = body[: min(control_offsets)] if control_offsets else body
    return tuple(sorted(re.sub(r"\s+", "", value) for value in _ASSERT_RE.findall(prefix)))


def _schedule_preflight(source: str) -> str:
    _, _, body = _function(source)
    fixed_loops = len(re.findall(r"for\s*\(\s*;\s*batch\s*>=", body))
    if fixed_loops >= 2 or re.search(r"\bdo\s*\{", body):
        return "multi-phase"
    if re.search(r"\bif\b[^\n{]*batch\s*!=\s*0", body):
        return "fixed-tail"
    return "fixed-no-tail"


def _configured_spellings() -> dict[BackendArchitecture, frozenset[str]]:
    result: dict[BackendArchitecture, set[str]] = {
        BackendArchitecture.NEON: set(),
        BackendArchitecture.RVV: set(),
    }
    for occurrence in configured_intrinsic_occurrences():
        result[occurrence.spec.architecture].add(occurrence.spec.spelling)
    return {architecture: frozenset(values) for architecture, values in result.items()}


def _status_for_error(error: Exception) -> str:
    if isinstance(error, (RecognitionError, IntrinsicResolutionError)):
        return error.status
    if isinstance(error, FrontendError):
        return ResultStatus.PARSE_UNSUPPORTED.value
    if isinstance(error, (GenerationError, CompilerError)):
        return ResultStatus.GENERATION_FAILED.value
    return ResultStatus.GENERATION_FAILED.value


def compile_corpus(
    repository_root: str | Path,
    output_directory: str | Path,
) -> dict[str, Any]:
    """Compile every discovered scalar-layout pair and record honest blockers."""

    root = Path(repository_root).resolve()
    output = Path(output_directory).resolve()
    facade_root = root / "src/workflow/verification/lean_backend/facade"
    facades = tuple(
        sorted(
            path
            for path in facade_root.glob("*.h")
            if path.name != "integer_types.h" and "example" not in path.name
        )
    )
    configured = _configured_spellings()
    discovered = discover_candidates(root)
    records: list[dict[str, Any]] = []
    dependencies: dict[str, set[str]] = {}
    for candidate in discovered:
        neon_text = candidate.neon_source.read_text(encoding="utf-8")
        rvv_text = candidate.rvv_source.read_text(encoding="utf-8")
        _, _, neon_body = _function(neon_text)
        _, _, rvv_body = _function(rvv_text)
        neon_calls = _intrinsic_calls(neon_body, BackendArchitecture.NEON)
        rvv_calls = _intrinsic_calls(rvv_body, BackendArchitecture.RVV)
        missing = tuple(
            sorted(
                {
                    *(f"neon:{name}" for name in neon_calls if name not in configured[BackendArchitecture.NEON]),
                    *(f"rvv:{name}" for name in rvv_calls if name not in configured[BackendArchitecture.RVV]),
                }
            )
        )
        for capability in (*[f"neon:{name}" for name in neon_calls], *[f"rvv:{name}" for name in rvv_calls]):
            dependencies.setdefault(capability, set()).add(candidate.program_id)
        external_request = discover_request(root, candidate.neon_source)
        external_preflight = None
        external_error = None
        if external_request is not None:
            try:
                external_preflight = audit_external_condition(
                    root,
                    (candidate.neon_source, candidate.rvv_source),
                    raw_source_pair_sha256(
                        root, (candidate.neon_source, candidate.rvv_source)
                    ),
                    external_request,
                )
            except ExternalConditionError as error:
                external_error = str(error)
        else:
            external_error = "no unique same-stem upstream registration was found"
        record: dict[str, Any] = {
            "program_id": candidate.program_id,
            "neon_source": candidate.neon_source.relative_to(root).as_posix(),
            "rvv_source": candidate.rvv_source.relative_to(root).as_posix(),
            "neon_function": candidate.neon_function,
            "rvv_function": candidate.rvv_function,
            "layout_preflight": "grouped-planar" if candidate.grouped_layout else "scalar-lane",
            "schedule_preflight": _schedule_preflight(neon_text),
            "entry_contract_preflight": (
                "equal" if _entry_assertions(neon_text) == _entry_assertions(rvv_text) else "mismatch"
            ),
            "input_streams": list(candidate.inputs),
            "output_streams": list(candidate.outputs),
            "neon_intrinsics": list(neon_calls),
            "rvv_intrinsics": list(rvv_calls),
            "missing_intrinsics": list(missing),
            "artifact_index": None,
            "manifest_sha256": None,
            "external_condition_status": (
                "audit-unavailable"
                if external_preflight is None
                else external_preflight.status.value
            ),
            "external_condition_sha256": (
                None if external_preflight is None else external_preflight.sha256
            ),
            "external_condition_detail": (
                external_error
                if external_preflight is None
                else external_preflight.detail
            ),
            "counterexample": None,
            "cross_phase_status": "not-typed",
            "status": ResultStatus.INTRINSIC_MISSING.value,
            "status_layer": "lexical-preflight",
            "detail": "no exact typed parse facade covers this pair",
        }
        if candidate.grouped_layout:
            record.update(
                status=ResultStatus.LAYOUT_UNRECOGNIZED.value,
                detail="planar grouping needs a reusable grouped layout capability",
            )
        else:
            facade = _facade_for(facades, neon_calls, rvv_calls)
            if facade is not None:
                program_output = output / "programs" / candidate.program_id
                try:
                    compilation = compile_pair(
                        CompilerRequest(
                            root,
                            candidate.neon_source,
                            candidate.rvv_source,
                            candidate.neon_function,
                            candidate.rvv_function,
                            facade,
                            facade,
                            "aarch64-none-elf",
                            "riscv64-none-elf",
                            f"SALT.Corpus.{re.sub(r'[^A-Za-z0-9]', '', candidate.program_id)}",
                            program_output,
                            external_condition=external_request,
                        )
                    )
                    external = compilation.external_condition
                    multi_phase = (
                        compilation.recognition.neon.kind.value == "multi-phase"
                    )
                    search_blocked = (
                        multi_phase
                        and external is not None
                        and external.status
                        is ExternalConditionStatus.REQUIRED_MISSING
                        and not external.candidate_contract.clauses
                    )
                    counterexample = None
                    cross_phase_status = (
                        "not-multi-phase"
                        if not multi_phase
                        else "blocked-by-missing-external-condition"
                        if search_blocked
                        else "no-counterexample-in-bounded-search"
                    )
                    if multi_phase and not search_blocked:
                        try:
                            counterexample = find_cross_phase_counterexample(
                                root, compilation
                            )
                        except CounterexampleError as error:
                            cross_phase_status = f"search-inconclusive: {error}"
                        else:
                            if counterexample is not None:
                                cross_phase_status = "lean-checked-counterexample"
                    generated_status = "spec-generated"
                    generated_detail = (
                        "typed manifest, Models, and proof-free Spec generated"
                    )
                    if counterexample is not None:
                        generated_status = ResultStatus.COUNTEREXAMPLE.value
                        generated_detail = (
                            "Lean checked a concrete disagreement between generated Neon phases"
                        )
                    elif (
                        external is not None
                        and external.status
                        is ExternalConditionStatus.REQUIRED_MISSING
                    ):
                        generated_status = (
                            ResultStatus.EXTERNAL_CONDITION_MISSING.value
                        )
                        generated_detail = (
                            "generated Spec is blocked because external input conditions are unresolved"
                        )
                    record.update(
                        status=generated_status,
                        status_layer="typed-generated",
                        detail=generated_detail,
                        artifact_index=compilation.artifact_index_path.relative_to(output).as_posix(),
                        manifest_sha256=compilation.manifest.sha256,
                        external_condition_status=(
                            "not-audited" if external is None else external.status.value
                        ),
                        external_condition_sha256=(
                            None if external is None else external.sha256
                        ),
                        external_condition_detail=(
                            None if external is None else external.detail
                        ),
                        counterexample=(
                            None
                            if counterexample is None
                            else {
                                "path": (
                                    program_output / "Counterexample.json"
                                ).relative_to(output).as_posix(),
                                "sha256": counterexample.sha256,
                                "claim": counterexample.claim,
                                "parameters": dict(
                                    counterexample.parameter_values
                                ),
                                "inputs": list(counterexample.input_values),
                                "left_output": counterexample.left_output,
                                "right_output": counterexample.right_output,
                            }
                        ),
                        cross_phase_status=cross_phase_status,
                    )
                except Exception as error:
                    record.update(
                        status=_status_for_error(error),
                        status_layer="typed-compiler",
                        detail=f"{type(error).__name__}: {error}",
                    )
        program_path = output / "programs" / candidate.program_id / "ProgramStatus.json"
        _atomic_write(program_path, canonical_json(record, pretty=True))
        record["program_status"] = program_path.relative_to(output).as_posix()
        records.append(record)
    scalar_records = [record for record in records if record["layout_preflight"] == "scalar-lane"]
    report: dict[str, Any] = {
        "artifact_kind": "elementwise-corpus-report",
        "schema_version": 1,
        "discovery_rule": "paired-single-output-vsetvl-vector-load-store-v1",
        "discovered_elementwise": len(records),
        "scalar_layout_scope": len(scalar_records),
        "grouped_layout_deferred": len(records) - len(scalar_records),
        "status_counts": {
            status: sum(record["status"] == status for record in records)
            for status in sorted({str(record["status"]) for record in records})
        },
        "external_condition_counts": {
            status: sum(record["external_condition_status"] == status for record in records)
            for status in sorted(
                {str(record["external_condition_status"]) for record in records}
            )
        },
        "counterexample_count": sum(record["counterexample"] is not None for record in records),
        "programs": records,
        "intrinsic_dependencies": [
            {
                "intrinsic": intrinsic,
                "configured": intrinsic.split(":", 1)[1] in configured[
                    BackendArchitecture(intrinsic.split(":", 1)[0])
                ],
                "programs": sorted(programs),
            }
            for intrinsic, programs in sorted(dependencies.items())
        ],
    }
    report["report_sha256"] = canonical_sha256(report)
    _atomic_write(output / "CorpusReport.json", canonical_json(report, pretty=True))
    return report


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    arguments = parser.parse_args(argv)
    report = compile_corpus(arguments.repository_root, arguments.output_directory)
    print(json.dumps(report["status_counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
