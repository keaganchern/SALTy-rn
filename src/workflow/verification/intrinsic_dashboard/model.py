"""Typed audit records for the intrinsic-coverage dashboard.

The persisted booleans shown by the dashboard are derived facts.  In particular,
an intrinsic is reviewed only while an independent review attestation names the
same subject and binds both its current source and semantic-content digests.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = 2
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_BOUND_EVIDENCE_RE = re.compile(r"^.+@sha256:[0-9a-f]{64}$")


class AuditModelError(ValueError):
    """An audit record is malformed or internally inconsistent."""


class SelfApprovalError(AuditModelError):
    """An artifact author attempted to approve their own work."""


class NotReviewableError(AuditModelError):
    """An incomplete artifact was submitted for approval."""


class IntrinsicArchitecture(str, Enum):
    NEON = "neon"
    RVV = "rvv"


class LeanCheck(str, Enum):
    NOT_RUN = "not-run"
    PASSED = "passed"
    FAILED = "failed"


class ClaimScope(str, Enum):
    """The exact semantic boundary covered by a kernel/file claim."""

    LEXICAL_INVENTORY = "lexical-inventory"
    SELECTED_LOCAL_BLOCK = "selected-local-block"
    ARBITRARY_LENGTH_VALUE = "arbitrary-length-value"
    COMPLETE_C_FUNCTION = "complete-c-function"


class ReviewState(str, Enum):
    NOT_REVIEWED = "not-reviewed"
    REVIEWED = "reviewed"
    STALE = "stale"


def _require_text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise AuditModelError(f"{field} must be a non-empty string")
    return value


def _require_bool(value: object, field: str) -> bool:
    if type(value) is not bool:
        raise AuditModelError(f"{field} must be a boolean")
    return value


def _require_digest(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise AuditModelError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _require_optional_digest(value: object, field: str) -> str | None:
    if value is None:
        return None
    return _require_digest(value, field)


def _require_relative_path(value: object, field: str) -> str:
    path = PurePosixPath(_require_text(value, field))
    if path.is_absolute() or ".." in path.parts:
        raise AuditModelError(f"{field} must be a repository-relative path")
    return path.as_posix()


def _require_timestamp(value: object, field: str) -> str:
    timestamp = _require_text(value, field)
    try:
        parsed = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError as error:
        raise AuditModelError(f"{field} must be an ISO-8601 timestamp") from error
    if parsed.tzinfo is None:
        raise AuditModelError(f"{field} must include a timezone")
    return timestamp


def _require_exact_keys(
    data: Mapping[str, Any], expected: set[str], subject: str
) -> None:
    actual = set(data)
    if actual != expected:
        missing = sorted(expected - actual)
        extra = sorted(actual - expected)
        raise AuditModelError(
            f"invalid {subject} fields: missing={missing}, extra={extra}"
        )


def _identity(value: str) -> str:
    return value.strip().casefold()


def _string_tuple(value: object, field: str) -> tuple[str, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise AuditModelError(f"{field} must be a list of strings")
    result = tuple(_require_text(item, field) for item in value)
    if tuple(sorted(set(result))) != result:
        raise AuditModelError(f"{field} must be sorted and contain no duplicates")
    return result


def _evidence_tuple(value: object) -> tuple[str, ...]:
    evidence = _string_tuple(value, "evidence")
    if not evidence:
        raise NotReviewableError("a review requires evidence")
    for reference in evidence:
        if _BOUND_EVIDENCE_RE.fullmatch(reference) is None:
            raise AuditModelError(
                "evidence must have form path@sha256:<lowercase digest>"
            )
        path, _separator, _digest = reference.rpartition("@sha256:")
        _require_relative_path(path, "evidence")
    return evidence


def canonical_sha256(value: object) -> str:
    """Hash a JSON value using the dashboard's canonical representation."""

    encoded = json.dumps(
        value, ensure_ascii=True, separators=(",", ":"), sort_keys=True
    ).encode("ascii")
    return hashlib.sha256(encoded).hexdigest()


@dataclass(frozen=True, slots=True)
class ProofCheckAttestation:
    """A concrete Lean build result bound to the checked project inputs.

    ``binding_sha256`` deliberately excludes ``checked_at``. Re-running the same
    target against byte-identical inputs therefore does not invalidate an
    independent final review, while target, toolchain, status, or project changes
    do invalidate it.
    """

    target: str
    project_sha256: str
    policy_sha256: str
    toolchain: str
    status: LeanCheck
    checked_at: str

    def __post_init__(self) -> None:
        _require_text(self.target, "target")
        _require_digest(self.project_sha256, "project_sha256")
        _require_digest(self.policy_sha256, "policy_sha256")
        _require_text(self.toolchain, "toolchain")
        if self.status not in {LeanCheck.PASSED, LeanCheck.FAILED}:
            raise AuditModelError("proof-check status must be passed or failed")
        _require_timestamp(self.checked_at, "checked_at")

    def _binding_subject(self) -> dict[str, str]:
        return {
            "target": self.target,
            "project_sha256": self.project_sha256,
            "policy_sha256": self.policy_sha256,
            "toolchain": self.toolchain,
            "status": self.status.value,
        }

    @property
    def binding_sha256(self) -> str:
        return canonical_sha256(self._binding_subject())

    def to_dict(self) -> dict[str, str]:
        return {
            **self._binding_subject(),
            "checked_at": self.checked_at,
            "binding_sha256": self.binding_sha256,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ProofCheckAttestation":
        _require_exact_keys(
            data,
            {
                "target",
                "project_sha256",
                "policy_sha256",
                "toolchain",
                "status",
                "checked_at",
                "binding_sha256",
            },
            "proof-check attestation",
        )
        try:
            status = LeanCheck(data["status"])
        except (TypeError, ValueError) as error:
            raise AuditModelError(
                "proof-check status must be passed or failed"
            ) from error
        result = cls(
            target=_require_text(data["target"], "target"),
            project_sha256=_require_digest(data["project_sha256"], "project_sha256"),
            policy_sha256=_require_digest(data["policy_sha256"], "policy_sha256"),
            toolchain=_require_text(data["toolchain"], "toolchain"),
            status=status,
            checked_at=_require_timestamp(data["checked_at"], "checked_at"),
        )
        if _require_digest(data["binding_sha256"], "binding_sha256") != (
            result.binding_sha256
        ):
            raise AuditModelError(
                "persisted proof-check binding digest disagrees with its inputs"
            )
        return result


@dataclass(frozen=True, slots=True)
class DigestBinding:
    """The exact intrinsic identity and contents approved by a reviewer."""

    subject_id: str
    source_sha256: str
    semantics_sha256: str

    def __post_init__(self) -> None:
        _require_text(self.subject_id, "subject_id")
        _require_digest(self.source_sha256, "source_sha256")
        _require_digest(self.semantics_sha256, "semantics_sha256")

    def to_dict(self) -> dict[str, str]:
        return {
            "subject_id": self.subject_id,
            "source_sha256": self.source_sha256,
            "semantics_sha256": self.semantics_sha256,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "DigestBinding":
        _require_exact_keys(
            data,
            {"subject_id", "source_sha256", "semantics_sha256"},
            "digest binding",
        )
        return cls(
            subject_id=_require_text(data["subject_id"], "subject_id"),
            source_sha256=_require_digest(data["source_sha256"], "source_sha256"),
            semantics_sha256=_require_digest(
                data["semantics_sha256"], "semantics_sha256"
            ),
        )


@dataclass(frozen=True, slots=True)
class ReviewChecklist:
    """Required semantic-review questions and their supporting evidence."""

    identity_signature: bool
    operand_order_types: bool
    value_semantics: bool
    fused_rounding_saturation: bool
    architectural_state: bool
    mutation_tests: bool
    evidence: tuple[str, ...]

    def __post_init__(self) -> None:
        checks = {
            "identity_signature": self.identity_signature,
            "operand_order_types": self.operand_order_types,
            "value_semantics": self.value_semantics,
            "fused_rounding_saturation": self.fused_rounding_saturation,
            "architectural_state": self.architectural_state,
            "mutation_tests": self.mutation_tests,
        }
        for field, value in checks.items():
            _require_bool(value, field)
        incomplete = sorted(field for field, value in checks.items() if not value)
        if incomplete:
            raise NotReviewableError(
                f"intrinsic review checklist is incomplete: {incomplete}"
            )
        _evidence_tuple(self.evidence)

    def to_dict(self) -> dict[str, object]:
        return {
            "identity_signature": self.identity_signature,
            "operand_order_types": self.operand_order_types,
            "value_semantics": self.value_semantics,
            "fused_rounding_saturation": self.fused_rounding_saturation,
            "architectural_state": self.architectural_state,
            "mutation_tests": self.mutation_tests,
            "evidence": list(self.evidence),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReviewChecklist":
        boolean_fields = {
            "identity_signature",
            "operand_order_types",
            "value_semantics",
            "fused_rounding_saturation",
            "architectural_state",
            "mutation_tests",
        }
        _require_exact_keys(data, boolean_fields | {"evidence"}, "review checklist")
        return cls(
            **{field: _require_bool(data[field], field) for field in boolean_fields},
            evidence=_evidence_tuple(data["evidence"]),
        )


@dataclass(frozen=True, slots=True)
class ReviewAttestation:
    """An independent, hash-bound review of an intrinsic implementation."""

    binding: DigestBinding
    author: str
    reviewer: str
    reviewed_at: str
    checklist: ReviewChecklist
    note: str = ""

    def __post_init__(self) -> None:
        _require_text(self.author, "author")
        _require_text(self.reviewer, "reviewer")
        _require_timestamp(self.reviewed_at, "reviewed_at")
        if not isinstance(self.checklist, ReviewChecklist):
            raise AuditModelError("checklist must be a complete review checklist")
        if not isinstance(self.note, str):
            raise AuditModelError("note must be a string")
        if _identity(self.author) == _identity(self.reviewer):
            raise SelfApprovalError("an author cannot approve their own intrinsic")

    def to_dict(self) -> dict[str, object]:
        return {
            "binding": self.binding.to_dict(),
            "author": self.author,
            "reviewer": self.reviewer,
            "reviewed_at": self.reviewed_at,
            "checklist": self.checklist.to_dict(),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ReviewAttestation":
        _require_exact_keys(
            data,
            {"binding", "author", "reviewer", "reviewed_at", "checklist", "note"},
            "review attestation",
        )
        binding = data["binding"]
        if not isinstance(binding, Mapping):
            raise AuditModelError("binding must be an object")
        checklist = data["checklist"]
        if not isinstance(checklist, Mapping):
            raise AuditModelError("checklist must be an object")
        if not isinstance(data["note"], str):
            raise AuditModelError("note must be a string")
        return cls(
            binding=DigestBinding.from_dict(binding),
            author=_require_text(data["author"], "author"),
            reviewer=_require_text(data["reviewer"], "reviewer"),
            reviewed_at=_require_timestamp(data["reviewed_at"], "reviewed_at"),
            checklist=ReviewChecklist.from_dict(checklist),
            note=data["note"],
        )


@dataclass(frozen=True, slots=True)
class IntrinsicStatus:
    generated: bool
    automated: bool
    reviewed: bool
    stale: bool

    def __post_init__(self) -> None:
        for field, value in (
            ("generated", self.generated),
            ("automated", self.automated),
            ("reviewed", self.reviewed),
            ("stale", self.stale),
        ):
            _require_bool(value, field)
        if self.reviewed and self.stale:
            raise AuditModelError("reviewed and stale cannot both be true")

    def to_dict(self) -> dict[str, bool]:
        return {
            "generated": self.generated,
            "automated": self.automated,
            "reviewed": self.reviewed,
            "stale": self.stale,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "IntrinsicStatus":
        expected = {"generated", "automated", "reviewed", "stale"}
        _require_exact_keys(data, expected, "intrinsic status")
        return cls(**{field: _require_bool(data[field], field) for field in expected})


@dataclass(frozen=True, slots=True)
class IntrinsicAudit:
    """Current evidence and optional review for one case-scoped intrinsic."""

    architecture: IntrinsicArchitecture
    spelling: str
    profile: str
    source_path: str
    source_sha256: str
    semantics_path: str | None
    semantics_sha256: str | None
    author: str
    generated: bool
    automated: bool
    related_kernel_families: tuple[str, ...] = ()
    related_programs: tuple[str, ...] = ()
    review: ReviewAttestation | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.architecture, IntrinsicArchitecture):
            raise AuditModelError("architecture must be neon or rvv")
        _require_text(self.spelling, "spelling")
        _require_text(self.profile, "profile")
        _require_relative_path(self.source_path, "source_path")
        _require_digest(self.source_sha256, "source_sha256")
        _require_text(self.author, "author")
        _require_bool(self.generated, "generated")
        _require_bool(self.automated, "automated")
        _string_tuple(self.related_kernel_families, "related_kernel_families")
        _string_tuple(self.related_programs, "related_programs")

        if (self.semantics_path is None) != (self.semantics_sha256 is None):
            raise AuditModelError(
                "semantics_path and semantics_sha256 must either both exist or both be absent"
            )
        if self.semantics_path is not None:
            _require_relative_path(self.semantics_path, "semantics_path")
            _require_digest(self.semantics_sha256, "semantics_sha256")
        if (self.generated or self.automated) and self.semantics_sha256 is None:
            raise AuditModelError(
                "generated or automated intrinsics require hash-bound semantics"
            )
        if self.review is not None:
            if self.review.binding.subject_id != self.subject_id:
                raise AuditModelError("review is bound to a different intrinsic")

    @property
    def subject_id(self) -> str:
        return f"{self.architecture.value}:{self.spelling}@{self.profile}"

    @property
    def reviewable(self) -> bool:
        return (self.generated or self.automated) and self.semantics_sha256 is not None

    @property
    def review_state(self) -> ReviewState:
        if self.review is None:
            return ReviewState.NOT_REVIEWED
        binding = self.review.binding
        if (
            self.reviewable
            and binding.subject_id == self.subject_id
            and _identity(self.review.author) == _identity(self.author)
            and binding.source_sha256 == self.source_sha256
            and binding.semantics_sha256 == self.semantics_sha256
        ):
            return ReviewState.REVIEWED
        return ReviewState.STALE

    @property
    def status(self) -> IntrinsicStatus:
        state = self.review_state
        return IntrinsicStatus(
            generated=self.generated,
            automated=self.automated,
            reviewed=state is ReviewState.REVIEWED,
            stale=state is ReviewState.STALE,
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "architecture": self.architecture.value,
            "spelling": self.spelling,
            "profile": self.profile,
            "source_path": self.source_path,
            "source_sha256": self.source_sha256,
            "semantics_path": self.semantics_path,
            "semantics_sha256": self.semantics_sha256,
            "author": self.author,
            "related_kernel_families": list(self.related_kernel_families),
            "related_programs": list(self.related_programs),
            "status": self.status.to_dict(),
            "review": None if self.review is None else self.review.to_dict(),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "IntrinsicAudit":
        expected = {
            "architecture",
            "spelling",
            "profile",
            "source_path",
            "source_sha256",
            "semantics_path",
            "semantics_sha256",
            "author",
            "related_kernel_families",
            "related_programs",
            "status",
            "review",
        }
        _require_exact_keys(data, expected, "intrinsic audit")
        status_data = data["status"]
        if not isinstance(status_data, Mapping):
            raise AuditModelError("status must be an object")
        persisted_status = IntrinsicStatus.from_dict(status_data)
        review_data = data["review"]
        if review_data is not None and not isinstance(review_data, Mapping):
            raise AuditModelError("review must be null or an object")
        try:
            architecture = IntrinsicArchitecture(data["architecture"])
        except (TypeError, ValueError) as error:
            raise AuditModelError("architecture must be neon or rvv") from error
        result = cls(
            architecture=architecture,
            spelling=_require_text(data["spelling"], "spelling"),
            profile=_require_text(data["profile"], "profile"),
            source_path=_require_relative_path(data["source_path"], "source_path"),
            source_sha256=_require_digest(data["source_sha256"], "source_sha256"),
            semantics_path=(
                None
                if data["semantics_path"] is None
                else _require_relative_path(data["semantics_path"], "semantics_path")
            ),
            semantics_sha256=_require_optional_digest(
                data["semantics_sha256"], "semantics_sha256"
            ),
            author=_require_text(data["author"], "author"),
            generated=persisted_status.generated,
            automated=persisted_status.automated,
            related_kernel_families=_string_tuple(
                data["related_kernel_families"], "related_kernel_families"
            ),
            related_programs=_string_tuple(
                data["related_programs"], "related_programs"
            ),
            review=(
                None
                if review_data is None
                else ReviewAttestation.from_dict(review_data)
            ),
        )
        if result.status != persisted_status:
            raise AuditModelError(
                "persisted intrinsic status disagrees with its hash-bound review"
            )
        return result


@dataclass(frozen=True, slots=True)
class ApprovalCount:
    approved: int
    total: int

    def __post_init__(self) -> None:
        if type(self.approved) is not int or type(self.total) is not int:
            raise AuditModelError("approval counts must be integers")
        if self.total < 0 or self.approved < 0 or self.approved > self.total:
            raise AuditModelError("approval counts must satisfy 0 <= approved <= total")

    @property
    def complete(self) -> bool:
        return self.total > 0 and self.approved == self.total

    def to_dict(self) -> dict[str, int]:
        return {"approved": self.approved, "total": self.total}

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ApprovalCount":
        _require_exact_keys(data, {"approved", "total"}, "approval count")
        return cls(approved=data["approved"], total=data["total"])


@dataclass(frozen=True, slots=True)
class FinalReview:
    """An independent approval bound to a complete kernel/file status digest."""

    status_sha256: str
    author: str
    reviewer: str
    reviewed_at: str
    evidence: tuple[str, ...]
    note: str = ""

    def __post_init__(self) -> None:
        _require_digest(self.status_sha256, "status_sha256")
        _require_text(self.author, "author")
        _require_text(self.reviewer, "reviewer")
        _require_timestamp(self.reviewed_at, "reviewed_at")
        _evidence_tuple(self.evidence)
        if not isinstance(self.note, str):
            raise AuditModelError("note must be a string")
        if _identity(self.author) == _identity(self.reviewer):
            raise SelfApprovalError("an author cannot approve their own kernel status")

    def to_dict(self) -> dict[str, object]:
        return {
            "status_sha256": self.status_sha256,
            "author": self.author,
            "reviewer": self.reviewer,
            "reviewed_at": self.reviewed_at,
            "evidence": list(self.evidence),
            "note": self.note,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "FinalReview":
        _require_exact_keys(
            data,
            {
                "status_sha256",
                "author",
                "reviewer",
                "reviewed_at",
                "evidence",
                "note",
            },
            "final review",
        )
        if not isinstance(data["note"], str):
            raise AuditModelError("note must be a string")
        return cls(
            status_sha256=_require_digest(data["status_sha256"], "status_sha256"),
            author=_require_text(data["author"], "author"),
            reviewer=_require_text(data["reviewer"], "reviewer"),
            reviewed_at=_require_timestamp(data["reviewed_at"], "reviewed_at"),
            evidence=_evidence_tuple(data["evidence"]),
            note=data["note"],
        )


@dataclass(frozen=True, slots=True)
class KernelFileStatus:
    """Review and proof progress for one concrete Neon/RVV program pair."""

    kernel_family: str
    program_id: str
    source_path: str
    artifact_sha256: str
    author: str
    claim_scope: ClaimScope
    neon: ApprovalCount
    rvv: ApprovalCount
    generated_model_fresh: bool
    spec_generated: bool
    proof_generated: bool
    proof_check: ProofCheckAttestation | None = None
    final_review: FinalReview | None = None

    def __post_init__(self) -> None:
        _require_text(self.kernel_family, "kernel_family")
        _require_text(self.program_id, "program_id")
        _require_relative_path(self.source_path, "source_path")
        _require_digest(self.artifact_sha256, "artifact_sha256")
        _require_text(self.author, "author")
        if not isinstance(self.claim_scope, ClaimScope):
            raise AuditModelError("claim_scope must be a recognized claim scope")
        _require_bool(self.spec_generated, "spec_generated")
        _require_bool(self.proof_generated, "proof_generated")
        _require_bool(self.generated_model_fresh, "generated_model_fresh")
        if not isinstance(self.neon, ApprovalCount) or not isinstance(
            self.rvv, ApprovalCount
        ):
            raise AuditModelError("neon and rvv must be approval counts")
        if self.proof_check is not None and not isinstance(
            self.proof_check, ProofCheckAttestation
        ):
            raise AuditModelError(
                "proof_check must be null or a proof-check attestation"
            )
        if self.proof_check is not None and not self.proof_generated:
            raise AuditModelError(
                "proof-check evidence cannot exist without a generated proof"
            )
        if self.final_review is not None:
            if (
                self.final_review.status_sha256 == self.review_subject_sha256
                and _identity(self.final_review.author) == _identity(self.author)
                and not self.ready_for_final_review
            ):
                raise AuditModelError(
                    "a current final review cannot approve an incomplete kernel status"
                )

    @property
    def ready_for_final_review(self) -> bool:
        return (
            self.neon.complete
            and self.rvv.complete
            and self.generated_model_fresh
            and self.spec_generated
            and self.proof_generated
            and self.proof_check is not None
            and self.proof_check.status is LeanCheck.PASSED
        )

    @property
    def lean_check(self) -> LeanCheck:
        """Dashboard projection; the actual evidence is ``proof_check``."""

        if self.proof_check is None:
            return LeanCheck.NOT_RUN
        return self.proof_check.status

    @property
    def review_subject_sha256(self) -> str:
        return canonical_sha256(self._review_subject())

    @property
    def final_review_state(self) -> ReviewState:
        if self.final_review is None:
            return ReviewState.NOT_REVIEWED
        if (
            self.ready_for_final_review
            and _identity(self.final_review.author) == _identity(self.author)
            and self.final_review.status_sha256 == self.review_subject_sha256
        ):
            return ReviewState.REVIEWED
        return ReviewState.STALE

    @property
    def complete_c_function_verified(self) -> bool:
        """Whether a current final review explicitly covers a complete C body."""

        return (
            self.claim_scope is ClaimScope.COMPLETE_C_FUNCTION
            and self.final_review_state is ReviewState.REVIEWED
        )

    def _review_subject(self) -> dict[str, object]:
        return {
            "kernel_family": self.kernel_family,
            "program_id": self.program_id,
            "source_path": self.source_path,
            "artifact_sha256": self.artifact_sha256,
            "author": self.author,
            "claim_scope": self.claim_scope.value,
            "neon": self.neon.to_dict(),
            "rvv": self.rvv.to_dict(),
            "generated_model_fresh": self.generated_model_fresh,
            "spec_generated": self.spec_generated,
            "proof_generated": self.proof_generated,
            "lean_check": self.lean_check.value,
            "proof_check_sha256": (
                None if self.proof_check is None else self.proof_check.binding_sha256
            ),
        }

    def to_dict(self) -> dict[str, object]:
        state = self.final_review_state
        return {
            **self._review_subject(),
            "proof_check": (
                None if self.proof_check is None else self.proof_check.to_dict()
            ),
            "final_reviewed": state is ReviewState.REVIEWED,
            "final_review_stale": state is ReviewState.STALE,
            "complete_c_function_verified": self.complete_c_function_verified,
            "final_review": (
                None if self.final_review is None else self.final_review.to_dict()
            ),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "KernelFileStatus":
        expected = {
            "kernel_family",
            "program_id",
            "source_path",
            "artifact_sha256",
            "author",
            "claim_scope",
            "neon",
            "rvv",
            "generated_model_fresh",
            "spec_generated",
            "proof_generated",
            "lean_check",
            "proof_check_sha256",
            "proof_check",
            "final_reviewed",
            "final_review_stale",
            "complete_c_function_verified",
            "final_review",
        }
        _require_exact_keys(data, expected, "kernel file status")
        if not isinstance(data["neon"], Mapping) or not isinstance(
            data["rvv"], Mapping
        ):
            raise AuditModelError("neon and rvv must be objects")
        review_data = data["final_review"]
        if review_data is not None and not isinstance(review_data, Mapping):
            raise AuditModelError("final_review must be null or an object")
        proof_check_data = data["proof_check"]
        if proof_check_data is not None and not isinstance(proof_check_data, Mapping):
            raise AuditModelError("proof_check must be null or an object")
        try:
            persisted_lean_check = LeanCheck(data["lean_check"])
        except (TypeError, ValueError) as error:
            raise AuditModelError(
                "lean_check must be not-run, passed, or failed"
            ) from error
        try:
            claim_scope = ClaimScope(data["claim_scope"])
        except (TypeError, ValueError) as error:
            raise AuditModelError("claim_scope is not recognized") from error
        result = cls(
            kernel_family=_require_text(data["kernel_family"], "kernel_family"),
            program_id=_require_text(data["program_id"], "program_id"),
            source_path=_require_relative_path(data["source_path"], "source_path"),
            artifact_sha256=_require_digest(data["artifact_sha256"], "artifact_sha256"),
            author=_require_text(data["author"], "author"),
            claim_scope=claim_scope,
            neon=ApprovalCount.from_dict(data["neon"]),
            rvv=ApprovalCount.from_dict(data["rvv"]),
            generated_model_fresh=_require_bool(
                data["generated_model_fresh"], "generated_model_fresh"
            ),
            spec_generated=_require_bool(data["spec_generated"], "spec_generated"),
            proof_generated=_require_bool(data["proof_generated"], "proof_generated"),
            proof_check=(
                None
                if proof_check_data is None
                else ProofCheckAttestation.from_dict(proof_check_data)
            ),
            final_review=(
                None if review_data is None else FinalReview.from_dict(review_data)
            ),
        )
        if result.lean_check is not persisted_lean_check:
            raise AuditModelError(
                "persisted lean_check disagrees with proof-check attestation"
            )
        persisted_check_digest = _require_optional_digest(
            data["proof_check_sha256"], "proof_check_sha256"
        )
        current_check_digest = (
            None if result.proof_check is None else result.proof_check.binding_sha256
        )
        if persisted_check_digest != current_check_digest:
            raise AuditModelError(
                "persisted proof-check digest disagrees with its attestation"
            )
        state = result.final_review_state
        if _require_bool(data["final_reviewed"], "final_reviewed") != (
            state is ReviewState.REVIEWED
        ) or _require_bool(data["final_review_stale"], "final_review_stale") != (
            state is ReviewState.STALE
        ):
            raise AuditModelError(
                "persisted final-review status disagrees with its status digest"
            )
        if (
            _require_bool(
                data["complete_c_function_verified"],
                "complete_c_function_verified",
            )
            != result.complete_c_function_verified
        ):
            raise AuditModelError(
                "persisted complete-C verification status disagrees with claim scope"
            )
        return result


@dataclass(frozen=True, slots=True)
class AuditLedger:
    intrinsics: tuple[IntrinsicAudit, ...] = ()
    kernel_files: tuple[KernelFileStatus, ...] = ()
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if (
            type(self.schema_version) is not int
            or self.schema_version != SCHEMA_VERSION
        ):
            raise AuditModelError(
                f"unsupported audit schema version: {self.schema_version!r}"
            )
        intrinsic_ids = [record.subject_id for record in self.intrinsics]
        if len(intrinsic_ids) != len(set(intrinsic_ids)):
            raise AuditModelError("duplicate intrinsic audit subjects")
        file_ids = [
            (record.kernel_family, record.program_id, record.source_path)
            for record in self.kernel_files
        ]
        if len(file_ids) != len(set(file_ids)):
            raise AuditModelError("duplicate kernel file statuses")

    def to_dict(self) -> dict[str, object]:
        return {
            "schema_version": self.schema_version,
            "intrinsics": [
                record.to_dict()
                for record in sorted(self.intrinsics, key=lambda item: item.subject_id)
            ],
            "kernel_files": [
                record.to_dict()
                for record in sorted(
                    self.kernel_files,
                    key=lambda item: (
                        item.kernel_family,
                        item.program_id,
                        item.source_path,
                    ),
                )
            ],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "AuditLedger":
        _require_exact_keys(
            data, {"schema_version", "intrinsics", "kernel_files"}, "audit ledger"
        )
        if not isinstance(data["intrinsics"], list) or not isinstance(
            data["kernel_files"], list
        ):
            raise AuditModelError("intrinsics and kernel_files must be lists")
        if any(not isinstance(item, Mapping) for item in data["intrinsics"]):
            raise AuditModelError("every intrinsic must be an object")
        if any(not isinstance(item, Mapping) for item in data["kernel_files"]):
            raise AuditModelError("every kernel file must be an object")
        return cls(
            intrinsics=tuple(
                IntrinsicAudit.from_dict(item) for item in data["intrinsics"]
            ),
            kernel_files=tuple(
                KernelFileStatus.from_dict(item) for item in data["kernel_files"]
            ),
            schema_version=data["schema_version"],
        )
