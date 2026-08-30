from __future__ import annotations

import csv
import io
import json
from pathlib import Path

import jsonschema

from workflow.verification.elementwise_compiler.semantic_audit_ledger import (
    COLUMNS,
    build_ledger,
    render_csv,
)
from workflow.verification.elementwise_compiler.schema import canonical_sha256


ROOT = Path(__file__).resolve().parents[3]
CORPUS = ROOT / "verification/elementwise-compiler"
LEDGER = CORPUS / "SemanticAuditLedger.json"
CSV = ROOT / "notes/audits/intrinsic-semantic-audit.csv"
SCHEMA = CORPUS / "schemas/semantic-audit-ledger.schema.json"


def _record() -> dict:
    return json.loads(LEDGER.read_text(encoding="utf-8"))


def test_semantic_ledger_is_deterministic_exact_id_join() -> None:
    record = _record()
    assert build_ledger(ROOT) == record
    unsigned = dict(record)
    assert unsigned.pop("ledger_sha256") == canonical_sha256(unsigned)
    assert record["join_key"] == "capability_id"
    assert record["columns"] == list(COLUMNS)
    assert record["counts"]["variants"] == len(record["rows"])
    assert len({row["capability_id"] for row in record["rows"]}) == len(record["rows"])
    assert record["counts"]["used"] + record["counts"]["unused"] == len(record["rows"])
    assert all("[object Object]" not in str(row) for row in record["rows"])


def test_semantic_ledger_csv_is_the_exact_projection() -> None:
    record = _record()
    rendered = render_csv(record)
    assert CSV.read_text(encoding="utf-8") == rendered
    rows = list(csv.DictReader(io.StringIO(rendered)))
    assert len(rows) == record["counts"]["variants"]
    assert tuple(rows[0]) == COLUMNS


def test_shift_repairs_have_separate_sampled_evidence() -> None:
    rows = {row["capability_id"]: row for row in _record()["rows"]}
    for capability_id in (
        "intrinsic:rvv:__riscv_vssra_vx_i32m8:19e343bce1b4b97b",
        "intrinsic:rvv:__riscv_vssra_vx_i32m8:c47e1ab152864cb9",
    ):
        row = rows[capability_id]
        assert row["deep_verdict"] == "confirmed"
        assert row["evidence_level"] == "L3-sampled"
        assert row["differential_test_status"] == "passed_sampled:43"
        assert "43 sampled vectors" in row["deep_evidence"]
    neon = rows["intrinsic:neon:vrshlq_s32:3e1dfee0c446d378"]
    assert neon["evidence_level"] == "L3-sampled"
    assert neon["differential_test_status"].startswith("passed_sampled:")


def test_generator_evidence_does_not_claim_isa_correspondence() -> None:
    rows = [
        row for row in _record()["rows"]
        if row["evidence_level"] in {"L2-traceable-lowering", "L3-generator-mutation"}
    ]
    assert rows
    assert all("ISA correspondence pending" in row["deep_evidence"] for row in rows)
    assert all("not_isa_differential" in row["differential_test_status"] for row in rows)


def test_semantic_ledger_schema_validates() -> None:
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    jsonschema.Draft202012Validator(schema).validate(_record())
    assert all(
        parent["path"] != "notes/audits/intrinsic-semantic-audit.csv"
        for parent in _record()["parents"]
    )
