from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path

import pytest

from src.workflow.verification.intrinsic_dashboard.authority import (
    ReviewerAuthorityError,
    bind_evidence,
    load_reviewer_registry,
    require_trusted_reviewer,
    verify_bound_evidence,
)


def _write_registry(path: Path, reviewers: list[dict[str, str]]) -> None:
    path.write_text(
        json.dumps({"schema_version": 2, "reviewers": reviewers}),
        encoding="utf-8",
    )


def test_empty_registry_fails_closed_for_every_claimed_reviewer(tmp_path: Path) -> None:
    path = tmp_path / "reviewers.json"
    _write_registry(path, [])

    assert load_reviewer_registry(path) == {}
    with pytest.raises(ReviewerAuthorityError, match="not in the tracked"):
        require_trusted_reviewer(path, "reviewer", author="backend")


def test_registry_requires_sorted_unique_strict_records(tmp_path: Path) -> None:
    path = tmp_path / "reviewers.json"
    _write_registry(
        path,
        [
            {
                "id": "z-reviewer",
                "display_name": "Z Reviewer",
                "may_review_authors": ["backend"],
            },
            {
                "id": "a-reviewer",
                "display_name": "A Reviewer",
                "may_review_authors": ["backend"],
            },
        ],
    )

    with pytest.raises(ReviewerAuthorityError, match="sorted by id"):
        load_reviewer_registry(path)


def test_registered_reviewer_resolves_to_canonical_display_name(tmp_path: Path) -> None:
    path = tmp_path / "reviewers.json"
    _write_registry(
        path,
        [
            {
                "id": "alice",
                "display_name": "Alice Reviewer",
                "may_review_authors": ["backend"],
            }
        ],
    )

    reviewer = require_trusted_reviewer(path, "alice", author="backend")

    assert reviewer.reviewer_id == "alice"
    assert reviewer.display_name == "Alice Reviewer"
    assert reviewer.may_review_authors == ("backend",)


def test_reviewer_must_be_independent_from_author_group(tmp_path: Path) -> None:
    path = tmp_path / "reviewers.json"
    _write_registry(
        path,
        [
            {
                "id": "alice",
                "display_name": "Alice Reviewer",
                "may_review_authors": ["different-backend"],
            }
        ],
    )

    with pytest.raises(ReviewerAuthorityError, match="not authorized"):
        require_trusted_reviewer(path, "alice", author="backend")


def test_evidence_is_repository_relative_existing_and_content_bound(
    tmp_path: Path,
) -> None:
    evidence = tmp_path / "notes" / "review.txt"
    evidence.parent.mkdir()
    evidence.write_bytes(b"checked\n")

    bound = bind_evidence(tmp_path, ["notes/review.txt"])
    assert bound == (f"notes/review.txt@sha256:{sha256(b'checked\n').hexdigest()}",)
    assert verify_bound_evidence(tmp_path, bound) == bound

    evidence.write_bytes(b"changed\n")
    with pytest.raises(ReviewerAuthorityError, match="content changed"):
        verify_bound_evidence(tmp_path, bound)


@pytest.mark.parametrize(
    "reference",
    ("https://example.com/review", "/tmp/review.txt", "../review.txt", "missing"),
)
def test_evidence_rejects_urls_absolute_parent_and_missing_paths(
    tmp_path: Path, reference: str
) -> None:
    with pytest.raises(ReviewerAuthorityError):
        bind_evidence(tmp_path, [reference])
