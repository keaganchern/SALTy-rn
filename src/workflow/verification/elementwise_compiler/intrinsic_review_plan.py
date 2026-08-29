"""Partition exact intrinsic audit subjects into reviewable semantic families.

The partition is review workflow metadata, never compiler support authority.  It
must cover every used exact audit subject once and fails closed when a new
operation does not fit an explicit family rule.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence

from .schema import canonical_json, canonical_sha256


class IntrinsicReviewPlanError(RuntimeError):
    """The audit or semantic-family partition is malformed."""


FAMILY_ORDER = (
    "S0-schedule-setvl",
    "S1-structural-plain",
    "S2-structural-immediate",
    "I0-integer-plain",
    "I1-integer-broadcast-normalized",
    "I2-integer-saturating-narrow-shift",
    "I3-integer-mode-sensitive-rounding",
    "FP0-float-arithmetic-abs",
    "FP1-float-predicate-select-sign",
    "FP2-float-maxmin-nan",
    "FP3-float-div-sqrt",
    "FP4-float-conversion",
)


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _family(row: Mapping[str, Any]) -> str:
    role = row["role"]
    spelling = str(row["spelling"])
    if role == "schedule":
        return "S0-schedule-setvl"
    if role == "structural":
        return (
            "S2-structural-immediate"
            if row["immediate_constraints"]
            else "S1-structural-plain"
        )
    if role != "semantic":
        raise IntrinsicReviewPlanError(f"unknown intrinsic role: {role!r}")

    if spelling in {"vmulq_s32", "vmlaq_s32", "vqaddq_s16"}:
        return "I1-integer-broadcast-normalized"
    if any(token in spelling for token in ("qrdmulh", "rshl", "vssra", "vnclip")):
        return "I3-integer-mode-sensitive-rounding"
    if any(
        token in spelling
        for token in ("qmov", "qsub", "vsadd", "shrn", "vnsrl", "vsll", "shlq")
    ):
        return "I2-integer-saturating-narrow-shift"

    is_float = (
        "f32" in spelling
        or spelling.startswith("__riscv_vf")
        or spelling.startswith("__riscv_vmf")
    )
    if is_float:
        if "cvt" in spelling:
            return "FP4-float-conversion"
        if any(token in spelling for token in ("div", "sqrt")):
            return "FP3-float-div-sqrt"
        if any(token in spelling for token in ("max", "min")):
            return "FP2-float-maxmin-nan"
        if any(
            token in spelling
            for token in ("bsl", "calt", "sgnj", "merge", "mfgt", "mfne")
        ):
            return "FP1-float-predicate-select-sign"
        if any(token in spelling for token in ("abs", "add", "sub", "mul")):
            return "FP0-float-arithmetic-abs"
        raise IntrinsicReviewPlanError(
            f"unclassified floating-point intrinsic: {spelling}"
        )
    return "I0-integer-plain"


def build_intrinsic_review_plan(
    repository_root: str | Path,
    *,
    audit_path: str | Path = "verification/elementwise-compiler/IntrinsicAudit.json",
    policy_path: str | Path = "notes/policies/elementwise-intrinsic-review-v2.md",
) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    audit_file = (root / audit_path).resolve()
    policy_file = (root / policy_path).resolve()
    audit = json.loads(audit_file.read_text(encoding="utf-8"))
    if not isinstance(audit, Mapping):
        raise IntrinsicReviewPlanError("intrinsic audit must be a JSON object")
    unsigned_audit = dict(audit)
    audit_sha256 = unsigned_audit.pop("audit_sha256", None)
    if (
        audit.get("schema_version") != 2
        or audit_sha256 != canonical_sha256(unsigned_audit)
    ):
        raise IntrinsicReviewPlanError("intrinsic audit is stale or malformed")
    if not policy_file.is_file():
        raise IntrinsicReviewPlanError("intrinsic review policy is absent")

    grouped: dict[str, list[dict[str, Any]]] = {name: [] for name in FAMILY_ORDER}
    for raw in audit["variants"]:
        if not isinstance(raw, Mapping) or not raw.get("used"):
            continue
        family = _family(raw)
        grouped[family].append(
            {
                "capability_id": raw["capability_id"],
                "audit_variant_sha256": raw["audit_variant_sha256"],
                "architecture": raw["architecture"],
                "spelling": raw["spelling"],
                "function_type": raw["function_type"],
                "argument_count": raw["argument_count"],
                "role": raw["role"],
                "descriptor_sha256": raw["descriptor_sha256"],
                "implementation_sha256": raw["implementation_sha256"],
                "semantic_symbol": raw["semantic_symbol"],
                "immediate_constraints": raw["immediate_constraints"],
                "claim_scope": raw["claim_scope"],
                "architecture_conditions": raw["architecture_conditions"],
                "programs": raw["programs"],
                "primary_evidence": raw["primary_evidence"],
            }
        )
    for subjects in grouped.values():
        subjects.sort(
            key=lambda row: (
                row["architecture"],
                row["spelling"],
                row["capability_id"],
            )
        )
    if sum(map(len, grouped.values())) != audit["counts"]["used_variants"]:
        raise IntrinsicReviewPlanError("review partition does not cover used variants")

    plan: dict[str, Any] = {
        "artifact_kind": "elementwise-intrinsic-review-plan",
        "schema_version": 1,
        "audit_path": Path(audit_path).as_posix(),
        "audit_sha256": audit_sha256,
        "policy_path": Path(policy_path).as_posix(),
        "policy_sha256": _file_sha256(policy_file),
        "target": "all-used-exact-variants",
        "counts": {
            "families": len(FAMILY_ORDER),
            "used_variants": sum(map(len, grouped.values())),
        },
        "families": [
            {"family": family, "count": len(grouped[family]), "subjects": grouped[family]}
            for family in FAMILY_ORDER
        ],
    }
    plan["plan_sha256"] = canonical_sha256(plan)
    return plan


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    plan = build_intrinsic_review_plan(arguments.repository_root)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(canonical_json(plan, pretty=True), encoding="utf-8")
    print(
        json.dumps(
            {item["family"]: item["count"] for item in plan["families"]},
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
