"""Publish one schema-v2 approval per independently accepted exact subject.

This command is intentionally separate from audit/check generation.  It may run
only after a read-only reviewer has accepted all families named in the plan.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path
from typing import Any, Mapping, Sequence

from .reviews import IntrinsicReview, ReviewCheck, ReviewEvidence
from .schema import Architecture, canonical_json, canonical_sha256


class IntrinsicReviewPublishError(RuntimeError):
    """Candidate evidence is stale, incomplete, or lacks reviewer authorization."""


PYTHON_COMMAND = (
    "PYTHONPATH=.:src pytest -q "
    "tests/verification/elementwise_compiler/test_intrinsic_audit.py "
    "tests/verification/elementwise_compiler/test_intrinsic_review_plan.py "
    "tests/verification/elementwise_compiler/test_intrinsic_review_checks.py "
    "tests/verification/elementwise_compiler/test_intrinsic_review_publish.py "
    "tests/verification/elementwise_compiler/test_intrinsics.py "
    "tests/verification/elementwise_compiler/test_reviews.py "
    "tests/verification/elementwise_compiler/test_wide_generation.py "
    "tests/verification/lean_backend/test_binding.py "
    "tests/verification/lean_backend/test_emit_lean.py "
    "tests/verification/lean_backend/test_case_emit.py "
    "tests/verification/lean_backend/test_registry.py "
    "tests/verification/lean_backend/test_intrinsic_index.py "
    "tests/verification/lean_backend/test_intrinsic_index_inventory.py "
    "tests/verification/intrinsic_dashboard/test_web.py"
)
LEAN_COMMAND = "lake build && lake build SALT.Test.FP32 SALT.Test.IntegerIntrinsics"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_bound(path: Path, digest_field: str) -> Mapping[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, Mapping):
        raise IntrinsicReviewPublishError(f"{path.name} is not a JSON object")
    unsigned = dict(value)
    if unsigned.pop(digest_field, None) != canonical_sha256(unsigned):
        raise IntrinsicReviewPublishError(f"{path.name} digest disagrees")
    return value


def _successful_pytest_count(output: str) -> int | None:
    summary = re.search(
        r"(?m)^(\d+) passed(?P<rest>(?:, [^\n]+)?) in [0-9.]+s$",
        output,
    )
    if summary is None:
        return None
    rest = summary.group("rest")
    if "failed" in rest or "error" in rest:
        return None
    return int(summary.group(1))


def _primary_evidence(row: Mapping[str, Any]) -> tuple[ReviewEvidence, ...]:
    evidence = row["primary_evidence"]
    if row["architecture"] == "neon":
        records = (
            ReviewEvidence(
                evidence["authority"],
                evidence["revision"],
                evidence["source_url"],
                evidence["path"],
                evidence["file_sha256"],
                tuple(sorted({evidence["selector"], evidence["instruction"]})),
            ),
        )
    else:
        records = (
            ReviewEvidence(
                evidence["authority"],
                evidence["revision"],
                evidence["source_url"],
                evidence["path"],
                evidence["file_sha256"],
                (evidence["selector"],),
            ),
            ReviewEvidence(
                evidence["isa_authority"],
                evidence["isa_revision"],
                evidence["isa_source_url"],
                evidence["isa_path"],
                evidence["isa_file_sha256"],
                (evidence["isa_selector"],),
            ),
        )
    return tuple(sorted(records, key=lambda item: item.to_record().__repr__()))


def publish_intrinsic_reviews(
    repository_root: str | Path,
    *,
    reviewer: str,
    reviewer_report: str | Path,
    output_directory: str | Path = "verification/elementwise-compiler/intrinsic-reviews",
    _validate_execution_evidence: bool = True,
) -> tuple[IntrinsicReview, ...]:
    if not reviewer.startswith("agent:"):
        raise IntrinsicReviewPublishError("reviewer must be an independent agent identity")
    root = Path(repository_root).resolve()
    corpus = root / "verification/elementwise-compiler"
    audit = _load_bound(corpus / "IntrinsicAudit.json", "audit_sha256")
    plan = _load_bound(corpus / "IntrinsicReviewPlan.json", "plan_sha256")
    checks = _load_bound(corpus / "IntrinsicReviewChecks.json", "checks_sha256")
    if (
        plan["audit_sha256"] != audit["audit_sha256"]
        or checks["audit_sha256"] != audit["audit_sha256"]
        or checks["plan_sha256"] != plan["plan_sha256"]
    ):
        raise IntrinsicReviewPublishError("review evidence parent is stale")
    reviewer_path = (root / reviewer_report).resolve()
    reviewer_text = reviewer_path.read_text(encoding="utf-8")
    if _validate_execution_evidence:
        if "Verdict: GO (180/180)" not in reviewer_text:
            raise IntrinsicReviewPublishError(
                "reviewer report does not authorize final 180 approvals"
            )
    elif not any(
        marker in reviewer_text
        for marker in ("Implementation gate: GO", "Verdict: GO (180/180)")
    ):
        raise IntrinsicReviewPublishError(
            "reviewer report does not authorize bootstrap publication"
        )

    python_output = root / "notes/reviews/evidence/elementwise-m6-python-tests.txt"
    lean_output = root / "notes/reviews/evidence/elementwise-m6-lean-build.txt"
    lean_text = lean_output.read_text(encoding="utf-8")
    if _validate_execution_evidence:
        passed = _successful_pytest_count(python_output.read_text(encoding="utf-8"))
        if passed is None or passed < 150:
            raise IntrinsicReviewPublishError("focused Python evidence did not pass")
        if "Build completed successfully (46 jobs)." not in lean_text or (
            "Build completed successfully (7 jobs)." not in lean_text
        ):
            raise IntrinsicReviewPublishError("Lean evidence did not pass both targets")
    shared_checks = tuple(
        sorted(
            (
                ReviewCheck(
                    "family-audit",
                    "PYTHONPATH=.:src python -m workflow.verification.elementwise_compiler.intrinsic_review_checks",
                    "verification/elementwise-compiler/IntrinsicReviewChecks.json",
                    _sha256(corpus / "IntrinsicReviewChecks.json"),
                ),
                ReviewCheck(
                    "lean-elaboration",
                    LEAN_COMMAND,
                    "notes/reviews/evidence/elementwise-m6-lean-build.txt",
                    _sha256(lean_output),
                ),
                ReviewCheck(
                    "python-regression",
                    PYTHON_COMMAND,
                    "notes/reviews/evidence/elementwise-m6-python-tests.txt",
                    _sha256(python_output),
                ),
            ),
            key=lambda item: item.name,
        )
    )
    policy_path = root / plan["policy_path"]
    if _sha256(policy_path) != plan["policy_sha256"]:
        raise IntrinsicReviewPublishError("review policy is stale")
    audit_by_id = {row["capability_id"]: row for row in audit["variants"]}
    checked_ids = {row["capability_id"] for row in checks["subjects"]}
    reviews: list[IntrinsicReview] = []
    for family in plan["families"]:
        for subject in family["subjects"]:
            row = audit_by_id[subject["capability_id"]]
            if subject["capability_id"] not in checked_ids:
                raise IntrinsicReviewPublishError("subject lacks machine checks")
            reviews.append(
                IntrinsicReview(
                    architecture=Architecture(row["architecture"]),
                    spelling=row["spelling"],
                    function_type=row["function_type"],
                    argument_count=row["argument_count"],
                    descriptor_sha256=row["descriptor_sha256"],
                    implementation_sha256=row["implementation_sha256"],
                    policy_path=plan["policy_path"],
                    policy_sha256=plan["policy_sha256"],
                    reviewer=reviewer,
                    evidence=_primary_evidence(row),
                    checks=shared_checks,
                    detail=(
                        f"{family['family']}: independently accepted exact Lean value-model "
                        f"subject; reviewer report {_sha256(reviewer_path)}."
                    ),
                    audit_variant_sha256=row["audit_variant_sha256"],
                    claim_scope=row["claim_scope"],
                    architecture_conditions=tuple(row["architecture_conditions"]),
                )
            )
    if len(reviews) != 180 or len({review.review_id for review in reviews}) != 180:
        raise IntrinsicReviewPublishError("publisher did not create 180 exact reviews")
    destination = (root / output_directory).resolve()
    destination.mkdir(parents=True, exist_ok=True)
    for review in reviews:
        slug = re.sub(r"[^a-z0-9]+", "-", review.review_id.lower()).strip("-")
        (destination / f"{slug}.json").write_text(
            canonical_json(review.to_record(), pretty=True), encoding="utf-8"
        )
    return tuple(reviews)


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    parser.add_argument("--reviewer", required=True)
    parser.add_argument("--reviewer-report", type=Path, required=True)
    parser.add_argument("--output-directory", type=Path, required=True)
    arguments = parser.parse_args(argv)
    reviews = publish_intrinsic_reviews(
        arguments.repository_root,
        reviewer=arguments.reviewer,
        reviewer_report=arguments.reviewer_report,
        output_directory=arguments.output_directory,
    )
    print(json.dumps({"published_reviews": len(reviews)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
