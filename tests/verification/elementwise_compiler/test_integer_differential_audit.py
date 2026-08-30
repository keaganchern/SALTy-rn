from __future__ import annotations

import csv
import io
import json
import platform
import shutil
from pathlib import Path

import jsonschema
import pytest

from workflow.verification.elementwise_compiler.integer_differential_audit import (
    COVERAGE_SCOPE,
    P1_FAMILIES,
    REPAIRED_REGRESSION_CAPABILITY_IDS,
    REPAIRED_REGRESSION_FAMILY,
    STATE_EXCLUSIONS,
    IntegerDifferentialAuditError,
    _make_cases,
    build_audit,
    load_exact_subjects,
    render_ledger_projection,
    validate_audit,
)
from workflow.verification.elementwise_compiler.schema import canonical_sha256


ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "verification/elementwise-compiler"
EVIDENCE = CORPUS / "IntegerDifferentialAudit.json"
LEDGER = CORPUS / "IntegerDifferentialAuditLedger.csv"
SCHEMA = CORPUS / "schemas/integer-differential-audit.schema.json"


def _evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_p1_set_is_dynamically_joined_by_exact_capability_id() -> None:
    subjects = load_exact_subjects(ROOT, CORPUS)
    assert len(subjects) == 20
    assert len({item["capability"]["capability_id"] for item in subjects}) == len(subjects)
    assert {item["semantic_family"] for item in subjects} == (
        P1_FAMILIES | {REPAIRED_REGRESSION_FAMILY}
    )
    assert {
        item["capability"]["capability_id"]
        for item in subjects
        if item["subject_scope"] == "explicit-repaired-regression-unused"
    } == REPAIRED_REGRESSION_CAPABILITY_IDS
    for subject in subjects:
        capability = subject["capability"]
        audit = subject["audit"]
        assert capability["capability_id"] == audit["capability_id"]
        assert capability["semantic_symbol"] == audit["semantic_symbol"]
        assert capability["role"] == "semantic"
        assert audit["primary_evidence"]["revision"]
        assert audit["primary_evidence"]["file_sha256"]


def test_vssra_matrix_covers_shift_mask_boundaries_and_ties() -> None:
    values = {0, 1, 0xFFFFFFFF, 0x80000000, 0x7FFFFFFF}
    shifts = {0, 1, 31, 32, 33, 63, 64, 0xFFFFFFFFFFFFFFFF}
    subjects = [
        item
        for item in load_exact_subjects(ROOT, CORPUS)
        if item["capability"]["spelling"] == "__riscv_vssra_vx_i32m8"
    ]
    assert len(subjects) == 2
    assert {item["capability"]["semantic_symbol"] for item in subjects} == {
        "SALT.Intrinsics.RVV.vssra_vx_i32_mode",
        "SALT.Intrinsics.RVV.vssra_vx_rnu",
    }
    for subject in subjects:
        cases = _make_cases(subject)
        pairs = {(case.inputs[0], case.shift) for case in cases}
        assert {(value, shift) for value in values for shift in shifts} <= pairs
        assert (3, 1) in pairs
        assert (0xFFFFFFFD, 1) in pairs


def test_checked_in_integer_evidence_is_content_addressed_and_schema_valid() -> None:
    evidence = _evidence()
    unsigned = dict(evidence)
    assert unsigned.pop("audit_sha256") == canonical_sha256(unsigned)
    validate_audit(unsigned)
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(evidence)
    assert evidence["counts"] == {
        "blocked_subjects": 0,
        "blocked_vectors": 0,
        "executed_vectors": 232,
        "mismatch_subjects": 0,
        "passed_subjects": 20,
        "subjects": 20,
        "test_vectors": 232,
    }
    assert evidence["coverage_scope"] == COVERAGE_SCOPE
    assert evidence["state_exclusions"] == list(STATE_EXCLUSIONS)
    assert "not a proof" in evidence["verdict_definition"]


def test_every_p1_case_has_c_authority_lean_and_architecture_evidence() -> None:
    evidence = _evidence()
    for subject in evidence["subjects"]:
        assert subject["status"] == "passed"
        assert subject["semantic_family"] in P1_FAMILIES | {REPAIRED_REGRESSION_FAMILY}
        if subject["subject_scope"] == "current-P1-exact":
            assert subject["c_calls"]
            assert subject["registry_used"] is True
        else:
            assert subject["c_calls"] == []
            assert subject["registry_used"] is False
            assert "generated-oracle-calls-exact-intrinsic" in subject["real_c_call_scope"]
        for call in subject["c_calls"]:
            path = ROOT / call["path"]
            assert path.is_file()
            assert path.read_text(encoding="utf-8").splitlines()[call["line"] - 1].strip() == call["text"]
            assert subject["spelling"] in call["text"]
        authority = subject["official_pinned_source"]
        assert authority["revision"]
        assert authority["file_sha256"]
        assert authority["source_url"]
        lean = subject["lean"]
        assert lean["symbol"]
        assert (ROOT / lean["definition_path"]).is_file()
        assert lean["definition_file_sha256"]
        assert subject["oracle_backend"]["status"] == "passed"
        assert "excluded" in subject["state_effect_scope"] or "value-only" in subject["state_effect_scope"]
        for case in subject["cases"]:
            assert case["verdict"] == "passed"
            assert case["actual_bits"] == case["expected_bits"]


def test_integer_projection_has_exact_capability_id_join_fields() -> None:
    evidence = _evidence()
    rendered = render_ledger_projection(evidence)
    assert LEDGER.read_text(encoding="utf-8") == rendered
    rows = list(csv.DictReader(io.StringIO(rendered)))
    assert len(rows) == evidence["counts"]["subjects"]
    assert len({row["capability_id"] for row in rows}) == len(rows)
    assert all(row["evidence_level"] == "L3-sampled" for row in rows)
    assert all(row["differential_test_status"] == "passed-sampled" for row in rows)
    assert all(row["mismatch_found"] == "no" for row in rows)
    assert all(row["full_intrinsic_proof"] == "no" for row in rows)


def test_mutated_integer_subject_digest_is_rejected() -> None:
    evidence = _evidence()
    evidence.pop("audit_sha256")
    evidence["subjects"][0]["cases"][0]["actual_bits"] = "0x00"
    with pytest.raises(IntegerDifferentialAuditError, match="subject evidence digest mismatch"):
        validate_audit(evidence)


@pytest.mark.skipif(
    not (
        platform.machine().lower() in {"arm64", "aarch64"}
        and shutil.which("lake")
        and shutil.which("clang")
        and shutil.which("spike")
        and shutil.which("riscv64-elf-ld")
        and shutil.which("riscv64-elf-objdump")
        and Path("/opt/homebrew/opt/llvm/bin/clang").is_file()
    ),
    reason="native AArch64, LLVM RVV compiler, Spike and riscv64 ELF tools required",
)
def test_integer_differential_evidence_reproduces_on_available_toolchains() -> None:
    assert build_audit(ROOT) == _evidence()
