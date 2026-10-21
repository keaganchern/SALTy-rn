from __future__ import annotations

import json
import shutil
from collections import Counter
from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.compiler import (
    CompilerRequest,
    compile_pair,
)
from workflow.verification.elementwise_compiler.corpus import discover_candidates
from workflow.verification.elementwise_compiler.counterexamples import (
    find_cross_phase_counterexample,
)
from workflow.verification.elementwise_compiler.external_conditions import (
    ExternalConditionError,
    audit_external_condition,
    discover_request,
    raw_source_pair_sha256,
    verify_external_condition,
)
from workflow.verification.elementwise_compiler.proof import (
    ProofGateError,
    prepare_proof_task,
)
from workflow.verification.elementwise_compiler.schema import (
    CounterexampleWitness,
    CrossPhaseAudit,
    CrossPhaseAuditStatus,
    ExternalConditionEvidence,
    ExternalConditionScope,
    ExternalConditionStatus,
    Result,
    ResultStatus,
)


ROOT = Path(__file__).resolve().parents[3]
FACADE = ROOT / "src/workflow/verification/lean_backend/facade/s8_vclamp.h"
pytestmark = pytest.mark.skipif(shutil.which("clang") is None, reason="Clang required")


def _s8_evidence():
    neon = ROOT / "kernels/source/s8-vclamp.c"
    rvv = ROOT / "kernels/target/s8-vclamp.c"
    request = discover_request(ROOT, neon)
    assert request is not None
    binding = raw_source_pair_sha256(ROOT, (neon, rvv))
    return (
        neon,
        rvv,
        request,
        binding,
        audit_external_condition(ROOT, (neon, rvv), binding, request),
    )


def test_structural_external_audit_finds_eight_quantized_parameter_pairs() -> None:
    counts: Counter[str] = Counter()
    candidates = discover_candidates(ROOT)
    for candidate in candidates:
        request = discover_request(ROOT, candidate.neon_source)
        assert request is not None
        evidence = audit_external_condition(
            ROOT,
            (candidate.neon_source, candidate.rvv_source),
            raw_source_pair_sha256(
                ROOT, (candidate.neon_source, candidate.rvv_source)
            ),
            request,
        )
        counts[evidence.status.value] += 1

    assert counts == {
        ExternalConditionStatus.NOT_REQUIRED.value: 12,
        ExternalConditionStatus.REQUIRED_MISSING.value: 8,
    }


def test_s8_candidate_is_not_promoted_without_a_caller_guarantee() -> None:
    neon, rvv, _, binding, evidence = _s8_evidence()

    assert evidence.status is ExternalConditionStatus.REQUIRED_MISSING
    assert len(evidence.candidate_contract.clauses) == 1
    assert "caller" in evidence.detail
    verify_external_condition(ROOT, (neon, rvv), binding, evidence)
    with pytest.raises(ExternalConditionError, match="stale|reproduced"):
        verify_external_condition(ROOT, (neon, rvv), "f" * 64, evidence)


def test_compiler_emits_candidate_but_proof_gate_rejects_it(tmp_path: Path) -> None:
    neon, rvv, request, _, _ = _s8_evidence()
    output = tmp_path / "s8"
    compilation = compile_pair(
        CompilerRequest(
            ROOT,
            neon,
            rvv,
            "test_neon",
            "test_rvv",
            FACADE,
            FACADE,
            "aarch64-none-elf",
            "riscv64-none-elf",
            "SALT.Generated.ExternalS8",
            output,
            external_condition=request,
        )
    )

    spec = (output / "Spec.lean").read_text(encoding="utf-8")
    assert "def completeValueEquivalenceClaim : Prop" in spec
    assert "def candidateExternalCondition" in spec
    assert "completeValueEquivalenceUnderCandidateConditionClaim" in spec
    assert compilation.external_condition is not None
    assert compilation.manifest.external_condition is not None
    phase = CrossPhaseAudit.from_record(
        json.loads((output / "CrossPhaseAudit.json").read_text(encoding="utf-8"))
    )
    assert phase.status is CrossPhaseAuditStatus.COUNTEREXAMPLE
    with pytest.raises(ProofGateError, match="counterexample"):
        prepare_proof_task(ROOT, output)


def test_omitted_upstream_request_becomes_explicit_unconditional_audit(
    tmp_path: Path,
) -> None:
    neon, rvv, _, _, _ = _s8_evidence()
    output = tmp_path / "standalone-s8"
    compilation = compile_pair(
        CompilerRequest(
            ROOT,
            neon,
            rvv,
            "test_neon",
            "test_rvv",
            FACADE,
            FACADE,
            "aarch64-none-elf",
            "riscv64-none-elf",
            "SALT.Generated.StandaloneS8",
            output,
        )
    )

    evidence = ExternalConditionEvidence.from_record(
        json.loads((output / "ExternalCondition.json").read_text(encoding="utf-8"))
    )
    phase = CrossPhaseAudit.from_record(
        json.loads((output / "CrossPhaseAudit.json").read_text(encoding="utf-8"))
    )
    assert evidence == compilation.external_condition
    assert evidence.scope is ExternalConditionScope.LOCAL_UNCONDITIONAL
    assert evidence.status is ExternalConditionStatus.NOT_REQUIRED
    assert phase.status is CrossPhaseAuditStatus.COUNTEREXAMPLE
    with pytest.raises(ProofGateError, match="counterexample"):
        prepare_proof_task(ROOT, output)


def test_cross_phase_counterexample_is_found_and_lean_checked(tmp_path: Path) -> None:
    neon, rvv, request, _, _ = _s8_evidence()
    output = tmp_path / "counterexample"
    compilation = compile_pair(
        CompilerRequest(
            ROOT,
            neon,
            rvv,
            "test_neon",
            "test_rvv",
            FACADE,
            FACADE,
            "aarch64-none-elf",
            "riscv64-none-elf",
            "SALT.Generated.CounterexampleS8",
            output,
            external_condition=request,
        )
    )

    witness = find_cross_phase_counterexample(ROOT, compilation)

    assert witness is not None
    assert witness.left_output != witness.right_output
    assert dict(witness.parameter_values)["min"] > dict(witness.parameter_values)["max"]
    assert CounterexampleWitness.from_record(
        json.loads((output / "Counterexample.json").read_text(encoding="utf-8"))
    ) == witness
    assert "native_decide" in (output / "Counterexample.lean").read_text(
        encoding="utf-8"
    )
    result = Result.from_record(
        json.loads((output / "Result.json").read_text(encoding="utf-8"))
    )
    assert result.status is ResultStatus.COUNTEREXAMPLE
    assert result.counterexample_sha256 == witness.sha256


def test_external_extractor_contains_no_program_allowlist() -> None:
    source = (
        ROOT
        / "src/workflow/verification/elementwise_compiler/external_conditions.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "s8-vclamp",
        "qs8-vadd-minmax",
        "qu8-vadd-minmax",
        "qs8-vcvt",
        "qs8-vlrelu",
    ):
        assert forbidden not in source
