from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.program_counterexamples import (
    find_program_counterexample,
)
from workflow.verification.elementwise_compiler.proof import (
    ProofGateError,
    _load_index,
    _verify_stack,
    prepare_proof_task,
)
from workflow.verification.elementwise_compiler.schema import (
    CounterexampleWitness,
    Result,
    ResultStatus,
)


ROOT = Path(__file__).resolve().parents[3]
PROGRAMS = ROOT / "verification/elementwise-compiler/programs"
pytestmark = pytest.mark.skipif(
    shutil.which("lean") is None, reason="Lean is required"
)


def _copy_program(tmp_path: Path, program: str) -> Path:
    output = tmp_path / program
    shutil.copytree(PROGRAMS / program, output)
    return output


def test_complete_claim_counterexample_is_lean_checked_and_bound(tmp_path: Path) -> None:
    output = _copy_program(tmp_path, "f32-vmax")

    witness = find_program_counterexample(ROOT, output)

    assert witness is not None
    assert witness.claim == "SALT.Corpus.f32vmax.completeValueEquivalenceClaim"
    assert witness.left_output != witness.right_output
    assert not (output / "ProofTask.json").exists()
    assert CounterexampleWitness.from_record(
        json.loads((output / "Counterexample.json").read_text(encoding="utf-8"))
    ) == witness
    result = Result.from_record(
        json.loads((output / "Result.json").read_text(encoding="utf-8"))
    )
    assert result.status is ResultStatus.COUNTEREXAMPLE
    assert result.counterexample_sha256 == witness.sha256
    _verify_stack(ROOT, output, _load_index(output))
    with pytest.raises(ProofGateError, match="counterexample"):
        prepare_proof_task(ROOT, output)


def test_newly_exposed_f32_vadd_nan_gap_is_lean_checked(tmp_path: Path) -> None:
    output = _copy_program(tmp_path, "f32-vadd")

    witness = find_program_counterexample(ROOT, output)

    assert witness is not None
    assert witness.claim == "SALT.Corpus.f32vadd.completeValueEquivalenceClaim"
    assert witness.left_output != witness.right_output
    result = Result.from_record(
        json.loads((output / "Result.json").read_text(encoding="utf-8"))
    )
    assert result.status is ResultStatus.COUNTEREXAMPLE
    assert result.counterexample_sha256 == witness.sha256
    _verify_stack(ROOT, output, _load_index(output))


def test_counterexample_lean_mutation_fails_stack_integrity(tmp_path: Path) -> None:
    output = _copy_program(tmp_path, "f32-vmax")
    assert find_program_counterexample(ROOT, output) is not None
    path = output / "Counterexample.lean"
    path.write_text(path.read_text(encoding="utf-8") + "\n-- changed\n", encoding="utf-8")

    with pytest.raises(ProofGateError, match="counterexample identity"):
        _verify_stack(ROOT, output, _load_index(output))


def test_program_counterexample_search_has_no_corpus_allowlist() -> None:
    source = (
        ROOT
        / "src/workflow/verification/elementwise_compiler/program_counterexamples.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "f32-vrndne",
        "f32-vmax",
        "f32-vmin",
        "s8-vclamp",
    ):
        assert forbidden not in source
