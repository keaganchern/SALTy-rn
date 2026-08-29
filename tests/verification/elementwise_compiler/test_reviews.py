from __future__ import annotations

import copy
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.reviews import (
    IntrinsicReview,
    ReviewCheck,
    ReviewEvidence,
    load_intrinsic_reviews,
)
from workflow.verification.elementwise_compiler.schema import (
    Architecture,
    ElementwiseSchemaError,
    canonical_json,
)


D = "0" * 64
E = "1" * 64
F = "2" * 64


def _review(policy_sha256: str = E) -> IntrinsicReview:
    return IntrinsicReview(
        architecture=Architecture.NEON,
        spelling="vget_low_f32",
        function_type="float32x2_t (float32x4_t)",
        argument_count=1,
        descriptor_sha256=D,
        implementation_sha256=F,
        policy_path="notes/policies/elementwise-intrinsic-review-v1.md",
        policy_sha256=policy_sha256,
        reviewer="agent:independent-reviewer",
        evidence=(
            ReviewEvidence(
                "Arm ACLE",
                "c218a6b499897e70d88ceab7c6148d692541929f",
                "https://github.com/ARM-software/acle/blob/c218a6b/tools/intrinsic_db/advsimd.csv",
                "tools/intrinsic_db/advsimd.csv",
                E,
                ("vget_low_f32",),
            ),
        ),
        checks=(
            ReviewCheck(
                "descriptor-tests",
                "pytest -q tests",
                "notes/reviews/evidence/descriptor-tests.txt",
                D,
            ),
        ),
        detail="Exact split-vector signature and low-half lane order approved.",
    )


def test_intrinsic_review_round_trip_is_strict_and_content_addressed() -> None:
    review = _review()
    record = review.to_record()

    assert IntrinsicReview.from_record(record) == review
    assert review.review_id.startswith("intrinsic-review:neon:vget_low_f32:")

    changed = copy.deepcopy(record)
    changed["descriptor_sha256"] = E
    with pytest.raises(ElementwiseSchemaError, match="id disagrees with source key"):
        IntrinsicReview.from_record(changed)

    other_descriptor = replace(review, descriptor_sha256=E)
    assert other_descriptor.review_id != review.review_id


def test_review_loader_rechecks_policy_hash_and_rejects_duplicates(tmp_path: Path) -> None:
    policy = tmp_path / "notes/policies/elementwise-intrinsic-review-v1.md"
    policy.parent.mkdir(parents=True)
    policy.write_text("policy\n", encoding="utf-8")
    policy_sha256 = hashlib.sha256(policy.read_bytes()).hexdigest()
    review = _review(policy_sha256)
    review_root = tmp_path / "verification/elementwise-compiler/intrinsic-reviews"
    review_root.mkdir(parents=True)
    check_output = tmp_path / "notes/reviews/evidence/descriptor-tests.txt"
    check_output.parent.mkdir(parents=True)
    check_output.write_bytes(b"")
    review = IntrinsicReview(
        review.architecture,
        review.spelling,
        review.function_type,
        review.argument_count,
        review.descriptor_sha256,
        review.implementation_sha256,
        review.policy_path,
        review.policy_sha256,
        review.reviewer,
        review.evidence,
        (
            ReviewCheck(
                "descriptor-tests",
                "pytest -q tests",
                "notes/reviews/evidence/descriptor-tests.txt",
                hashlib.sha256(b"").hexdigest(),
            ),
        ),
        review.detail,
    )
    (review_root / "first.json").write_text(
        canonical_json(review.to_record(), pretty=True), encoding="utf-8"
    )

    loaded = load_intrinsic_reviews(tmp_path)
    assert loaded[review.key] == review

    (review_root / "duplicate.json").write_text(
        canonical_json(review.to_record(), pretty=True), encoding="utf-8"
    )
    with pytest.raises(ElementwiseSchemaError, match="duplicate"):
        load_intrinsic_reviews(tmp_path)

    (review_root / "duplicate.json").unlink()
    policy.write_text("changed\n", encoding="utf-8")
    with pytest.raises(ElementwiseSchemaError, match="stale policy"):
        load_intrinsic_reviews(tmp_path)


def test_review_record_rejects_non_passed_check() -> None:
    record = _review().to_record()
    assert isinstance(record["checks"], list)
    record["checks"][0]["status"] = "failed"
    record["review_sha256"] = "0" * 64

    with pytest.raises(ElementwiseSchemaError, match="only passed"):
        IntrinsicReview.from_record(record)
