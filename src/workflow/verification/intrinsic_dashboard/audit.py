"""Review operations and atomic persistence for the intrinsic dashboard."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Mapping

from .model import (
    ApprovalCount,
    AuditLedger,
    AuditModelError,
    ClaimScope,
    DigestBinding,
    FinalReview,
    IntrinsicArchitecture,
    IntrinsicAudit,
    KernelFileStatus,
    NotReviewableError,
    ProofCheckAttestation,
    ReviewAttestation,
    ReviewChecklist,
)


class AuditPersistenceError(RuntimeError):
    """A persisted audit ledger cannot be read or written safely."""


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _timestamp(value: str | None) -> str:
    if value is not None:
        return value
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def approve_intrinsic(
    intrinsic: IntrinsicAudit,
    *,
    reviewer: str,
    checklist: ReviewChecklist,
    reviewed_at: str | None = None,
    note: str = "",
) -> IntrinsicAudit:
    """Return an independently approved copy bound to both current digests."""

    if not intrinsic.reviewable or intrinsic.semantics_sha256 is None:
        raise NotReviewableError(
            f"{intrinsic.subject_id} has no generated/automated semantic artifact"
        )
    review = ReviewAttestation(
        binding=DigestBinding(
            subject_id=intrinsic.subject_id,
            source_sha256=intrinsic.source_sha256,
            semantics_sha256=intrinsic.semantics_sha256,
        ),
        author=intrinsic.author,
        reviewer=reviewer,
        reviewed_at=_timestamp(reviewed_at),
        checklist=checklist,
        note=note,
    )
    return replace(intrinsic, review=review)


def approval_count(intrinsics: Iterable[IntrinsicAudit]) -> ApprovalCount:
    """Count only current, independently reviewed intrinsic descriptors."""

    records = tuple(intrinsics)
    return ApprovalCount(
        approved=sum(record.status.reviewed for record in records),
        total=len(records),
    )


def build_kernel_file_status(
    *,
    kernel_family: str,
    program_id: str,
    source_path: str,
    artifact_sha256: str,
    author: str,
    claim_scope: ClaimScope,
    neon_intrinsics: Iterable[IntrinsicAudit],
    rvv_intrinsics: Iterable[IntrinsicAudit],
    generated_model_fresh: bool,
    spec_generated: bool,
    proof_generated: bool,
    proof_check: ProofCheckAttestation | None = None,
) -> KernelFileStatus:
    """Aggregate one program without treating stale approvals as current."""

    neon = tuple(neon_intrinsics)
    rvv = tuple(rvv_intrinsics)
    if any(item.architecture is not IntrinsicArchitecture.NEON for item in neon):
        raise AuditModelError("neon_intrinsics contains a non-Neon descriptor")
    if any(item.architecture is not IntrinsicArchitecture.RVV for item in rvv):
        raise AuditModelError("rvv_intrinsics contains a non-RVV descriptor")
    if len({item.subject_id for item in neon}) != len(neon):
        raise AuditModelError("neon_intrinsics contains duplicate descriptors")
    if len({item.subject_id for item in rvv}) != len(rvv):
        raise AuditModelError("rvv_intrinsics contains duplicate descriptors")
    return KernelFileStatus(
        kernel_family=kernel_family,
        program_id=program_id,
        source_path=source_path,
        artifact_sha256=artifact_sha256,
        author=author,
        claim_scope=claim_scope,
        neon=approval_count(neon),
        rvv=approval_count(rvv),
        generated_model_fresh=generated_model_fresh,
        spec_generated=spec_generated,
        proof_generated=proof_generated,
        proof_check=proof_check,
    )


def approve_kernel_file(
    status: KernelFileStatus,
    *,
    reviewer: str,
    evidence: tuple[str, ...],
    reviewed_at: str | None = None,
    note: str = "",
) -> KernelFileStatus:
    """Approve a complete program status and bind every gate through its digest."""

    if not status.ready_for_final_review:
        raise NotReviewableError(
            f"{status.program_id} has not passed every intrinsic/spec/proof/Lean gate"
        )
    review = FinalReview(
        status_sha256=status.review_subject_sha256,
        author=status.author,
        reviewer=reviewer,
        reviewed_at=_timestamp(reviewed_at),
        evidence=evidence,
        note=note,
    )
    return replace(status, final_review=review)


def reconcile_reviews(current: AuditLedger, previous: AuditLedger) -> AuditLedger:
    """Carry attestations into a fresh scan so changed hashes become ``stale``.

    Current records win when they already contain a review.  Reviews are matched
    only by the complete intrinsic subject id or concrete kernel/file identity;
    they are never transferred by a fuzzy spelling or basename match.
    """

    previous_intrinsics = {
        item.subject_id: item.review
        for item in previous.intrinsics
        if item.review is not None
    }
    intrinsics = tuple(
        (
            item
            if item.review is not None or item.subject_id not in previous_intrinsics
            else replace(item, review=previous_intrinsics[item.subject_id])
        )
        for item in current.intrinsics
    )

    def kernel_key(item: KernelFileStatus) -> tuple[str, str, str]:
        return item.kernel_family, item.program_id, item.source_path

    previous_files = {
        kernel_key(item): item.final_review
        for item in previous.kernel_files
        if item.final_review is not None
    }
    kernel_files = tuple(
        (
            item
            if item.final_review is not None or kernel_key(item) not in previous_files
            else replace(item, final_review=previous_files[kernel_key(item)])
        )
        for item in current.kernel_files
    )
    return AuditLedger(intrinsics=intrinsics, kernel_files=kernel_files)


def render_ledger(ledger: AuditLedger) -> str:
    return (
        json.dumps(ledger.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    )


def load_ledger(path: Path) -> AuditLedger:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise AuditPersistenceError(
            f"cannot read audit ledger {path}: {error}"
        ) from error
    if not isinstance(raw, Mapping):
        raise AuditPersistenceError(f"audit ledger {path} must contain a JSON object")
    try:
        return AuditLedger.from_dict(raw)
    except AuditModelError as error:
        raise AuditPersistenceError(f"invalid audit ledger {path}: {error}") from error


def save_ledger(path: Path, ledger: AuditLedger) -> None:
    """Atomically replace ``path`` with a deterministic, fsynced JSON ledger."""

    content = render_ledger(ledger)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary_path = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary_path, path)
        temporary_path = None
        try:
            directory_fd = os.open(path.parent, os.O_RDONLY)
        except OSError:
            directory_fd = None
        if directory_fd is not None:
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    except (OSError, UnicodeError) as error:
        raise AuditPersistenceError(
            f"cannot write audit ledger {path}: {error}"
        ) from error
    finally:
        if temporary_path is not None:
            temporary_path.unlink(missing_ok=True)
