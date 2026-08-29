"""Content-addressed independent reviews of generated program outcomes."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Sequence

from .schema import (
    ExternalConditionStatus,
    ResultStatus,
    canonical_json,
    canonical_sha256,
)


class ProgramReviewError(RuntimeError):
    """A program review parent, subject, or authorization is malformed."""


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_bound(path: Path, digest_field: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ProgramReviewError(f"cannot read {path.name}") from error
    if not isinstance(value, Mapping):
        raise ProgramReviewError(f"{path.name} is not a JSON object")
    unsigned = dict(value)
    if unsigned.pop(digest_field, None) != canonical_sha256(unsigned):
        raise ProgramReviewError(f"{path.name} digest disagrees")
    return value


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ProgramReviewError(f"{field} must be trimmed non-empty text")
    return value


def _digest(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ProgramReviewError(f"{field} must be a SHA-256 digest")
    return value


def _optional_digest(value: object, field: str) -> str | None:
    return None if value is None else _digest(value, field)


def _relative(value: object, field: str) -> str:
    if isinstance(value, Path):
        value = value.as_posix()
    text = _text(value, field)
    path = Path(text)
    if path.is_absolute() or ".." in path.parts:
        raise ProgramReviewError(f"{field} must stay repository-relative")
    return path.as_posix()


def _exact(data: Mapping[str, Any], expected: set[str], subject: str) -> None:
    if set(data) != expected:
        raise ProgramReviewError(
            f"invalid {subject} fields: missing={sorted(expected - set(data))!r}, "
            f"extra={sorted(set(data) - expected)!r}"
        )


def _subject(
    root: Path,
    corpus_root: Path,
    report_sha256: str,
    record: Mapping[str, Any],
) -> dict[str, Any]:
    # Lazy import avoids making the dashboard depend on its own plan builder at
    # module-import time.  Both paths still use the same strict stack verifier.
    from workflow.verification.intrinsic_dashboard.elementwise_graph import (
        _verify_stack,
    )

    program_id = _text(record.get("program_id"), "program id")
    relative_index = record.get("artifact_index")
    if relative_index is None:
        raise ProgramReviewError(f"{program_id} has no generated artifact stack")
    index_relative = _relative(relative_index, "artifact index path")
    stack = _verify_stack(corpus_root, index_relative)
    index_path = corpus_root / index_relative
    manifest = stack["manifest"]
    models = stack["models"]
    spec = stack["spec"]
    external = stack["external"]
    phase = stack["phase"]
    counterexample = stack["counterexample"]
    task = stack["task"]
    result = stack["result"]
    if record.get("manifest_sha256") != manifest.sha256:
        raise ProgramReviewError(f"{program_id} report/manifest binding differs")

    proof_path = index_path.parent / "Proof.lean"
    if result is None and proof_path.is_file():
        raise ProgramReviewError(f"{program_id} has an unbound Proof.lean")
    if result is not None:
        outcome = result.status.value
        checker = result.checker_sha256
        toolchain = result.toolchain_sha256
        result_sha = result.sha256
        proof_sha = result.proof_sha256
    elif external.status is ExternalConditionStatus.REQUIRED_MISSING:
        outcome = ResultStatus.EXTERNAL_CONDITION_MISSING.value
        checker = None
        toolchain = None
        result_sha = None
        proof_sha = None
    elif task is not None:
        outcome = "proof-ready"
        checker = task.checker_policy_sha256
        toolchain = task.toolchain_sha256
        result_sha = None
        proof_sha = None
    else:
        outcome = "spec-generated"
        checker = None
        toolchain = None
        result_sha = None
        proof_sha = None

    sources = []
    for source in manifest.sources:
        source_path = root / source.path
        if not source_path.is_file() or _sha256(source_path) != source.source_sha256:
            raise ProgramReviewError(f"{program_id} source digest differs: {source.path}")
        sources.append(source.to_record())
    subject: dict[str, Any] = {
        "program_id": program_id,
        "report_sha256": report_sha256,
        "artifact_index_path": index_relative,
        "artifact_index_sha256": _sha256(index_path),
        "manifest_sha256": manifest.sha256,
        "sources": sources,
        "models_sha256": models.sha256,
        "spec_sha256": spec.sha256,
        "external_condition_sha256": external.sha256,
        "external_condition_status": external.status.value,
        "cross_phase_audit_sha256": phase.sha256,
        "cross_phase_status": phase.status.value,
        "counterexample_sha256": (
            None if counterexample is None else counterexample.sha256
        ),
        "counterexample_claim": None if counterexample is None else counterexample.claim,
        "proof_task_sha256": None if task is None else task.sha256,
        "proof_sha256": proof_sha,
        "result_sha256": result_sha,
        "result_status": None if result is None else result.status.value,
        "checker_sha256": checker,
        "toolchain_sha256": toolchain,
        "outcome_status": outcome,
        "claim_scope": "lean-value-model-only",
    }
    subject["subject_sha256"] = canonical_sha256(subject)
    return subject


def build_program_review_plan(
    repository_root: str | Path,
    *,
    corpus_path: str | Path = "verification/elementwise-compiler",
    policy_path: str | Path = "notes/policies/elementwise-program-review-v1.md",
) -> dict[str, Any]:
    """Build the exact nineteen-subject review plan from the live artifact graph."""

    from workflow.verification.intrinsic_dashboard.elementwise_graph import (
        _verify_report,
    )

    root = Path(repository_root).resolve()
    corpus_root = (root / corpus_path).resolve()
    policy = (root / policy_path).resolve()
    if not policy.is_file():
        raise ProgramReviewError("program review policy is absent")
    report = _verify_report(corpus_root)
    subjects = [
        _subject(root, corpus_root, str(report["report_sha256"]), record)
        for record in report["programs"]
        if isinstance(record, Mapping) and record.get("artifact_index") is not None
    ]
    subjects.sort(key=lambda item: item["program_id"])
    expected = report.get("scalar_layout_scope")
    if len(subjects) != expected or len({row["program_id"] for row in subjects}) != len(subjects):
        raise ProgramReviewError("review plan does not cover scalar-layout programs exactly")
    plan: dict[str, Any] = {
        "artifact_kind": "elementwise-program-review-plan",
        "schema_version": 1,
        "corpus_report_path": f"{Path(corpus_path).as_posix()}/CorpusReport.json",
        "corpus_report_sha256": report["report_sha256"],
        "policy_path": Path(policy_path).as_posix(),
        "policy_sha256": _sha256(policy),
        "claim_scope": "lean-value-model-only",
        "counts": {
            "programs": len(subjects),
            "outcomes": {
                status: sum(row["outcome_status"] == status for row in subjects)
                for status in sorted({str(row["outcome_status"]) for row in subjects})
            },
        },
        "subjects": subjects,
    }
    plan["plan_sha256"] = canonical_sha256(plan)
    return plan


def build_program_review_checks(repository_root: str | Path) -> dict[str, Any]:
    """Recompute the plan and enforce outcome-specific integrity invariants."""

    root = Path(repository_root).resolve()
    corpus = root / "verification/elementwise-compiler"
    stored = _load_bound(corpus / "ProgramReviewPlan.json", "plan_sha256")
    current = build_program_review_plan(root)
    if stored != current:
        raise ProgramReviewError("program review plan is stale")

    # Program approval depends on the reusable intrinsic puzzle closure being
    # complete.  Import locally to keep this module usable by the graph loader.
    from workflow.verification.intrinsic_dashboard.elementwise_graph import (
        build_elementwise_graph,
    )

    graph = build_elementwise_graph(corpus, include_program_reviews=False)
    summary = graph["summary"]
    if (
        summary["reviewed_used_intrinsic_variants"]
        != summary["used_intrinsic_variants"]
        or summary["lean_checked_used_intrinsic_variants"]
        != summary["used_intrinsic_variants"]
    ):
        raise ProgramReviewError("used exact intrinsic review closure is incomplete")

    rows = []
    for subject in current["subjects"]:
        outcome = subject["outcome_status"]
        task = subject["proof_task_sha256"]
        proof = subject["proof_sha256"]
        result = subject["result_sha256"]
        witness = subject["counterexample_sha256"]
        if outcome == ResultStatus.VERIFIED_VALUE.value:
            valid = all(
                subject[field] is not None
                for field in (
                    "proof_task_sha256",
                    "proof_sha256",
                    "result_sha256",
                    "checker_sha256",
                    "toolchain_sha256",
                )
            ) and witness is None
        elif outcome == ResultStatus.COUNTEREXAMPLE.value:
            from .counterexamples import _checker_sha256 as phase_checker_sha256
            from .program_counterexamples import (
                _checker_sha256 as program_checker_sha256,
            )

            claim = subject["counterexample_claim"]
            if isinstance(claim, str) and claim.endswith(
                ".neonPhaseFunctionsEqualClaim"
            ):
                expected_checker = phase_checker_sha256()
            elif isinstance(claim, str) and claim.endswith(
                ".completeValueEquivalenceClaim"
            ):
                expected_checker = program_checker_sha256()
            else:
                expected_checker = None
            valid = (
                task is None
                and proof is None
                and result is not None
                and witness is not None
                and subject["checker_sha256"] is not None
                and subject["checker_sha256"] == expected_checker
                and subject["toolchain_sha256"] is not None
            )
        elif outcome == ResultStatus.EXTERNAL_CONDITION_MISSING.value:
            valid = (
                subject["external_condition_status"]
                == ExternalConditionStatus.REQUIRED_MISSING.value
                and task is None
                and proof is None
                and result is None
                and witness is None
            )
        else:
            valid = outcome in {
                ResultStatus.PROOF_SEARCH_FAILED.value,
                ResultStatus.LEAN_FAILED.value,
            } and task is not None and result is not None and witness is None
        if not valid:
            raise ProgramReviewError(
                f"{subject['program_id']} outcome bindings are inconsistent"
            )
        rows.append(
            {
                "program_id": subject["program_id"],
                "subject_sha256": subject["subject_sha256"],
                "outcome_status": outcome,
                "status": "passed",
            }
        )
    checks: dict[str, Any] = {
        "artifact_kind": "elementwise-program-review-checks",
        "schema_version": 1,
        "plan_sha256": current["plan_sha256"],
        "checker_sha256": canonical_sha256(
            {
                path.name: _sha256(path)
                for path in (
                    Path(__file__).resolve(),
                    Path(__file__).resolve().with_name("proof.py"),
                    Path(__file__).resolve().with_name("schema.py"),
                    Path(__file__).resolve().with_name("counterexamples.py"),
                    Path(__file__).resolve().with_name("program_counterexamples.py"),
                    root
                    / "src/workflow/verification/intrinsic_dashboard/elementwise_graph.py",
                )
            }
        ),
        "claim_scope": "lean-value-model-only",
        "intrinsic_review_closure": {
            "used": summary["used_intrinsic_variants"],
            "reviewed": summary["reviewed_used_intrinsic_variants"],
            "lean_checked": summary["lean_checked_used_intrinsic_variants"],
        },
        "counts": {"passed_programs": len(rows)},
        "subjects": rows,
    }
    checks["checks_sha256"] = canonical_sha256(checks)
    return checks


@dataclass(frozen=True, slots=True)
class ProgramReview:
    program_id: str
    outcome_status: str
    subject_sha256: str
    plan_sha256: str
    checks_sha256: str
    policy_path: str
    policy_sha256: str
    reviewer: str
    reviewer_report_path: str
    reviewer_report_sha256: str
    detail: str
    schema_version: int = 1

    def __post_init__(self) -> None:
        if self.schema_version != 1:
            raise ProgramReviewError("unsupported program review schema")
        for value, field in (
            (self.program_id, "program id"),
            (self.outcome_status, "outcome status"),
            (self.reviewer, "reviewer"),
            (self.detail, "review detail"),
        ):
            _text(value, field)
        for value, field in (
            (self.subject_sha256, "subject digest"),
            (self.plan_sha256, "plan digest"),
            (self.checks_sha256, "checks digest"),
            (self.policy_sha256, "policy digest"),
            (self.reviewer_report_sha256, "reviewer report digest"),
        ):
            _digest(value, field)
        _relative(self.policy_path, "policy path")
        _relative(self.reviewer_report_path, "reviewer report path")
        if not self.reviewer.startswith("agent:"):
            raise ProgramReviewError("reviewer must be an independent agent identity")

    @property
    def review_id(self) -> str:
        return f"program-review:{self.program_id}"

    def unsigned_record(self) -> dict[str, Any]:
        return {
            "artifact_kind": "elementwise-program-review",
            "schema_version": self.schema_version,
            "review_id": self.review_id,
            "verdict": "approved-outcome",
            "program_id": self.program_id,
            "outcome_status": self.outcome_status,
            "subject_sha256": self.subject_sha256,
            "plan_sha256": self.plan_sha256,
            "checks_sha256": self.checks_sha256,
            "policy_path": self.policy_path,
            "policy_sha256": self.policy_sha256,
            "reviewer": self.reviewer,
            "reviewer_report_path": self.reviewer_report_path,
            "reviewer_report_sha256": self.reviewer_report_sha256,
            "detail": self.detail,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.unsigned_record())

    def to_record(self) -> dict[str, Any]:
        return {**self.unsigned_record(), "review_sha256": self.sha256}

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "ProgramReview":
        expected = {
            "artifact_kind", "schema_version", "review_id", "verdict",
            "program_id", "outcome_status", "subject_sha256", "plan_sha256",
            "checks_sha256", "policy_path", "policy_sha256", "reviewer",
            "reviewer_report_path", "reviewer_report_sha256", "detail",
            "review_sha256",
        }
        _exact(data, expected, "program review")
        if data["artifact_kind"] != "elementwise-program-review":
            raise ProgramReviewError("invalid program review artifact kind")
        if data["verdict"] != "approved-outcome":
            raise ProgramReviewError("program review does not approve the outcome")
        result = cls(
            schema_version=data["schema_version"],
            program_id=_text(data["program_id"], "program id"),
            outcome_status=_text(data["outcome_status"], "outcome status"),
            subject_sha256=_digest(data["subject_sha256"], "subject digest"),
            plan_sha256=_digest(data["plan_sha256"], "plan digest"),
            checks_sha256=_digest(data["checks_sha256"], "checks digest"),
            policy_path=_relative(data["policy_path"], "policy path"),
            policy_sha256=_digest(data["policy_sha256"], "policy digest"),
            reviewer=_text(data["reviewer"], "reviewer"),
            reviewer_report_path=_relative(
                data["reviewer_report_path"], "reviewer report path"
            ),
            reviewer_report_sha256=_digest(
                data["reviewer_report_sha256"], "reviewer report digest"
            ),
            detail=_text(data["detail"], "review detail"),
        )
        if data["review_id"] != result.review_id:
            raise ProgramReviewError("program review id disagrees")
        if _digest(data["review_sha256"], "review digest") != result.sha256:
            raise ProgramReviewError("program review digest disagrees")
        return result


def publish_program_reviews(
    repository_root: str | Path,
    *,
    reviewer: str,
    reviewer_report: str | Path,
    output_directory: str | Path = "verification/elementwise-compiler/program-reviews",
) -> tuple[ProgramReview, ...]:
    """Publish nineteen approvals after a reviewer accepts every exact outcome."""

    root = Path(repository_root).resolve()
    corpus = root / "verification/elementwise-compiler"
    plan = _load_bound(corpus / "ProgramReviewPlan.json", "plan_sha256")
    checks = _load_bound(corpus / "ProgramReviewChecks.json", "checks_sha256")
    current_plan = build_program_review_plan(root)
    if plan != current_plan:
        raise ProgramReviewError("program review plan is stale")
    current_checks = build_program_review_checks(root)
    if checks != current_checks:
        raise ProgramReviewError("program review checks are stale")
    if checks.get("plan_sha256") != plan.get("plan_sha256"):
        raise ProgramReviewError("program review checks have a stale plan parent")
    report_relative = _relative(reviewer_report, "reviewer report path")
    report_path = root / report_relative
    report_text = report_path.read_text(encoding="utf-8")
    if "Verdict: GO (19/19)" not in report_text:
        raise ProgramReviewError("reviewer report does not authorize 19 approvals")
    subject_ids = tuple(row["program_id"] for row in plan["subjects"])
    if any(program_id not in report_text for program_id in subject_ids):
        raise ProgramReviewError("reviewer report does not name every program")
    check_by_id = {row["program_id"]: row for row in checks["subjects"]}
    if set(check_by_id) != set(subject_ids):
        raise ProgramReviewError("review checks do not cover planned programs")
    output = (root / output_directory).resolve()
    output.mkdir(parents=True, exist_ok=True)
    reviews = []
    for subject in plan["subjects"]:
        program_id = subject["program_id"]
        check = check_by_id[program_id]
        if (
            check.get("status") != "passed"
            or check.get("subject_sha256") != subject["subject_sha256"]
            or check.get("outcome_status") != subject["outcome_status"]
        ):
            raise ProgramReviewError(f"{program_id} review check is stale")
        review = ProgramReview(
            program_id=program_id,
            outcome_status=subject["outcome_status"],
            subject_sha256=subject["subject_sha256"],
            plan_sha256=plan["plan_sha256"],
            checks_sha256=checks["checks_sha256"],
            policy_path=plan["policy_path"],
            policy_sha256=plan["policy_sha256"],
            reviewer=reviewer,
            reviewer_report_path=report_relative,
            reviewer_report_sha256=_sha256(report_path),
            detail=(
                f"Independent reviewer accepted the integrity and honest "
                f"{subject['outcome_status']} outcome; this approval does not widen "
                "the Lean value-model claim scope."
            ),
        )
        (output / f"{program_id}.json").write_text(
            canonical_json(review.to_record(), pretty=True), encoding="utf-8"
        )
        reviews.append(review)
    expected_files = {f"{program_id}.json" for program_id in subject_ids}
    for path in output.glob("*.json"):
        if path.name not in expected_files:
            path.unlink()
    return tuple(reviews)


def load_program_reviews(corpus_root: str | Path) -> dict[str, ProgramReview]:
    """Load and validate live review records against recomputed exact subjects."""

    corpus = Path(corpus_root).resolve()
    review_directory = corpus / "program-reviews"
    if not review_directory.is_dir() or not any(review_directory.glob("*.json")):
        return {}
    root = corpus.parents[1]
    plan = _load_bound(corpus / "ProgramReviewPlan.json", "plan_sha256")
    checks = _load_bound(corpus / "ProgramReviewChecks.json", "checks_sha256")
    current = build_program_review_plan(root)
    current_checks = build_program_review_checks(root)
    if (
        plan != current
        or checks != current_checks
        or checks.get("plan_sha256") != plan.get("plan_sha256")
    ):
        raise ProgramReviewError("published program review parents are stale")
    checks_by_id = {row["program_id"]: row for row in checks["subjects"]}
    subjects = {row["program_id"]: row for row in plan["subjects"]}
    reviews: dict[str, ProgramReview] = {}
    for path in sorted(review_directory.glob("*.json")):
        value = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(value, Mapping):
            raise ProgramReviewError("program review root is not an object")
        review = ProgramReview.from_record(value)
        subject = subjects.get(review.program_id)
        check = checks_by_id.get(review.program_id)
        report = root / review.reviewer_report_path
        policy = root / review.policy_path
        if (
            subject is None
            or check is None
            or review.program_id in reviews
            or review.subject_sha256 != subject["subject_sha256"]
            or review.outcome_status != subject["outcome_status"]
            or review.plan_sha256 != plan["plan_sha256"]
            or review.checks_sha256 != checks["checks_sha256"]
            or check.get("status") != "passed"
            or check.get("subject_sha256") != review.subject_sha256
            or not report.is_file()
            or _sha256(report) != review.reviewer_report_sha256
            or not policy.is_file()
            or _sha256(policy) != review.policy_sha256
        ):
            raise ProgramReviewError(f"stale program review: {review.program_id}")
        reviews[review.program_id] = review
    if set(reviews) != set(subjects):
        raise ProgramReviewError("published program reviews do not cover all subjects")
    return reviews


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repository-root", type=Path, required=True)
    subparsers = parser.add_subparsers(dest="operation", required=True)
    plan_parser = subparsers.add_parser("plan")
    plan_parser.add_argument(
        "--output",
        type=Path,
        default=Path("verification/elementwise-compiler/ProgramReviewPlan.json"),
    )
    checks_parser = subparsers.add_parser("checks")
    checks_parser.add_argument(
        "--output",
        type=Path,
        default=Path("verification/elementwise-compiler/ProgramReviewChecks.json"),
    )
    publish_parser = subparsers.add_parser("publish")
    publish_parser.add_argument("--reviewer", required=True)
    publish_parser.add_argument("--reviewer-report", type=Path, required=True)
    arguments = parser.parse_args(argv)
    root = arguments.repository_root.resolve()
    if arguments.operation == "plan":
        value = build_program_review_plan(root)
        output = root / arguments.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(canonical_json(value, pretty=True), encoding="utf-8")
        print(json.dumps(value["counts"], sort_keys=True))
        return 0
    if arguments.operation == "checks":
        value = build_program_review_checks(root)
        output = root / arguments.output
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(canonical_json(value, pretty=True), encoding="utf-8")
        print(json.dumps(value["counts"], sort_keys=True))
        return 0
    reviews = publish_program_reviews(
        root,
        reviewer=arguments.reviewer,
        reviewer_report=arguments.reviewer_report,
    )
    print(json.dumps({"published": len(reviews)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
