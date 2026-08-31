"""Find and Lean-check concrete Neon/RVV program disagreements.

This bounded search is deliberately separate from proof search.  A miss is only
diagnostic and creates no artifact.  A hit is published only after Lean checks a
concrete negation of the generated ``completeValueEquivalenceClaim``.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from .lean_check import (
    ALLOWED_AXIOMS,
    _checked_axioms,
    _compile,
    _resolve_toolchain,
    _stage,
)
from .proof import _load_index, _verify_stack
from .schema import (
    CounterexampleWitness,
    CrossPhaseAuditStatus,
    ExternalConditionStatus,
    Result,
    ResultStatus,
    canonical_json,
    canonical_sha256,
)


class ProgramCounterexampleError(RuntimeError):
    """The generated whole-program diagnostic could not be checked."""


_FLOAT32_VALUES = (
    0x00000000,  # +0
    0x80000000,  # -0
    0x3F800000,  # +1
    0xBF800000,  # -1
    0x7F800000,  # +inf
    0xFF800000,  # -inf
    0x7FC00000,  # quiet NaN
    0x7FA00001,  # signaling-NaN payload
)
_MAX_TRIALS = 256


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


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


def _bit_values(width: int) -> tuple[int, ...]:
    if width == 32:
        return _FLOAT32_VALUES
    maximum = (1 << width) - 1
    return tuple(dict.fromkeys((0, 1, maximum // 2, maximum)))


def _parameter_fields(models_text: str, parameter_type: str) -> tuple[tuple[str, int], ...]:
    match = re.search(
        rf"(?ms)^structure\s+{re.escape(parameter_type)}\s+where\s*(.*?)^\s*deriving\b",
        models_text,
    )
    if match is None:
        raise ProgramCounterexampleError("generated parameter structure is absent")
    fields = tuple(
        (name, int(width))
        for name, width in re.findall(
            r"(?m)^\s*([A-Za-z_][A-Za-z0-9_']*)\s*:\s*BitVec\s+([0-9]+)\s*$",
            match.group(1),
        )
    )
    residue = re.sub(
        r"(?m)^\s*[A-Za-z_][A-Za-z0-9_']*\s*:\s*BitVec\s+[0-9]+\s*$",
        "",
        match.group(1),
    )
    if residue.strip():
        raise ProgramCounterexampleError("unsupported generated parameter field")
    return fields


def _parameter_trials(fields: Sequence[tuple[str, int]]) -> tuple[tuple[int, ...], ...]:
    zero = (0,) * len(fields)
    trials = [zero]
    for index, (_, width) in enumerate(fields):
        for value in _bit_values(width):
            candidate = list(zero)
            candidate[index] = value
            trials.append(tuple(candidate))
    return tuple(dict.fromkeys(trials))


def _input_width(manifest: object) -> int:
    layout = getattr(manifest, "layout")
    input_streams = tuple(getattr(layout, "input_streams"))
    types = dict(getattr(layout, "stream_c_types"))
    widths = {
        "float": 32,
        "int8_t": 8,
        "uint8_t": 8,
        "int16_t": 16,
        "uint16_t": 16,
        "int32_t": 32,
        "uint32_t": 32,
    }
    found = {widths.get(types[stream]) for stream in input_streams}
    if None in found or len(found) != 1:
        raise ProgramCounterexampleError("scalar search needs one known input width")
    return next(iter(found))


def _input_trials(arity: int, width: int) -> tuple[tuple[int, ...], ...]:
    values = _bit_values(width)
    if arity == 1:
        return tuple((value,) for value in values)
    if arity == 2:
        return tuple(itertools.product(values, repeat=2))
    raise ProgramCounterexampleError("scalar search supports one or two input streams")


def _params(parameter_type: str, fields: Sequence[tuple[str, int]], values: Sequence[int]) -> str:
    body = ", ".join(
        f"{name} := ({value} : BitVec {width})"
        for (name, width), value in zip(fields, values, strict=True)
    )
    return f"({{ {body} }} : {parameter_type})"


def _search_text(
    namespace: str,
    parameter_type: str,
    fields: Sequence[tuple[str, int]],
    trials: Sequence[tuple[tuple[int, ...], tuple[int, ...]]],
    width: int,
) -> str:
    expressions = []
    for parameter_values, input_values in trials:
        p = _params(parameter_type, fields, parameter_values)
        args = " ".join(f"({value} : BitVec {width})" for value in input_values)
        expressions.append(f"decide (fNeon {p} {args} != fRvv {p} {args})")
    return (
        f"import {namespace}.Spec\nnamespace {namespace}\n\n"
        "def firstTrue : List Bool -> Nat -> Option Nat\n"
        "  | [], _ => none\n"
        "  | value :: rest, index =>\n"
        "      if value then some index else firstTrue rest (index + 1)\n\n"
        "#eval firstTrue [\n  "
        + ",\n  ".join(expressions)
        + "\n] 0\n\n"
        + f"end {namespace}\n"
    )


def _tail_width(manifest: object) -> int:
    schedules = tuple(getattr(manifest, "schedules"))
    neon = next(
        (schedule for schedule in schedules if schedule.architecture.value == "neon"),
        None,
    )
    if neon is None or neon.capability.capability_id not in {
        "schedule:neon:fixed-tail",
        "schedule:neon:multi-phase",
    }:
        raise ProgramCounterexampleError(
            "whole-claim witness currently supports generated tail families"
        )
    text = dict(neon.parameters).get("phase_widths")
    if not isinstance(text, str):
        raise ProgramCounterexampleError("Neon phase widths are absent")
    widths = tuple(int(value) for value in text.split(","))
    if not widths or widths[-1] <= 1:
        raise ProgramCounterexampleError("invalid generated tail phase width")
    return widths[-1]


def _witness_text(
    namespace: str,
    parameter_type: str,
    fields: Sequence[tuple[str, int]],
    parameter_values: Sequence[int],
    input_values: Sequence[int],
    width: int,
    tail_width: int,
    left: int,
    right: int,
) -> str:
    p = _params(parameter_type, fields, parameter_values)
    inputs = "\n".join(
        f"def counterexampleInput{index} : List (BitVec {width}) := [{value}]"
        for index, value in enumerate(input_values)
    )
    overreads = "\n".join(
        f"def counterexampleOverread{index} : List (BitVec {width}) := "
        f"List.replicate {tail_width - 1} 0"
        for index in range(len(input_values))
    )
    neon_args = " ".join(
        [
            "counterexampleParams",
            *(f"counterexampleInput{i}" for i in range(len(input_values))),
            *(f"counterexampleOverread{i}" for i in range(len(input_values))),
        ]
    )
    rvv_args = " ".join(
        [
            "counterexampleParams",
            *(f"counterexampleInput{i}" for i in range(len(input_values))),
        ]
    )
    claim_args = [
        "counterexampleParams",
        *(f"counterexampleInput{i}" for i in range(len(input_values))),
        *(f"counterexampleOverread{i}" for i in range(len(input_values))),
    ]
    if len(input_values) == 2:
        same_length = (
            "(by decide : counterexampleInput0.length = counterexampleInput1.length)"
        )
        neon_args += f" {same_length}"
        rvv_args += f" {same_length}"
        claim_args.append(same_length)
    claim_args.extend(("counterexampleSchedule", "(by decide)"))
    neon_expression = f"neonValueLoopWithOverreadFromIntrinsics {neon_args}"
    rvv_expression = (
        f"rvvValueLoopFromIntrinsics {rvv_args} counterexampleSchedule"
    )
    schedule = (
        "def counterexampleSchedule :\n"
        "    SALT.Kernel.Schedule.PositivePartition counterexampleInput0.length :=\n"
        "  SALT.Kernel.Schedule.PositivePartition.singleton 1 (by decide)"
    )
    return f"""import {namespace}.Spec

namespace {namespace}

def counterexampleParams : {parameter_type} := {p}
{inputs}
{overreads}
{schedule}

example : (({neon_expression}).headD 0).toNat = {left} := by
  native_decide
example : (({rvv_expression}).headD 0).toNat = {right} := by
  native_decide
theorem completeValueEquivalenceCounterexample : Not completeValueEquivalenceClaim := by
  intro claim
  have impossible := claim {' '.join(claim_args)}
  exact (by native_decide : {neon_expression} ≠ {rvv_expression}) impossible

end {namespace}
"""


def _evaluate_text(
    namespace: str,
    parameter_type: str,
    fields: Sequence[tuple[str, int]],
    parameter_values: Sequence[int],
    input_values: Sequence[int],
    width: int,
) -> str:
    p = _params(parameter_type, fields, parameter_values)
    args = " ".join(f"({value} : BitVec {width})" for value in input_values)
    return (
        f"import {namespace}.Spec\nnamespace {namespace}\n"
        f"#eval (fNeon {p} {args}).toNat\n"
        f"#eval (fRvv {p} {args}).toNat\n"
        f"end {namespace}\n"
    )


def _numbers(output: str) -> tuple[int, ...]:
    return tuple(int(value) for value in re.findall(r"(?m)^([0-9]+)\s*$", output))


def _checker_sha256() -> str:
    here = Path(__file__).resolve()
    return canonical_sha256(
        {
            "program_counterexamples.py": _sha256(here),
            "proof.py": _sha256(here.with_name("proof.py")),
            "schema.py": _sha256(here.with_name("schema.py")),
        }
    )


def _write_index(
    output: Path, index: Mapping[str, Any], witness: CounterexampleWitness, result: Result
) -> None:
    record = dict(index)
    record.pop("stack_sha256", None)
    record.pop("proof_task", None)
    record["counterexample"] = {
        "path": "Counterexample.json",
        "sha256": witness.sha256,
        "lean_path": witness.lean_path,
        "lean_sha256": witness.lean_sha256,
        "claim": witness.claim,
    }
    record["result"] = {
        "path": "Result.json",
        "sha256": result.sha256,
        "status": result.status.value,
    }
    record["stack_sha256"] = canonical_sha256(record)
    _atomic_write(output / "ArtifactIndex.json", canonical_json(record, pretty=True))


def find_program_counterexample(
    repository_root: str | Path,
    output_directory: str | Path,
) -> CounterexampleWitness | None:
    """Publish a checked complete-claim witness, or return ``None`` after a miss."""

    repository = Path(repository_root).resolve()
    output = Path(output_directory).resolve()
    index = _load_index(output)
    manifest, _, _, namespace, target_claim, external, phase = _verify_stack(
        repository, output, index
    )
    if index.get("counterexample") is not None:
        witness = CounterexampleWitness.from_record(
            json.loads((output / "Counterexample.json").read_text(encoding="utf-8"))
        )
        if witness.claim != f"{namespace}.completeValueEquivalenceClaim":
            return None
        if witness.checker_sha256 == _checker_sha256():
            return witness
    if external.status is ExternalConditionStatus.REQUIRED_MISSING:
        return None
    if phase.status is CrossPhaseAuditStatus.COUNTEREXAMPLE:
        return None
    if target_claim != "completeValueEquivalenceClaim":
        raise ProgramCounterexampleError("unexpected generated target claim")

    models_text = (output / "Models.lean").read_text(encoding="utf-8")
    parameter_match = re.search(r"(?m)^structure\s+([A-Za-z_][A-Za-z0-9_']*)\s+where$", models_text)
    if parameter_match is None:
        raise ProgramCounterexampleError("generated parameter type is absent")
    parameter_type = parameter_match.group(1)
    fields = _parameter_fields(models_text, parameter_type)
    width = _input_width(manifest)
    arity = len(manifest.layout.input_streams)
    trials = tuple(
        itertools.islice(
            itertools.product(_parameter_trials(fields), _input_trials(arity, width)),
            _MAX_TRIALS,
        )
    )
    toolchain = _resolve_toolchain(repository)
    temporary, stage, environment = _stage(
        repository, output, namespace, toolchain, include_proof=False
    )
    try:
        module_directory = stage.joinpath(*namespace.split("."))
        for name in ("Models.lean", "Spec.lean"):
            completed = _compile(
                toolchain, stage, environment, module_directory / name, emit_olean=True
            )
            if completed.returncode != 0:
                raise ProgramCounterexampleError(
                    f"generated {name} failed before search:\n{completed.stdout}{completed.stderr}"
                )
        search = stage / "ProgramCounterexampleSearch.lean"
        search.write_text(
            _search_text(namespace, parameter_type, fields, trials, width),
            encoding="utf-8",
        )
        completed = _compile(toolchain, stage, environment, search, emit_olean=False)
        if completed.returncode != 0:
            raise ProgramCounterexampleError(
                f"Lean program search failed:\n{completed.stdout}{completed.stderr}"
            )
        match = re.search(r"some\s+([0-9]+)", completed.stdout)
        if match is None:
            if re.search(r"(?m)^none\s*$", completed.stdout):
                return None
            raise ProgramCounterexampleError("Lean search did not print a recognized result")
        trial_index = int(match.group(1))
        if trial_index >= len(trials):
            raise ProgramCounterexampleError("Lean returned an out-of-range trial index")
        parameter_values, input_values = trials[trial_index]
        evaluate = stage / "ProgramCounterexampleEvaluate.lean"
        evaluate.write_text(
            _evaluate_text(
                namespace,
                parameter_type,
                fields,
                parameter_values,
                input_values,
                width,
            ),
            encoding="utf-8",
        )
        completed = _compile(toolchain, stage, environment, evaluate, emit_olean=False)
        numbers = _numbers(completed.stdout)
        if completed.returncode != 0 or len(numbers) != 2 or numbers[0] == numbers[1]:
            raise ProgramCounterexampleError(
                f"Lean could not evaluate candidate outputs:\n{completed.stdout}{completed.stderr}"
            )
        left, right = numbers
        witness_text = _witness_text(
            namespace,
            parameter_type,
            fields,
            parameter_values,
            input_values,
            width,
            _tail_width(manifest),
            left,
            right,
        )
        staged_witness = stage / "ProgramCounterexample.lean"
        staged_witness.write_text(witness_text, encoding="utf-8")
        completed = _compile(
            toolchain, stage, environment, staged_witness, emit_olean=True
        )
        if completed.returncode != 0:
            raise ProgramCounterexampleError(
                f"Lean rejected complete-claim witness:\n{completed.stdout}{completed.stderr}"
            )
        audit = stage / "ProgramCounterexampleAudit.lean"
        theorem = f"{namespace}.completeValueEquivalenceCounterexample"
        claim = f"{namespace}.completeValueEquivalenceClaim"
        audit.write_text(
            "import ProgramCounterexample\n"
            f"example : Not {claim} := {theorem}\n"
            f"#print axioms {theorem}\n",
            encoding="utf-8",
        )
        completed = _compile(toolchain, stage, environment, audit, emit_olean=False)
        if completed.returncode != 0:
            raise ProgramCounterexampleError(
                f"Lean counterexample audit failed:\n{completed.stdout}{completed.stderr}"
            )
        axioms = _checked_axioms(completed.stdout + completed.stderr)
        generated_native = {
            axiom
            for axiom in axioms
            if re.fullmatch(
                re.escape(theorem)
                + r"\._native\.native_decide\.ax_[0-9_]+",
                axiom,
            )
        }
        unexpected = sorted(axioms - ALLOWED_AXIOMS - generated_native)
        if unexpected:
            raise ProgramCounterexampleError(
                f"counterexample depends on forbidden axioms {unexpected!r}"
            )
    finally:
        temporary.cleanup()

    lean_path = output / "Counterexample.lean"
    _atomic_write(lean_path, witness_text)
    checker_sha = _checker_sha256()
    witness = CounterexampleWitness(
        manifest_sha256=manifest.sha256,
        models_sha256=_sha256(output / "Models.lean"),
        spec_sha256=_sha256(output / "Spec.lean"),
        claim=f"{namespace}.completeValueEquivalenceClaim",
        left_function=f"{namespace}.neonValueLoopWithOverreadFromIntrinsics",
        right_function=f"{namespace}.rvvValueLoopFromIntrinsics",
        parameter_values=tuple(
            sorted(
                (name, value)
                for (name, _), value in zip(fields, parameter_values, strict=True)
            )
        ),
        input_values=tuple(input_values),
        left_output=left,
        right_output=right,
        lean_path="Counterexample.lean",
        lean_sha256=_sha256(lean_path),
        checker_sha256=checker_sha,
        toolchain_sha256=toolchain.sha256,
    )
    result = Result(
        status=ResultStatus.COUNTEREXAMPLE,
        proof_task_sha256=None,
        proof_sha256=None,
        checker_sha256=checker_sha,
        toolchain_sha256=toolchain.sha256,
        start_closure_sha256=None,
        end_closure_sha256=None,
        detail="Lean checked a concrete Neon/RVV complete value-claim disagreement",
        counterexample_sha256=witness.sha256,
    )
    _atomic_write(
        output / "Counterexample.json", canonical_json(witness.to_record(), pretty=True)
    )
    _atomic_write(output / "Result.json", canonical_json(result.to_record(), pretty=True))
    (output / "ProofTask.json").unlink(missing_ok=True)
    (output / "Proof.lean").unlink(missing_ok=True)
    _write_index(output, index, witness, result)
    return witness


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    arguments = parser.parse_args(argv)
    witness = find_program_counterexample(
        arguments.repository_root,
        arguments.output_directory,
    )
    print("none" if witness is None else canonical_json(witness.to_record()))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
