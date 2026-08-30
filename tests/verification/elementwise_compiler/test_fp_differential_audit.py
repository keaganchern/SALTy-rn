from __future__ import annotations

import json
import platform
import shutil
from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.fp_differential_audit import (
    EXPECTED_EXACT_SUBJECTS,
    FPDifferentialAuditError,
    build_audit,
    load_exact_subjects,
    render_ledger_projection,
    validate_audit,
)
from workflow.verification.elementwise_compiler.schema import canonical_sha256


ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "verification/elementwise-compiler"
EVIDENCE = CORPUS / "FPDifferentialAudit.json"
LEDGER_PROJECTION = CORPUS / "FPDifferentialAuditLedger.csv"


def _evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_fp0_through_fp4_set_is_loaded_by_exact_capability_id() -> None:
    subjects = load_exact_subjects(CORPUS)
    assert len(subjects) == EXPECTED_EXACT_SUBJECTS == 28
    assert len({subject["capability"]["capability_id"] for subject in subjects}) == 28
    assert {subject["review_family"].split("-", 1)[0] for subject in subjects} == {
        "FP0",
        "FP1",
        "FP2",
        "FP3",
        "FP4",
    }
    for subject in subjects:
        capability = subject["capability"]
        audit = subject["audit"]
        assert capability["capability_id"] == audit["capability_id"]
        assert capability["semantic_symbol"] == audit["semantic_symbol"]
        assert audit["primary_evidence"]["revision"]
        assert audit["primary_evidence"]["file_sha256"]
        assert (
            subject["descriptor"]["descriptor_sha256"]
            == subject["planned"]["descriptor_sha256"]
        )
        assert subject["descriptor"]["operand_mapping"]


def test_checked_in_fp_differential_evidence_is_content_addressed() -> None:
    evidence = _evidence()
    unsigned = dict(evidence)
    assert unsigned.pop("audit_sha256") == canonical_sha256(unsigned)
    validate_audit(unsigned)
    assert evidence["counts"] == {
        "blocked_subjects": 0,
        "blocked_vectors": 0,
        "executed_vectors": 191,
        "mismatch_subjects": 0,
        "passed_subjects": 28,
        "subjects": 28,
        "test_vectors": 191,
    }
    assert evidence["evidence_level"] == "L3-sampled"
    assert "not-exhaustive" in evidence["coverage_scope"]
    assert "not a proof" in evidence["verdict_definition"]
    assert evidence["toolchain_inventory"]["native_neon"]["status"] == "passed"
    assert evidence["toolchain_inventory"]["rvv"]["backend"] == "spike-rvv-isa"
    assert evidence["toolchain_inventory"]["rvv"]["status"] == "passed"


def test_every_fp_case_has_real_c_authority_lean_and_oracle_evidence() -> None:
    evidence = _evidence()
    for subject in evidence["subjects"]:
        assert subject["status"] == "passed"
        assert subject["c_calls"]
        for call in subject["c_calls"]:
            path = ROOT / call["path"]
            assert path.is_file()
            assert call["file_sha256"]
            assert (
                path.read_text(encoding="utf-8").splitlines()[call["line"] - 1].strip()
                == call["text"]
            )
            assert subject["spelling"] in call["text"]
        authority = subject["official_pinned_source"]
        assert authority["revision"]
        assert authority["path"]
        assert authority["file_sha256"]
        assert authority["source_url"]
        assert subject["official_selector"]["api"] == authority["selector"]
        assert subject["official_selector"]["isa"]
        descriptor = subject["descriptor"]
        assert descriptor["descriptor_sha256"]
        assert descriptor["parameters"]
        assert descriptor["operand_mapping"]
        matrix = subject["case_matrix"]
        assert subject["capability_id"] in matrix["reused_by_capability_ids"]
        assert "independent" in matrix["reuse_scope"]
        lean = subject["lean"]
        assert lean["symbol"]
        assert (ROOT / lean["definition_path"]).is_file()
        assert lean["definition_file_sha256"]
        assert lean["fp32_support_sha256"]
        assert subject["oracle_backend"]["status"] == "passed"
        assert subject["evidence_level"] == "L3-sampled"
        assert "not-exhaustive" in subject["coverage_scope"]
        for case in subject["cases"]:
            assert case["verdict"] == "passed"
            assert case["actual_bits"] == case["expected_bits"]


def test_fp_projection_has_stable_fields_for_master_ledger_join() -> None:
    evidence = _evidence()
    assert LEDGER_PROJECTION.read_text(encoding="utf-8") == render_ledger_projection(
        evidence
    )
    lines = LEDGER_PROJECTION.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 29
    assert lines[0].split(",") == [
        "capability_id",
        "evidence_level",
        "coverage_scope",
        "differential_test_status",
        "oracle_backend",
        "executed_vectors",
        "total_vectors",
        "mismatch_found",
        "evidence_path",
        "evidence_sha256",
        "full_intrinsic_proof",
    ]
    assert all("L3-sampled" in line and line.endswith(",no") for line in lines[1:])


def test_mutated_fp_differential_subject_digest_is_rejected() -> None:
    evidence = _evidence()
    evidence.pop("audit_sha256")
    evidence["subjects"][0]["cases"][0]["actual_bits"] = "0xDEADBEEF"
    with pytest.raises(
        FPDifferentialAuditError, match="subject evidence digest mismatch"
    ):
        validate_audit(evidence)


@pytest.mark.skipif(
    not (
        platform.machine().lower() in {"arm64", "aarch64"}
        and shutil.which("lake")
        and shutil.which("clang")
        and shutil.which("spike")
        and shutil.which("riscv64-elf-ld")
        and Path("/opt/homebrew/opt/llvm/bin/clang").is_file()
    ),
    reason="native AArch64, LLVM RVV assembler, Spike and riscv64 ELF linker required",
)
def test_fp_differential_evidence_reproduces_on_available_toolchains() -> None:
    assert build_audit(ROOT) == _evidence()
