from __future__ import annotations

import csv
import io
import json
import shutil
from pathlib import Path

import jsonschema
import pytest

from workflow.verification.elementwise_compiler.schema import canonical_sha256
from workflow.verification.elementwise_compiler.structural_differential_audit import (
    COVERAGE_SCOPE,
    L2,
    L3,
    SELECTED_FAMILIES,
    StructuralDifferentialAuditError,
    _call_sites,
    build_audit,
    load_exact_subjects,
    render_ledger_projection,
    validate_audit,
)


ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "verification/elementwise-compiler"
EVIDENCE = CORPUS / "StructuralDifferentialAudit.json"
LEDGER = CORPUS / "StructuralDifferentialAuditLedger.csv"
SCHEMA = CORPUS / "schemas/structural-differential-audit.schema.json"


def _evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def test_exact_used_structural_set_is_joined_without_name_aliasing() -> None:
    subjects = load_exact_subjects(ROOT, CORPUS)
    assert len(subjects) == 68
    assert len({item["capability"]["capability_id"] for item in subjects}) == 68
    assert {item["family"] for item in subjects} == set(SELECTED_FAMILIES)
    assert {item["capability"]["role"] for item in subjects} == {
        "schedule",
        "structural",
    }
    for subject in subjects:
        capability = subject["capability"]
        assert capability["capability_id"] == subject["audit"]["capability_id"]
        assert capability["descriptor_sha256"] == subject["planned"]["descriptor_sha256"]


def test_lexical_scanner_ignores_comments_and_strings(tmp_path: Path) -> None:
    source = tmp_path / "probe.c"
    source.write_text(
        "// vext_s8(a, b, 2)\n"
        "const char* text = \"vext_s8(a, b, 2)\";\n"
        "value = vext_s8(left, nested(right, 1), 4);\n",
        encoding="utf-8",
    )
    calls = _call_sites(source, "vext_s8", "neon", "probe")
    assert len(calls) == 1
    assert calls[0]["assigned_to"] == "value"
    assert calls[0]["arguments"] == ["left", "nested(right, 1)", "4"]


def test_checked_in_structural_evidence_is_content_addressed_and_schema_valid() -> None:
    evidence = _evidence()
    unsigned = dict(evidence)
    assert unsigned.pop("audit_sha256") == canonical_sha256(unsigned)
    validate_audit(unsigned)
    jsonschema.Draft202012Validator(
        json.loads(SCHEMA.read_text(encoding="utf-8"))
    ).validate(evidence)
    assert evidence["coverage_scope"] == COVERAGE_SCOPE
    assert evidence["counts"]["subjects"] == 68
    assert evidence["counts"]["passed_subjects"] == 68
    assert evidence["counts"]["families"] == {
        "S0-schedule-setvl": 3,
        "S1-structural-plain": 57,
        "S2-structural-immediate": 8,
    }
    assert evidence["counts"]["l2_traceable_subjects"] > 0
    assert evidence["counts"]["l3_generator_mutation_subjects"] > 0
    assert evidence["counts"]["isa_correctness_validated_subjects"] == 0
    assert evidence["counts"]["semantic_correspondence_pending_subjects"] == 68
    assert "not an ISA correctness proof" in evidence["verdict_definition"]


def test_every_subject_binds_real_calls_descriptor_lowerer_and_manifest() -> None:
    for subject in _evidence()["subjects"]:
        assert subject["status"] == "passed"
        assert subject["issues"] == []
        assert subject["descriptor"]["descriptor_sha256"]
        assert subject["official_pinned_source"]["revision"]
        assert subject["official_pinned_source"]["file_sha256"]
        lowering = subject["lowering"]
        assert lowering["all_source_arguments_accounted_for"] is True
        assert len(lowering["operand_roles"]) == len(subject["c_calls"][0]["arguments"])
        for anchor in lowering["anchors"]:
            path = ROOT / anchor["path"]
            assert path.is_file()
            assert anchor["file_sha256"] == __import__("hashlib").sha256(path.read_bytes()).hexdigest()
            lines = path.read_text(encoding="utf-8").splitlines()
            assert all(anchor["needle"] in lines[line - 1] for line in anchor["lines"])
        for call in subject["c_calls"]:
            path = ROOT / call["path"]
            assert path.is_file()
            assert subject["spelling"] in path.read_text(encoding="utf-8").splitlines()[call["line"] - 1]
            assert len(call["arguments"]) == len(lowering["operand_roles"])
        provenance = subject["provenance_checks"]
        assert provenance["all_call_arities_exact"] is True
        assert provenance["all_source_arguments_accounted_for"] is True
        assert len(provenance["manifest_bindings"]) == len(provenance["program_set_exact"])
        for binding in provenance["manifest_bindings"]:
            assert binding["exact_capability_bound"] is True
            assert (ROOT / binding["manifest_path"]).is_file()
            assert (ROOT / binding["models_path"]).is_file()


def test_immediates_and_active_length_are_not_silently_lost() -> None:
    subjects = _evidence()["subjects"]
    s2 = [row for row in subjects if row["semantic_family"] == "S2-structural-immediate"]
    assert len(s2) == 8
    assert all(row["provenance_checks"]["immediate_values"] for row in s2)
    assert all(
        row["provenance_checks"]["immediates_consumed_by_structural_lowering"]
        for row in s2
    )
    schedules = [row for row in subjects if row["semantic_family"] == "S0-schedule-setvl"]
    assert len(schedules) == 3
    assert all(call["assigned_to"] == "vl" for row in schedules for call in row["c_calls"])
    rvv_vl = [
        row
        for row in subjects
        if "active-length" in row["lowering"]["operand_roles"]
    ]
    assert rvv_vl
    assert all(row["provenance_checks"]["active_length_call_count"] for row in rvv_vl)
    assert all(
        call["arguments"][row["lowering"]["operand_roles"].index("active-length")]
        == "vl"
        for row in rvv_vl
        for call in row["c_calls"]
    )


def test_l3_is_only_generator_boundary_evidence() -> None:
    evidence = _evidence()
    assert {probe["probe"] for probe in evidence["generator_mutation_probes"]} == {
        "rvv-active-length-expression",
        "neon-slide-immediate",
        "neon-tail-lane-selector",
        "neon-negated-broadcast-roundtrip",
    }
    assert all(probe["status"] == "passed" for probe in evidence["generator_mutation_probes"])
    levels = {row["evidence_level"] for row in evidence["subjects"]}
    assert levels == {L2, L3}
    assert all("not-isa-adequacy" in row["coverage_scope"] for row in evidence["subjects"])
    assert all(
        row["semantic_correspondence_status"]
        in {"not-independently-validated", "generator-boundary-validated-only"}
        for row in evidence["subjects"]
    )
    assert all(row["evidence_level"] == L3 for row in evidence["subjects"] if row["semantic_family"] == "S2-structural-immediate")


def test_structural_projection_is_exact_capability_keyed() -> None:
    evidence = _evidence()
    rendered = render_ledger_projection(evidence)
    assert LEDGER.read_text(encoding="utf-8") == rendered
    rows = list(csv.DictReader(io.StringIO(rendered)))
    assert len(rows) == 68
    assert len({row["capability_id"] for row in rows}) == 68
    assert {row["evidence_level"] for row in rows} == {L2, L3}
    assert all(row["audit_status"] == "passed" for row in rows)
    assert all(
        row["semantic_correspondence_status"]
        in {"not-independently-validated", "generator-boundary-validated-only"}
        for row in rows
    )
    assert all(row["isa_correctness_proof"] == "no" for row in rows)


def test_mutated_subject_digest_is_rejected() -> None:
    evidence = _evidence()
    evidence.pop("audit_sha256")
    evidence["subjects"][0]["c_calls"][0]["arguments"][0] = "silently_changed"
    with pytest.raises(
        StructuralDifferentialAuditError, match="subject evidence digest mismatch"
    ):
        validate_audit(evidence)


@pytest.mark.skipif(shutil.which("clang") is None, reason="system clang required")
def test_structural_audit_reproduces_with_production_generator() -> None:
    assert build_audit(ROOT) == _evidence()
