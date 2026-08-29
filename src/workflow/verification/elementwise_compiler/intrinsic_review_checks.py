"""Build the machine-checkable review pack for every used exact intrinsic."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from workflow.verification.lean_backend.descriptor import canonical_spec_digest
from workflow.verification.lean_backend.intrinsic_index import (
    CANONICAL_INTRINSIC_INDEX,
)
from workflow.verification.lean_backend.schema import SemanticIntrinsic

from .schema import canonical_json, canonical_sha256


class IntrinsicReviewCheckError(RuntimeError):
    """A planned subject lacks its exact implementation or falsification anchor."""


FAMILY_ANCHORS: Mapping[str, tuple[str, ...]] = {
    "S0-schedule-setvl": (
        "tests/verification/lean_backend/test_binding.py",
        "tests/verification/lean_backend/test_case_emit.py",
    ),
    "S1-structural-plain": (
        "tests/verification/elementwise_compiler/test_compiler.py",
        "tests/verification/elementwise_compiler/test_wide_generation.py",
    ),
    "S2-structural-immediate": (
        "tests/verification/lean_backend/test_case_emit.py",
        "tests/verification/elementwise_compiler/test_wide_generation.py",
    ),
    "I0-integer-plain": (
        "src/verification_bw/lean/SALT/Test/IntegerIntrinsics.lean",
    ),
    "I1-integer-broadcast-normalized": (
        "tests/verification/lean_backend/test_binding.py",
        "tests/verification/lean_backend/test_emit_lean.py",
    ),
    "I2-integer-saturating-narrow-shift": (
        "src/verification_bw/lean/SALT/Test/IntegerIntrinsics.lean",
        "tests/verification/lean_backend/test_intrinsic_index.py",
    ),
    "I3-integer-mode-sensitive-rounding": (
        "src/verification_bw/lean/SALT/Test/IntegerIntrinsics.lean",
        "src/verification_bw/lean/SALT/Proof/RoundingEquiv.lean",
    ),
    "FP0-float-arithmetic-abs": (
        "src/verification_bw/lean/SALT/Test/FP32.lean",
    ),
    "FP1-float-predicate-select-sign": (
        "src/verification_bw/lean/SALT/Test/FP32.lean",
    ),
    "FP2-float-maxmin-nan": (
        "src/verification_bw/lean/SALT/Test/FP32.lean",
    ),
    "FP3-float-div-sqrt": (
        "src/verification_bw/lean/SALT/Test/FP32.lean",
    ),
    "FP4-float-conversion": (
        "src/verification_bw/lean/SALT/Test/FP32.lean",
    ),
}


def _load_bound(path: Path, digest_field: str) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise IntrinsicReviewCheckError(f"{path.name} is not an object")
    unsigned = dict(value)
    digest = unsigned.pop(digest_field, None)
    if digest != canonical_sha256(unsigned):
        raise IntrinsicReviewCheckError(f"{path.name} digest disagrees")
    return value


def build_intrinsic_review_checks(repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    corpus = root / "verification/elementwise-compiler"
    audit = _load_bound(corpus / "IntrinsicAudit.json", "audit_sha256")
    plan = _load_bound(corpus / "IntrinsicReviewPlan.json", "plan_sha256")
    if plan["audit_sha256"] != audit["audit_sha256"]:
        raise IntrinsicReviewCheckError("review plan has a stale audit parent")

    descriptors = {
        canonical_spec_digest(variant.spec): variant.spec
        for variant in CANONICAL_INTRINSIC_INDEX.variants
    }
    lean_sources = {
        "neon": root / "src/verification_bw/lean/SALT/Intrinsics/Neon.lean",
        "rvv": root / "src/verification_bw/lean/SALT/Intrinsics/RVV.lean",
    }
    shared_sources = tuple(
        root / relative
        for relative in (
            "src/verification_bw/lean/SALT/Basic.lean",
            "src/verification_bw/lean/SALT/Intrinsics/FP32.lean",
            "src/verification_bw/lean/SALT/Kernel/Schedule.lean",
        )
    )
    for path in (*lean_sources.values(), *shared_sources):
        source = path.read_text(encoding="utf-8")
        if re.search(r"(^|\s)(axiom|sorry)(\s|$)", source):
            raise IntrinsicReviewCheckError(f"forbidden Lean token in {path}")

    audit_by_id = {row["capability_id"]: row for row in audit["variants"]}
    subjects: list[dict[str, Any]] = []
    family_checks: list[dict[str, Any]] = []
    for family in plan["families"]:
        family_name = family["family"]
        anchors = FAMILY_ANCHORS.get(family_name)
        if anchors is None:
            raise IntrinsicReviewCheckError(f"unrecognized review family: {family_name}")
        anchor_records = []
        for relative in anchors:
            path = root / relative
            if not path.is_file() or not path.read_text(encoding="utf-8").strip():
                raise IntrinsicReviewCheckError(f"missing family anchor: {relative}")
            anchor_records.append(
                {"path": relative, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
            )
        family_checks.append(
            {
                "family": family_name,
                "status": "passed",
                "subject_count": family["count"],
                "anchors": anchor_records,
            }
        )
        for subject in family["subjects"]:
            audit_row = audit_by_id.get(subject["capability_id"])
            if audit_row is None or not audit_row["used"]:
                raise IntrinsicReviewCheckError("planned subject is absent from used audit")
            spec = descriptors.get(subject["descriptor_sha256"])
            if spec is None:
                raise IntrinsicReviewCheckError("planned descriptor is not canonical")
            definition = None
            if isinstance(spec, SemanticIntrinsic):
                definition = spec.lean_name.rsplit(".", 1)[-1]
                source = lean_sources[subject["architecture"]].read_text(encoding="utf-8")
                if re.search(rf"(?m)^def\s+{re.escape(definition)}\b", source) is None:
                    raise IntrinsicReviewCheckError(
                        f"Lean semantic definition is absent: {spec.lean_name}"
                    )
            evidence = audit_row["primary_evidence"]
            if evidence.get("selector") != subject["spelling"]:
                raise IntrinsicReviewCheckError("primary evidence selector mismatch")
            subjects.append(
                {
                    "capability_id": subject["capability_id"],
                    "audit_variant_sha256": subject["audit_variant_sha256"],
                    "family": family_name,
                    "descriptor_sha256": subject["descriptor_sha256"],
                    "implementation_sha256": subject["implementation_sha256"],
                    "lean_definition": definition,
                    "claim_scope": subject["claim_scope"],
                    "architecture_conditions": subject["architecture_conditions"],
                    "status": "passed",
                }
            )
    subjects.sort(key=lambda row: row["capability_id"])
    if len(subjects) != 180 or len({row["capability_id"] for row in subjects}) != 180:
        raise IntrinsicReviewCheckError("review check pack does not have 180 exact subjects")
    report: dict[str, Any] = {
        "artifact_kind": "elementwise-intrinsic-review-checks",
        "schema_version": 1,
        "audit_sha256": audit["audit_sha256"],
        "plan_sha256": plan["plan_sha256"],
        "scope": "lean-value-model-only",
        "counts": {"families": len(family_checks), "passed_subjects": len(subjects)},
        "family_checks": family_checks,
        "subjects": subjects,
    }
    report["checks_sha256"] = canonical_sha256(report)
    return report


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    arguments = parser.parse_args(argv)
    checks = build_intrinsic_review_checks(arguments.repository_root)
    arguments.output.parent.mkdir(parents=True, exist_ok=True)
    arguments.output.write_text(canonical_json(checks, pretty=True), encoding="utf-8")
    print(json.dumps(checks["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
