"""Find and Lean-check concrete disagreements between generated Neon phases."""

from __future__ import annotations

import hashlib
import itertools
import json
import os
import re
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING, Iterable, Mapping, Sequence

from .capabilities import ScheduleKind
from .lean_check import (
    ALLOWED_AXIOMS,
    _checked_axioms,
    _compile,
    _resolve_toolchain,
    _stage,
)
from .schema import (
    CounterexampleWitness,
    CrossPhaseAudit,
    CrossPhaseAuditStatus,
    ExternalConditionStatus,
    Result,
    ResultStatus,
    canonical_json,
    canonical_sha256,
)

if TYPE_CHECKING:
    from .compiler import Compilation


class CounterexampleError(RuntimeError):
    """The generated cross-phase diagnostic could not be checked."""


_VALUES = (0, 5, 10, 127, 128, 255)
# Keep the generated Lean term small enough that elaboration itself is a reliable
# gate.  This search is a bug finder, not a proof of absence; 128 deterministic
# points include all one-field perturbations and the clamp-order witness.
_MAX_TRIALS = 128


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


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


def _parameter_assignments(fields: Sequence[object]) -> tuple[tuple[int, ...], ...]:
    width = len(fields)
    zero = (0,) * width
    assignments = {zero}
    for index in range(width):
        for value in _VALUES:
            item = list(zero)
            item[index] = value
            assignments.add(tuple(item))
    for first, second in itertools.combinations(range(width), 2):
        for left in _VALUES:
            for right in _VALUES:
                item = list(zero)
                item[first] = left
                item[second] = right
                assignments.add(tuple(item))
    return tuple(sorted(assignments))


def _input_assignments(arity: int) -> tuple[tuple[int, ...], ...]:
    if arity == 1:
        return tuple((value,) for value in _VALUES)
    if arity == 2:
        return tuple(
            dict.fromkeys(
                [*((value, value) for value in _VALUES), (0, 255), (255, 0)]
            )
        )
    raise CounterexampleError("cross-phase search supports one or two inputs")


def _params(stack: object, values: Sequence[int]) -> str:
    fields = getattr(stack, "parameter_fields")
    if len(fields) != len(values):
        raise CounterexampleError("parameter assignment arity changed")
    body = ", ".join(
        f"{field.name} := ({value} : BitVec {field.width})"
        for field, value in zip(fields, values, strict=True)
    )
    return f"({{ {body} }} : {getattr(stack, 'parameter_type')})"


def _arguments(width: int, values: Sequence[int]) -> str:
    return " ".join(f"({value} : BitVec {width})" for value in values)


def _trials(compilation: "Compilation") -> tuple[tuple[tuple[int, ...], tuple[int, ...]], ...]:
    parameters = _parameter_assignments(compilation.stack.parameter_fields)
    inputs = _input_assignments(len(compilation.recognition.inputs))
    result: list[tuple[tuple[int, ...], tuple[int, ...]]] = []
    for parameter_values in parameters:
        for input_values in inputs:
            result.append((parameter_values, input_values))
            if len(result) == _MAX_TRIALS:
                return tuple(result)
    return tuple(result)


def _search_text(namespace: str, compilation: "Compilation", trials: Sequence[object]) -> str:
    expressions = []
    for parameter_values, input_values in trials:
        params = _params(compilation.stack, parameter_values)
        arguments = _arguments(compilation.stack.input_width, input_values)
        expressions.append(
            f"decide (fNeon {params} {arguments} ≠ fNeonSecondary {params} {arguments})"
        )
    return (
        f"import {namespace}.Spec\n"
        f"namespace {namespace}\n\n"
        "def firstTrue : List Bool → Nat → Option Nat\n"
        "  | [], _ => none\n"
        "  | value :: rest, index =>\n"
        "      if value then some index else firstTrue rest (index + 1)\n\n"
        "#eval firstTrue [\n  "
        + ",\n  ".join(expressions)
        + "\n] 0\n\n"
        f"end {namespace}\n"
    )


def _evaluation_text(
    namespace: str,
    compilation: "Compilation",
    parameter_values: Sequence[int],
    input_values: Sequence[int],
) -> str:
    params = _params(compilation.stack, parameter_values)
    arguments = _arguments(compilation.stack.input_width, input_values)
    return (
        f"import {namespace}.Spec\n"
        f"namespace {namespace}\n"
        f"#eval (fNeon {params} {arguments}).toNat\n"
        f"#eval (fNeonSecondary {params} {arguments}).toNat\n"
        f"end {namespace}\n"
    )


def _witness_text(
    namespace: str,
    compilation: "Compilation",
    parameter_values: Sequence[int],
    input_values: Sequence[int],
    left: int,
    right: int,
) -> str:
    fields = compilation.stack.parameter_fields
    structure = ", ".join(
        f"{field.name} := ({value} : BitVec {field.width})"
        for field, value in zip(fields, parameter_values, strict=True)
    )
    input_defs = "\n".join(
        f"def counterexampleInput{index} : BitVec {compilation.stack.input_width} := {value}"
        for index, value in enumerate(input_values)
    )
    arguments = " ".join(
        f"counterexampleInput{index}" for index in range(len(input_values))
    )
    return f"""import {namespace}.Spec

namespace {namespace}

def counterexampleParams : {compilation.stack.parameter_type} := {{ {structure} }}
{input_defs}

example : (fNeon counterexampleParams {arguments}).toNat = {left} := by native_decide
example : (fNeonSecondary counterexampleParams {arguments}).toNat = {right} := by native_decide
theorem neonPhaseFunctionsCounterexample : Not neonPhaseFunctionsEqualClaim := by
  intro claim
  exact (by native_decide : fNeon counterexampleParams {arguments} ≠
    fNeonSecondary counterexampleParams {arguments})
    (claim counterexampleParams {arguments})

end {namespace}
"""


def _numbers(output: str) -> tuple[int, ...]:
    return tuple(int(value) for value in re.findall(r"(?m)^([0-9]+)\s*$", output))


def _update_index(
    output: Path,
    audit: CrossPhaseAudit,
    witness: CounterexampleWitness | None = None,
    result: Result | None = None,
) -> None:
    path = output / "ArtifactIndex.json"
    record = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(record, dict):
        raise CounterexampleError("ArtifactIndex root is not an object")
    stored = record.pop("stack_sha256", None)
    if stored != canonical_sha256(record):
        raise CounterexampleError("ArtifactIndex digest changed before counterexample audit")
    record["cross_phase_audit"] = {
        "path": "CrossPhaseAudit.json",
        "sha256": audit.sha256,
        "status": audit.status.value,
    }
    if witness is not None and result is not None:
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
    else:
        record.pop("counterexample", None)
        record.pop("result", None)
    record["stack_sha256"] = canonical_sha256(record)
    _atomic_write(path, canonical_json(record, pretty=True))


def _checker_sha256() -> str:
    return canonical_sha256(
        {
            "counterexamples.py": _sha256(Path(__file__).resolve()),
            "proof.py": _sha256(Path(__file__).with_name("proof.py").resolve()),
        }
    )


def _write_audit(output: Path, audit: CrossPhaseAudit) -> None:
    _atomic_write(
        output / "CrossPhaseAudit.json",
        canonical_json(audit.to_record(), pretty=True),
    )


def _existing_audit(
    output: Path, index: Mapping[str, object], compilation: "Compilation"
) -> tuple[CrossPhaseAudit, CounterexampleWitness | None] | None:
    binding = index.get("cross_phase_audit")
    if binding is None:
        return None
    if not isinstance(binding, Mapping):
        raise CounterexampleError("cross-phase audit binding is malformed")
    audit = CrossPhaseAudit.from_record(
        json.loads((output / str(binding.get("path", ""))).read_text(encoding="utf-8"))
    )
    if (
        binding.get("sha256") != audit.sha256
        or binding.get("status") != audit.status.value
        or audit.manifest_sha256 != compilation.manifest.sha256
        or audit.models_sha256 != compilation.models.sha256
        or audit.spec_sha256 != compilation.spec.sha256
    ):
        raise CounterexampleError("cross-phase audit identity differs from generated stack")
    witness = None
    if audit.status is CrossPhaseAuditStatus.COUNTEREXAMPLE:
        counterexample = index.get("counterexample")
        if not isinstance(counterexample, Mapping):
            raise CounterexampleError("counterexample audit has no witness binding")
        witness = CounterexampleWitness.from_record(
            json.loads(
                (output / str(counterexample.get("path", ""))).read_text(
                    encoding="utf-8"
                )
            )
        )
        if witness.sha256 != audit.counterexample_sha256:
            raise CounterexampleError("cross-phase audit witness digest differs")
    return audit, witness


def audit_cross_phase(
    repository_root: str | Path,
    compilation: "Compilation",
) -> tuple[CrossPhaseAudit, CounterexampleWitness | None]:
    """Run and persist the mandatory generic cross-phase audit."""

    repository = Path(repository_root).resolve()
    output = compilation.artifact_index_path.parent.resolve()
    index = json.loads(compilation.artifact_index_path.read_text(encoding="utf-8"))
    existing = _existing_audit(output, index, compilation)
    if existing is not None:
        return existing
    namespace = index.get("namespace")
    if not isinstance(namespace, str) or not namespace:
        raise CounterexampleError("ArtifactIndex namespace is absent")
    claim = f"{namespace}.neonPhaseFunctionsEqualClaim"
    if compilation.recognition.neon.kind is not ScheduleKind.MULTI_PHASE:
        audit = CrossPhaseAudit(
            compilation.manifest.sha256,
            compilation.models.sha256,
            compilation.spec.sha256,
            f"{namespace}.completeValueEquivalenceClaim",
            CrossPhaseAuditStatus.NOT_APPLICABLE,
            0,
            None,
            None,
            None,
            None,
            "generated Neon schedule has only one scalar phase function",
        )
        _write_audit(output, audit)
        _update_index(output, audit)
        return audit, None
    external = compilation.external_condition
    if (
        external.status is ExternalConditionStatus.REQUIRED_MISSING
        and not external.candidate_contract.clauses
    ):
        audit = CrossPhaseAudit(
            compilation.manifest.sha256,
            compilation.models.sha256,
            compilation.spec.sha256,
            claim,
            CrossPhaseAuditStatus.BLOCKED_EXTERNAL_CONDITION,
            0,
            None,
            None,
            external.sha256,
            None,
            "cross-phase search is blocked by an unresolved parameter domain",
        )
        _write_audit(output, audit)
        _update_index(output, audit)
        return audit, None
    trials = _trials(compilation)
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
                raise CounterexampleError(
                    f"generated {name} failed before search:\n{completed.stdout}{completed.stderr}"
                )
        search = stage / "CrossPhaseSearch.lean"
        search.write_text(_search_text(namespace, compilation, trials), encoding="utf-8")
        completed = _compile(toolchain, stage, environment, search, emit_olean=False)
        if completed.returncode != 0:
            raise CounterexampleError(
                f"Lean counterexample search failed:\n{completed.stdout}{completed.stderr}"
            )
        match = re.search(r"some\s+([0-9]+)", completed.stdout)
        if match is None:
            if re.search(r"(?m)^none\s*$", completed.stdout):
                audit = CrossPhaseAudit(
                    compilation.manifest.sha256,
                    compilation.models.sha256,
                    compilation.spec.sha256,
                    claim,
                    CrossPhaseAuditStatus.NO_COUNTEREXAMPLE_BOUNDED,
                    len(trials),
                    _checker_sha256(),
                    toolchain.sha256,
                    external.sha256,
                    None,
                    "bounded Lean evaluation found no concrete phase disagreement; this is not a proof",
                )
                _write_audit(output, audit)
                _update_index(output, audit)
                return audit, None
            raise CounterexampleError("Lean search did not print a recognized result")
        trial_index = int(match.group(1))
        if trial_index >= len(trials):
            raise CounterexampleError("Lean returned an out-of-range trial index")
        parameter_values, input_values = trials[trial_index]
        evaluation = stage / "CrossPhaseEvaluate.lean"
        evaluation.write_text(
            _evaluation_text(
                namespace, compilation, parameter_values, input_values
            ),
            encoding="utf-8",
        )
        completed = _compile(toolchain, stage, environment, evaluation, emit_olean=False)
        numbers = _numbers(completed.stdout)
        if completed.returncode != 0 or len(numbers) != 2 or numbers[0] == numbers[1]:
            raise CounterexampleError(
                f"Lean could not evaluate the candidate outputs:\n{completed.stdout}{completed.stderr}"
            )
        left, right = numbers
        witness_text = _witness_text(
            namespace,
            compilation,
            parameter_values,
            input_values,
            left,
            right,
        )
        staged_witness = stage / "Counterexample.lean"
        staged_witness.write_text(witness_text, encoding="utf-8")
        completed = _compile(
            toolchain, stage, environment, staged_witness, emit_olean=True
        )
        if completed.returncode != 0:
            raise CounterexampleError(
                f"Lean rejected the concrete witness:\n{completed.stdout}{completed.stderr}"
            )
        audit_file = stage / "CrossPhaseCounterexampleAudit.lean"
        theorem = f"{namespace}.neonPhaseFunctionsCounterexample"
        claim_type = f"{namespace}.neonPhaseFunctionsEqualClaim"
        audit_file.write_text(
            "import Counterexample\n"
            f"example : Not {claim_type} := {theorem}\n"
            f"#print axioms {theorem}\n",
            encoding="utf-8",
        )
        completed = _compile(
            toolchain, stage, environment, audit_file, emit_olean=False
        )
        if completed.returncode != 0:
            raise CounterexampleError(
                f"Lean phase-counterexample audit failed:\n"
                f"{completed.stdout}{completed.stderr}"
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
            raise CounterexampleError(
                f"phase counterexample depends on forbidden axioms {unexpected!r}"
            )
    finally:
        temporary.cleanup()
    lean_path = output / "Counterexample.lean"
    _atomic_write(lean_path, witness_text)
    checker_sha = _checker_sha256()
    witness = CounterexampleWitness(
        manifest_sha256=compilation.manifest.sha256,
        models_sha256=compilation.models.sha256,
        spec_sha256=compilation.spec.sha256,
        claim=f"{namespace}.neonPhaseFunctionsEqualClaim",
        left_function=f"{namespace}.fNeon",
        right_function=f"{namespace}.fNeonSecondary",
        parameter_values=tuple(
            sorted(
                (field.name, value)
                for field, value in zip(
                    compilation.stack.parameter_fields,
                    parameter_values,
                    strict=True,
                )
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
    _atomic_write(
        output / "Counterexample.json", canonical_json(witness.to_record(), pretty=True)
    )
    result = Result(
        status=ResultStatus.COUNTEREXAMPLE,
        proof_task_sha256=None,
        proof_sha256=None,
        checker_sha256=checker_sha,
        toolchain_sha256=toolchain.sha256,
        start_closure_sha256=None,
        end_closure_sha256=None,
        detail=(
            "Lean checked a concrete disagreement between generated Neon phase functions"
        ),
        counterexample_sha256=witness.sha256,
    )
    _atomic_write(output / "Result.json", canonical_json(result.to_record(), pretty=True))
    audit = CrossPhaseAudit(
        compilation.manifest.sha256,
        compilation.models.sha256,
        compilation.spec.sha256,
        claim,
        CrossPhaseAuditStatus.COUNTEREXAMPLE,
        len(trials),
        checker_sha,
        toolchain.sha256,
        external.sha256,
        witness.sha256,
        "bounded search found a concrete phase disagreement and Lean checked it",
    )
    _write_audit(output, audit)
    _update_index(output, audit, witness, result)
    return audit, witness


def find_cross_phase_counterexample(
    repository_root: str | Path,
    compilation: "Compilation",
) -> CounterexampleWitness | None:
    """Return the mandatory audit's Lean-checked disagreement, if one exists."""

    return audit_cross_phase(repository_root, compilation)[1]
