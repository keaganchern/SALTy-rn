from __future__ import annotations

import csv
import io
import json
import platform
import shutil
from pathlib import Path

import jsonschema
import pytest

from workflow.verification.elementwise_compiler.plain_integer_differential_audit import (
    COVERAGE_SCOPE,
    FAMILIES,
    LEGACY_CONTEXTUAL_IDS,
    PlainIntegerDifferentialAuditError,
    build_audit,
    load_exact_subjects,
    render_ledger_projection,
    validate_audit,
)
from workflow.verification.elementwise_compiler.schema import canonical_sha256


ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "verification/elementwise-compiler"
EVIDENCE = CORPUS / "PlainIntegerDifferentialAudit.json"
LEDGER = CORPUS / "PlainIntegerDifferentialAuditLedger.csv"
SCHEMA = CORPUS / "schemas/plain-integer-differential-audit.schema.json"


def _evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_subject_set_is_exactly_current_i0_i1_after_legacy_cleanup() -> None:
    subjects = load_exact_subjects(ROOT)
    assert len(subjects) == 65
    assert len({item["capability"]["capability_id"] for item in subjects}) == 65
    assert sum(item["subject_scope"] == "current-exact" for item in subjects) == 65
    assert {
        item["capability"]["capability_id"]
        for item in subjects
        if item["subject_scope"] == "explicit-unused-cleanup-candidate"
    } == LEGACY_CONTEXTUAL_IDS
    assert FAMILIES <= {item["semantic_family"] for item in subjects}


def test_checked_in_evidence_is_content_addressed_and_schema_valid() -> None:
    evidence = _evidence()
    unsigned = dict(evidence)
    assert unsigned.pop("audit_sha256") == canonical_sha256(unsigned)
    validate_audit(unsigned)
    jsonschema.Draft202012Validator(
        json.loads(SCHEMA.read_text(encoding="utf-8"))
    ).validate(evidence)
    assert evidence["coverage_scope"] == COVERAGE_SCOPE
    assert evidence["counts"] == {
        "blocked_subjects": 0,
        "conditional_subjects": 3,
        "current_subjects": 65,
        "executed_vectors": 378,
        "legacy_cleanup_candidates": 0,
        "mismatch_subjects": 0,
        "passed_subjects": 62,
        "subjects": 65,
        "test_vectors": 378,
    }


def test_i1_rows_are_conditional_and_fail_closed() -> None:
    evidence = _evidence()
    contextual = [row for row in evidence["subjects"] if row["context_condition"]]
    assert len(contextual) == 3
    assert all(row["status"] == "conditional" for row in contextual)
    assert all(
        any(item["transform"] == "unbroadcast" for item in row["descriptor_operand_lowering"])
        for row in contextual
    )
    assert not LEGACY_CONTEXTUAL_IDS
    probe = evidence["broadcast_provenance_audit"]
    assert probe["nonuniform_vector_mutation"]["status"] == "passed-rejected"
    assert probe["nonuniform_vector_mutation"]["error_type"] == "OperandProvenanceError"
    assert {item["spelling"] for item in probe["positive_occurrences"]} == {
        "vmulq_s32", "vmlaq_s32", "vqaddq_s16"
    }


def test_every_row_has_exact_c_descriptor_authority_lean_and_oracle_trace() -> None:
    for row in _evidence()["subjects"]:
        assert row["descriptor_sha256"]
        assert row["descriptor_operand_lowering"]
        if row["registry_used"]:
            assert row["c_calls"]
        else:
            pytest.fail("every current I0/I1 audit subject should be used")
        for call in row["c_calls"]:
            path = ROOT / call["path"]
            assert path.is_file()
            assert path.read_text(encoding="utf-8").splitlines()[call["line"] - 1].strip() == call["text"]
        assert row["official_pinned_source"]["revision"]
        assert row["official_pinned_source"]["file_sha256"]
        assert row["lean"]["definition_sha256"]
        assert row["oracle_backend"]["status"] == "passed"
        assert row["execution_status"] == "passed"
        assert all(case["verdict"] == "passed" for case in row["cases"])


def test_projection_is_keyed_by_exact_capability_id_and_denies_full_proof() -> None:
    evidence = _evidence()
    rendered = render_ledger_projection(evidence)
    assert LEDGER.read_text(encoding="utf-8") == rendered
    rows = list(csv.DictReader(io.StringIO(rendered)))
    assert len(rows) == 65
    assert len({row["capability_id"] for row in rows}) == 65
    assert all(row["evidence_level"] == "L3-sampled" for row in rows)
    assert all(row["full_intrinsic_proof"] == "no" for row in rows)


def test_mutated_subject_digest_is_rejected() -> None:
    evidence = _evidence()
    evidence.pop("audit_sha256")
    evidence["subjects"][0]["cases"][0]["actual_bits"] = "0x00"
    with pytest.raises(PlainIntegerDifferentialAuditError, match="subject digest mismatch"):
        validate_audit(evidence)


@pytest.mark.skipif(
    not (
        platform.machine().lower() in {"arm64", "aarch64"}
        and shutil.which("lake") and shutil.which("clang") and shutil.which("spike")
        and shutil.which("riscv64-elf-ld") and shutil.which("riscv64-elf-objdump")
        and Path("/opt/homebrew/opt/llvm/bin/clang").is_file()
    ),
    reason="native AArch64, Lean, LLVM RVV, Spike and RISC-V ELF tools required",
)
def test_plain_integer_evidence_reproduces_on_available_toolchains() -> None:
    assert build_audit(ROOT) == _evidence()
