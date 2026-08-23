"""Trusted-reviewer and evidence bindings for dashboard approval commands.

This module is a local policy boundary, not an authentication or signature
system.  A reviewer must be explicitly listed in the tracked authority file,
and every evidence path is converted to a repository-relative, content-bound
reference before it can enter the audit ledger.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Mapping, Sequence

from .audit import file_sha256


DEFAULT_REVIEWER_REGISTRY_RELATIVE_PATH = Path(
    "verification/intrinsic-dashboard/reviewers.json"
)

_REVIEWER_ID_RE = re.compile(r"^[a-z0-9](?:[a-z0-9._-]{0,62}[a-z0-9])?$")
_AUTHOR_ID_RE = _REVIEWER_ID_RE
_BOUND_EVIDENCE_RE = re.compile(r"^(?P<path>.+)@sha256:(?P<sha256>[0-9a-f]{64})$")


class ReviewerAuthorityError(ValueError):
    """Reviewer authority or review evidence is malformed."""


@dataclass(frozen=True, slots=True)
class TrustedReviewer:
    reviewer_id: str
    display_name: str
    may_review_authors: tuple[str, ...]

    def can_review(self, author: str) -> bool:
        return author in self.may_review_authors and author != self.reviewer_id


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ReviewerAuthorityError(f"{field} must be a non-empty trimmed string")
    return value


def load_reviewer_registry(path: Path) -> Mapping[str, TrustedReviewer]:
    """Load the exact tracked allowlist, failing closed on every discrepancy."""

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ReviewerAuthorityError(
            f"cannot read trusted-reviewer registry {path}: {error}"
        ) from error
    if not isinstance(raw, dict) or set(raw) != {"schema_version", "reviewers"}:
        raise ReviewerAuthorityError(
            "trusted-reviewer registry must contain exactly schema_version and reviewers"
        )
    if raw["schema_version"] != 2:
        raise ReviewerAuthorityError("unsupported trusted-reviewer schema version")
    rows = raw["reviewers"]
    if not isinstance(rows, list):
        raise ReviewerAuthorityError("reviewers must be a list")

    reviewers: dict[str, TrustedReviewer] = {}
    for index, row in enumerate(rows):
        if not isinstance(row, dict) or set(row) != {
            "id",
            "display_name",
            "may_review_authors",
        }:
            raise ReviewerAuthorityError(
                f"reviewers[{index}] must contain exactly id, display_name, "
                "and may_review_authors"
            )
        reviewer_id = _require_text(row["id"], f"reviewers[{index}].id")
        display_name = _require_text(
            row["display_name"], f"reviewers[{index}].display_name"
        )
        if _REVIEWER_ID_RE.fullmatch(reviewer_id) is None:
            raise ReviewerAuthorityError(
                f"invalid trusted reviewer id: {reviewer_id!r}"
            )
        if reviewer_id in reviewers:
            raise ReviewerAuthorityError(
                f"duplicate trusted reviewer id: {reviewer_id}"
            )
        raw_authors = row["may_review_authors"]
        if not isinstance(raw_authors, list) or not raw_authors:
            raise ReviewerAuthorityError(
                f"reviewers[{index}].may_review_authors must be a non-empty list"
            )
        authors = tuple(
            _require_text(author, f"reviewers[{index}].may_review_authors")
            for author in raw_authors
        )
        if tuple(sorted(set(authors))) != authors:
            raise ReviewerAuthorityError(
                f"reviewers[{index}].may_review_authors must be sorted and unique"
            )
        if any(_AUTHOR_ID_RE.fullmatch(author) is None for author in authors):
            raise ReviewerAuthorityError(
                f"reviewers[{index}].may_review_authors contains an invalid author id"
            )
        reviewers[reviewer_id] = TrustedReviewer(reviewer_id, display_name, authors)

    if list(reviewers) != sorted(reviewers):
        raise ReviewerAuthorityError("trusted reviewers must be sorted by id")
    return reviewers


def require_trusted_reviewer(
    path: Path, reviewer_id: str, *, author: str
) -> TrustedReviewer:
    reviewer = load_reviewer_registry(path).get(reviewer_id)
    if reviewer is None:
        raise ReviewerAuthorityError(
            f"reviewer {reviewer_id!r} is not in the tracked trusted-reviewer registry"
        )
    if reviewer.reviewer_id == author:
        raise ReviewerAuthorityError("a reviewer cannot approve their own author group")
    if not reviewer.can_review(author):
        raise ReviewerAuthorityError(
            f"reviewer {reviewer_id!r} is not authorized to review author {author!r}"
        )
    return reviewer


def _evidence_path(repository_root: Path, reference: str) -> tuple[str, Path, str]:
    match = _BOUND_EVIDENCE_RE.fullmatch(reference)
    if match is None:
        raise ReviewerAuthorityError(
            "bound evidence must have form path@sha256:<lowercase digest>"
        )
    normalized = PurePosixPath(match.group("path")).as_posix()
    relative = PurePosixPath(normalized)
    if (
        relative.is_absolute()
        or ".." in relative.parts
        or normalized != match.group("path")
    ):
        raise ReviewerAuthorityError(
            f"evidence must use a normalized repository-relative path: {reference!r}"
        )
    root = repository_root.resolve()
    candidate = (root / Path(*relative.parts)).resolve()
    try:
        candidate.relative_to(root)
    except ValueError as error:
        raise ReviewerAuthorityError(
            f"evidence escapes the repository: {reference!r}"
        ) from error
    return normalized, candidate, match.group("sha256")


def verify_bound_evidence(
    repository_root: Path, references: Sequence[str]
) -> tuple[str, ...]:
    """Revalidate persisted evidence against current repository bytes."""

    if not references:
        raise ReviewerAuthorityError("at least one bound evidence file is required")
    if tuple(sorted(set(references))) != tuple(references):
        raise ReviewerAuthorityError("bound evidence must be sorted and unique")
    for reference in references:
        normalized, candidate, expected_sha256 = _evidence_path(
            repository_root, reference
        )
        if not candidate.is_file():
            raise ReviewerAuthorityError(
                f"review evidence does not name an existing file: {normalized}"
            )
        if file_sha256(candidate) != expected_sha256:
            raise ReviewerAuthorityError(
                f"review evidence content changed after approval: {normalized}"
            )
    return tuple(references)


def bind_evidence(repository_root: Path, references: Sequence[str]) -> tuple[str, ...]:
    """Bind review evidence to bytes inside the current repository checkout."""

    root = repository_root.resolve()
    bound: list[str] = []
    seen: set[str] = set()
    for raw in references:
        reference = _require_text(raw, "evidence")
        relative = PurePosixPath(reference)
        if relative.is_absolute() or ".." in relative.parts:
            raise ReviewerAuthorityError(
                f"evidence must be a repository-relative path: {reference!r}"
            )
        normalized = relative.as_posix()
        if normalized in seen:
            raise ReviewerAuthorityError(
                f"review evidence must not contain duplicates: {normalized}"
            )
        seen.add(normalized)
        candidate = (root / Path(*relative.parts)).resolve()
        try:
            candidate.relative_to(root)
        except ValueError as error:
            raise ReviewerAuthorityError(
                f"evidence escapes the repository: {reference!r}"
            ) from error
        if not candidate.is_file():
            raise ReviewerAuthorityError(
                f"review evidence does not name an existing file: {normalized}"
            )
        bound.append(f"{normalized}@sha256:{file_sha256(candidate)}")
    if not bound:
        raise ReviewerAuthorityError("at least one evidence file is required")
    result = tuple(sorted(bound))
    verify_bound_evidence(root, result)
    return result
