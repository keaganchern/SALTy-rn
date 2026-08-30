"""Build the deterministic all-capability semantic-audit ledger.

The ledger joins the canonical registry/audit inventory, historical independent
manual assessments, and current sampled or generator-boundary audits by exact
``capability_id``.  It is a tracking artifact, not a proof-acceptance input.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from collections import Counter
from pathlib import Path
from typing import Any, Mapping, Sequence

from .schema import canonical_json, canonical_sha256


class SemanticAuditLedgerError(RuntimeError):
    """The audit inputs or exact-ID joins are incomplete or inconsistent."""


COLUMNS = (
    "capability_id", "architecture", "spelling", "function_type", "role",
    "semantic_family", "used_current_corpus", "dependent_programs",
    "real_c_call_files", "lean_semantic_symbol", "existing_review_status",
    "existing_reviewer", "existing_review_scope", "existing_review_sha256",
    "descriptor_sha256", "implementation_sha256", "architecture_conditions",
    "immediate_constraints", "official_authority", "official_prototype",
    "official_instruction_or_selector", "official_source_path",
    "official_source_line", "official_source_url", "static_checks",
    "risk_priority", "auditor_risk", "deep_audit_round", "deep_verdict",
    "evidence_level", "confidence", "deep_evidence", "finding", "next_action",
    "differential_test_status", "adequacy_proof_status",
    "final_semantic_audit_complete",
)

ROUND1_PATHS = (
    "notes/audits/round1-assessments/fp.json",
    "notes/audits/round1-assessments/neon-integer.json",
    "notes/audits/round1-assessments/rvv-integer.json",
)

DIFFERENTIAL_PATHS = {
    "fp": "verification/elementwise-compiler/FPDifferentialAudit.json",
    "integer": "verification/elementwise-compiler/IntegerDifferentialAudit.json",
    "structural": "verification/elementwise-compiler/StructuralDifferentialAudit.json",
    "plain_integer": "verification/elementwise-compiler/PlainIntegerDifferentialAudit.json",
}


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _json(path: Path, *, optional: bool = False) -> dict[str, Any]:
    if optional and not path.is_file():
        return {"subjects": []}
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise SemanticAuditLedgerError(f"cannot read audit input {path}") from error
    if not isinstance(value, dict):
        raise SemanticAuditLedgerError(f"audit input is not an object: {path}")
    return value


def _stringify(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return "; ".join(
            json.dumps(item, sort_keys=True, separators=(",", ":"))
            if isinstance(item, (dict, list)) else str(item)
            for item in value
        )
    if isinstance(value, dict):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value)


def _normalize_verdict(value: object) -> str:
    text = str(value or "needs_deep_audit").lower().replace("-", "_")
    accepted = {
        "confirmed", "conditional", "needs_deep_audit", "suspected_bug",
        "confirmed_bug", "unused_unreviewed",
    }
    if text in accepted:
        return text
    if "bug" in text:
        return "suspected_bug"
    if "condition" in text:
        return "conditional"
    if "confirm" in text or "pass" in text:
        return "confirmed"
    return "needs_deep_audit"


def _confidence(verdict: str) -> str:
    return {
        "confirmed_bug": "high_reproduced",
        "confirmed": "medium_sampled_or_manual",
        "conditional": "medium_conditional",
        "suspected_bug": "low_pending_reproduction",
    }.get(verdict, "unconfirmed")


def _risk(row: Mapping[str, Any], family: str) -> str:
    if family.startswith("FP"):
        return "P0"
    if family in {"I2-integer-saturating-narrow-shift", "I3-integer-mode-sensitive-rounding"}:
        return "P1"
    if row["role"] != "semantic" or any(
        token in row["spelling"]
        for token in ("load", "store", "ld1", "st1", "ext", "combine", "merge", "setvl", "reinterpret")
    ):
        return "P2"
    return "P3"


def _subjects_by_id(payload: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    subjects = payload.get("subjects", [])
    if not isinstance(subjects, list):
        raise SemanticAuditLedgerError("differential audit subjects are malformed")
    result: dict[str, Mapping[str, Any]] = {}
    for subject in subjects:
        if not isinstance(subject, Mapping) or not isinstance(subject.get("capability_id"), str):
            raise SemanticAuditLedgerError("differential audit subject lacks capability_id")
        capability_id = str(subject["capability_id"])
        if capability_id in result:
            raise SemanticAuditLedgerError(f"duplicate differential subject {capability_id}")
        result[capability_id] = subject
    return result


def build_ledger(repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    corpus = root / "verification/elementwise-compiler"
    audit_path = corpus / "IntrinsicAudit.json"
    registry_path = corpus / "IntrinsicRegistry.json"
    plan_path = corpus / "IntrinsicReviewPlan.json"
    audit = _json(audit_path)
    registry = _json(registry_path)
    plan = _json(plan_path)

    audit_rows = audit.get("variants")
    registry_rows = registry.get("variants")
    if not isinstance(audit_rows, list) or not isinstance(registry_rows, list):
        raise SemanticAuditLedgerError("registry or intrinsic audit inventory is malformed")
    review_by_id = {
        row["capability"]["capability_id"]: row.get("review")
        for row in registry_rows
    }
    family_by_id = {
        subject["capability_id"]: family["family"]
        for family in plan["families"]
        for subject in family["subjects"]
    }

    manual_by_id: dict[str, Mapping[str, Any]] = {}
    parents = [audit_path, registry_path, plan_path]
    for relative in ROUND1_PATHS:
        path = root / relative
        parents.append(path)
        payload = _json(path)
        for row in payload.get("rows", []):
            capability_id = row.get("capability_id")
            if not isinstance(capability_id, str):
                raise SemanticAuditLedgerError(f"manual row lacks capability_id: {path}")
            manual_by_id[capability_id] = row

    differential: dict[str, dict[str, Mapping[str, Any]]] = {}
    for name, relative in DIFFERENTIAL_PATHS.items():
        path = root / relative
        payload = _json(path, optional=True)
        if path.is_file():
            parents.append(path)
        differential[name] = _subjects_by_id(payload)

    rows: list[dict[str, str]] = []
    for audit_row in audit_rows:
        capability_id = audit_row["capability_id"]
        manual = manual_by_id.get(capability_id, {})
        review = review_by_id.get(capability_id)
        family = family_by_id.get(capability_id, "UNUSED-unpartitioned")
        fp = differential["fp"].get(capability_id)
        integer = differential["integer"].get(capability_id)
        structural = differential["structural"].get(capability_id)
        plain = differential["plain_integer"].get(capability_id)
        architecture_sample = next(
            (sample for sample in (plain, integer, fp) if sample and sample.get("status") == "passed"),
            None,
        )
        verdict = _normalize_verdict(
            manual.get("deep_verdict")
            if audit_row["used"]
            else manual.get("deep_verdict", "unused_unreviewed")
        )
        if architecture_sample and verdict in {"needs_deep_audit", "unused_unreviewed"}:
            verdict = "confirmed"

        if architecture_sample:
            cases = architecture_sample.get("cases", [])
            evidence_level = "L3-sampled"
            differential_status = f"passed_sampled:{len(cases)}"
        elif structural and structural.get("status") == "passed":
            evidence_level = str(structural["evidence_level"])
            differential_status = (
                "passed_generator_mutation:not_isa_differential"
                if evidence_level.startswith("L3")
                else "traceable_lowering_only:not_isa_differential"
            )
        else:
            evidence_level = (
                "L2-manual-first-pass"
                if verdict in {"confirmed", "conditional", "suspected_bug", "confirmed_bug"}
                else "L1-provenance"
            )
            differential_status = str(manual.get("differential_test_status", "not_run"))

        evidence_parts = [_stringify(manual.get("evidence") or manual.get("deep_evidence"))]
        for name, sample in (("FP", fp), ("Integer", integer), ("PlainInteger", plain)):
            if sample:
                evidence_parts.append(
                    f"verification/elementwise-compiler/{name}DifferentialAudit.json:"
                    f"{len(sample.get('cases', []))} sampled vectors"
                )
        if structural:
            evidence_parts.append(
                "verification/elementwise-compiler/StructuralDifferentialAudit.json:"
                f"{structural['evidence_level']}; ISA correspondence pending"
            )
        evidence_text = "; ".join(part for part in evidence_parts if part)
        finding = _stringify(manual.get("finding") or manual.get("reason"))
        if architecture_sample:
            scope = architecture_sample.get("subject_scope")
            suffix = f"{len(architecture_sample.get('cases', []))} sampled vectors matched"
            finding = "; ".join(part for part in (finding, str(scope or ""), suffix) if part)
            next_action = (
                f"Retain the {len(architecture_sample.get('cases', []))}-case architecture/Lean "
                "regression; full independent ISA correspondence remains separate"
            )
        else:
            next_action = _stringify(
                manual.get("next_action", "Run an independent edge-case semantic audit")
            )

        official = audit_row.get("primary_evidence", {})
        c_side = "source" if audit_row["architecture"] == "neon" else "target"
        c_files = [f"kernels/{c_side}/{program}.c" for program in audit_row.get("programs", [])]
        instruction = official.get("instruction") or official.get("isa_selector") or official.get("selector", "")
        rows.append({
            "capability_id": capability_id,
            "architecture": audit_row["architecture"],
            "spelling": audit_row["spelling"],
            "function_type": audit_row["function_type"],
            "role": audit_row["role"],
            "semantic_family": family,
            "used_current_corpus": "yes" if audit_row["used"] else "no",
            "dependent_programs": _stringify(audit_row.get("programs", [])),
            "real_c_call_files": _stringify(c_files),
            "lean_semantic_symbol": audit_row.get("semantic_symbol") or "",
            "existing_review_status": "approved_current_hash" if review else "not_reviewed",
            "existing_reviewer": "" if not review else review.get("reviewer", ""),
            "existing_review_scope": "" if not review else review.get("claim_scope", ""),
            "existing_review_sha256": "" if not review else review.get("review_sha256", ""),
            "descriptor_sha256": audit_row["descriptor_sha256"],
            "implementation_sha256": audit_row["implementation_sha256"],
            "architecture_conditions": _stringify(audit_row.get("architecture_conditions", [])),
            "immediate_constraints": _stringify(audit_row.get("immediate_constraints", [])),
            "official_authority": official.get("authority", ""),
            "official_prototype": official.get("prototype", ""),
            "official_instruction_or_selector": instruction,
            "official_source_path": official.get("path", ""),
            "official_source_line": str(official.get("line") or official.get("isa_line") or ""),
            "official_source_url": official.get("source_url") or official.get("isa_source_url", ""),
            "static_checks": _stringify(audit_row.get("static_checks", [])),
            "risk_priority": _risk(audit_row, family),
            "auditor_risk": _stringify(manual.get("risk")),
            "deep_audit_round": "2026-08-30-multi-stage" if manual or fp or integer or structural or plain else "not_started",
            "deep_verdict": verdict,
            "evidence_level": evidence_level,
            "confidence": _confidence(verdict),
            "deep_evidence": evidence_text,
            "finding": finding,
            "next_action": next_action,
            "differential_test_status": differential_status,
            "adequacy_proof_status": _stringify(manual.get("adequacy_proof_status", "not_established")),
            "final_semantic_audit_complete": "no",
        })

    rows.sort(key=lambda row: (
        row["risk_priority"], row["architecture"], row["spelling"], row["capability_id"]
    ))
    ids = [row["capability_id"] for row in rows]
    if len(rows) != len(audit_rows) or len(rows) != len(registry_rows):
        raise SemanticAuditLedgerError(
            f"inventory mismatch: ledger={len(rows)} audit={len(audit_rows)} registry={len(registry_rows)}"
        )
    if len(set(ids)) != len(ids):
        raise SemanticAuditLedgerError("duplicate capability_id in semantic ledger")
    if set(ids) != set(review_by_id):
        raise SemanticAuditLedgerError("semantic ledger and registry exact IDs differ")

    parent_records = [
        {"path": path.relative_to(root).as_posix(), "sha256": _sha256(path)}
        for path in sorted(set(parents))
    ]
    verdicts = Counter(row["deep_verdict"] for row in rows)
    levels = Counter(row["evidence_level"] for row in rows)
    record: dict[str, Any] = {
        "artifact_kind": "elementwise-semantic-audit-ledger",
        "schema_version": 1,
        "join_key": "capability_id",
        "claim_scope": "tracked-evidence-level-only;not-proof-acceptance",
        "parents": parent_records,
        "counts": {
            "variants": len(rows),
            "used": sum(row["used_current_corpus"] == "yes" for row in rows),
            "unused": sum(row["used_current_corpus"] == "no" for row in rows),
            "current_reviews": sum(row["existing_review_status"] == "approved_current_hash" for row in rows),
            "verdicts": dict(sorted(verdicts.items())),
            "evidence_levels": dict(sorted(levels.items())),
        },
        "columns": list(COLUMNS),
        "rows": rows,
    }
    record["ledger_sha256"] = canonical_sha256(record)
    return record


def render_csv(record: Mapping[str, Any]) -> str:
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in record["rows"]:
        writer.writerow({column: row.get(column, "") for column in COLUMNS})
    return stream.getvalue()


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("verification/elementwise-compiler/SemanticAuditLedger.json"),
    )
    parser.add_argument(
        "--csv-output",
        type=Path,
        default=Path("notes/audits/intrinsic-semantic-audit.csv"),
    )
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()
    output = arguments.output if arguments.output.is_absolute() else root / arguments.output
    csv_output = (
        arguments.csv_output if arguments.csv_output.is_absolute() else root / arguments.csv_output
    )
    record = build_ledger(root)
    rendered = canonical_json(record, pretty=True)
    rendered_csv = render_csv(record)
    if arguments.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
            raise SemanticAuditLedgerError(f"stale semantic audit ledger: {output}")
        if not csv_output.is_file() or csv_output.read_text(encoding="utf-8") != rendered_csv:
            raise SemanticAuditLedgerError(f"stale semantic audit CSV: {csv_output}")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        csv_output.parent.mkdir(parents=True, exist_ok=True)
        csv_output.write_text(rendered_csv, encoding="utf-8")
    print(json.dumps(record["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
