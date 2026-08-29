from __future__ import annotations

from pathlib import Path

import pytest
import workflow.verification.elementwise_compiler.program_reviews as program_reviews

from workflow.verification.elementwise_compiler.program_reviews import (
    ProgramReview,
    ProgramReviewError,
    build_program_review_checks,
    build_program_review_plan,
    publish_program_reviews,
)


ROOT = Path(__file__).resolve().parents[3]


def test_program_review_plan_and_checks_cover_exact_live_outcomes() -> None:
    plan = build_program_review_plan(ROOT)
    checks = build_program_review_checks(ROOT)

    assert plan["counts"] == {
        "programs": 19,
        "outcomes": {
            "counterexample": 4,
            "external-condition-missing": 7,
            "verified(value)": 8,
        },
    }
    assert len(plan["subjects"]) == 19
    assert len({row["program_id"] for row in plan["subjects"]}) == 19
    assert checks["plan_sha256"] == plan["plan_sha256"]
    assert checks["counts"] == {"passed_programs": 19}
    assert checks["intrinsic_review_closure"] == {
        "used": 180,
        "reviewed": 180,
        "lean_checked": 180,
    }


def test_program_review_round_trip_is_strict() -> None:
    digest = "a" * 64
    review = ProgramReview(
        program_id="sample",
        outcome_status="verified(value)",
        subject_sha256=digest,
        plan_sha256=digest,
        checks_sha256=digest,
        policy_path="notes/policy.md",
        policy_sha256=digest,
        reviewer="agent:independent-reviewer",
        reviewer_report_path="notes/review.md",
        reviewer_report_sha256=digest,
        detail="accepted exact recorded outcome",
    )

    assert ProgramReview.from_record(review.to_record()) == review
    changed = review.to_record()
    changed["outcome_status"] = "counterexample"
    with pytest.raises(ProgramReviewError, match="digest disagrees"):
        ProgramReview.from_record(changed)


def test_program_review_rejects_non_agent_identity() -> None:
    with pytest.raises(ProgramReviewError, match="independent agent"):
        ProgramReview(
            program_id="sample",
            outcome_status="counterexample",
            subject_sha256="a" * 64,
            plan_sha256="a" * 64,
            checks_sha256="a" * 64,
            policy_path="notes/policy.md",
            policy_sha256="a" * 64,
            reviewer="human",
            reviewer_report_path="notes/review.md",
            reviewer_report_sha256="a" * 64,
            detail="accepted exact recorded outcome",
        )


def test_program_review_implementation_has_no_program_allowlist() -> None:
    source = (
        ROOT / "src/workflow/verification/elementwise_compiler/program_reviews.py"
    ).read_text(encoding="utf-8")
    for forbidden in (
        "f32-vadd",
        "f32-vrndne",
        "f32-vmax",
        "f32-vmin",
        "s8-vclamp",
    ):
        assert forbidden not in source


def test_program_review_publisher_recomputes_live_parents(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    current = build_program_review_plan(ROOT)
    changed = {**current, "claim_scope": "mutated-after-review"}
    monkeypatch.setattr(program_reviews, "build_program_review_plan", lambda root: changed)

    with pytest.raises(ProgramReviewError, match="plan is stale"):
        publish_program_reviews(
            ROOT,
            reviewer="agent:test-reviewer",
            reviewer_report="notes/reviews/absent.md",
            output_directory=tmp_path,
        )


def test_program_review_publisher_accepts_cli_path_values(tmp_path: Path) -> None:
    reviews = publish_program_reviews(
        ROOT,
        reviewer="agent:test-reviewer",
        reviewer_report=Path(
            "notes/reviews/elementwise-m7-program-outcome-convergence-2026-08-29.md"
        ),
        output_directory=tmp_path,
    )

    assert len(reviews) == build_program_review_plan(ROOT)["counts"]["programs"]
