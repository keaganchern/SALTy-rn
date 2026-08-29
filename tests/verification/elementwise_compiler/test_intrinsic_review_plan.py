from __future__ import annotations

from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.intrinsic_review_plan import (
    IntrinsicReviewPlanError,
    _family,
    build_intrinsic_review_plan,
)
from workflow.verification.elementwise_compiler.schema import canonical_sha256


ROOT = Path(__file__).resolve().parents[3]


def test_review_plan_partitions_all_used_exact_variants_once() -> None:
    plan = build_intrinsic_review_plan(ROOT)
    unsigned = dict(plan)
    assert unsigned.pop("plan_sha256") == canonical_sha256(unsigned)
    assert plan["counts"] == {"families": 12, "used_variants": 180}
    assert {item["family"]: item["count"] for item in plan["families"]} == {
        "S0-schedule-setvl": 3,
        "S1-structural-plain": 57,
        "S2-structural-immediate": 8,
        "I0-integer-plain": 62,
        "I1-integer-broadcast-normalized": 3,
        "I2-integer-saturating-narrow-shift": 11,
        "I3-integer-mode-sensitive-rounding": 8,
        "FP0-float-arithmetic-abs": 11,
        "FP1-float-predicate-select-sign": 6,
        "FP2-float-maxmin-nan": 4,
        "FP3-float-div-sqrt": 4,
        "FP4-float-conversion": 3,
    }
    identities = [
        subject["capability_id"]
        for family in plan["families"]
        for subject in family["subjects"]
    ]
    assert len(identities) == len(set(identities)) == 180


def test_unknown_float_operation_fails_closed() -> None:
    with pytest.raises(IntrinsicReviewPlanError, match="unclassified floating"):
        _family(
            {
                "role": "semantic",
                "spelling": "__riscv_vfmystery_vv_f32m8",
                "immediate_constraints": [],
            }
        )
