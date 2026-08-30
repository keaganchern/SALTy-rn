from __future__ import annotations

import json
from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.intrinsic_review_publish import (
    IntrinsicReviewPublishError,
    _successful_pytest_count,
    publish_intrinsic_reviews,
)
from workflow.verification.elementwise_compiler.reviews import IntrinsicReview


ROOT = Path(__file__).resolve().parents[3]


def test_execution_evidence_rejects_a_mixed_pass_fail_summary() -> None:
    assert _successful_pytest_count("153 passed, 17 failed in 15.29s\n") is None
    assert _successful_pytest_count("170 passed in 127.04s\n") == 170


def test_publisher_emits_one_strict_record_per_used_exact_subject(tmp_path: Path) -> None:
    report = tmp_path / "review.md"
    report.write_text(
        "Implementation gate: GO\n\nVerdict: NO-GO\n", encoding="utf-8"
    )
    output = tmp_path / "reviews"

    reviews = publish_intrinsic_reviews(
        ROOT,
        reviewer="agent:test-independent-reviewer",
        reviewer_report=report,
        output_directory=output,
        _validate_execution_evidence=False,
    )

    assert len(reviews) == 180
    files = sorted(output.glob("*.json"))
    assert len(files) == 180
    parsed = [
        IntrinsicReview.from_record(json.loads(path.read_text(encoding="utf-8")))
        for path in files
    ]
    assert len({review.review_id for review in parsed}) == 180
    assert all(review.schema_version == 2 for review in parsed)
    assert all(review.audit_variant_sha256 for review in parsed)


def test_final_publisher_rejects_an_implementation_only_go(tmp_path: Path) -> None:
    report = tmp_path / "review.md"
    report.write_text(
        "Implementation gate: GO\n\nVerdict: NO-GO\n", encoding="utf-8"
    )
    with pytest.raises(
        IntrinsicReviewPublishError,
        match="does not authorize final 180 approvals",
    ):
        publish_intrinsic_reviews(
            ROOT,
            reviewer="agent:test-independent-reviewer",
            reviewer_report=report,
            output_directory=tmp_path / "reviews",
        )
