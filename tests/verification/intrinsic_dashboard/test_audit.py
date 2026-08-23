import json
from dataclasses import replace
from hashlib import sha256
from pathlib import Path

import pytest

from src.workflow.verification.intrinsic_dashboard import audit
from src.workflow.verification.intrinsic_dashboard.audit import (
    approve_intrinsic,
    approve_kernel_file,
    approval_count,
    build_kernel_file_status,
    load_ledger,
    reconcile_reviews,
    save_ledger,
)
from src.workflow.verification.intrinsic_dashboard.model import (
    ApprovalCount,
    AuditLedger,
    AuditModelError,
    ClaimScope,
    IntrinsicArchitecture,
    IntrinsicAudit,
    KernelFileStatus,
    LeanCheck,
    NotReviewableError,
    ProofCheckAttestation,
    ReviewChecklist,
    ReviewState,
    SelfApprovalError,
)


REVIEWED_AT = "2026-08-23T12:00:00+09:00"


def _digest(value: str) -> str:
    return sha256(value.encode("ascii")).hexdigest()


def _intrinsic(
    architecture: IntrinsicArchitecture,
    spelling: str,
    *,
    profile: str = "case",
    author: str = "Alice",
) -> IntrinsicAudit:
    side = architecture.value
    return IntrinsicAudit(
        architecture=architecture,
        spelling=spelling,
        profile=profile,
        source_path=f"kernels/{side}/{profile}.c",
        source_sha256=_digest(f"source:{side}:{spelling}:{profile}"),
        semantics_path=f"SALT/Intrinsics/{side}.lean",
        semantics_sha256=_digest(f"semantics:{side}:{spelling}:{profile}"),
        author=author,
        generated=True,
        automated=True,
        related_kernel_families=("qs8-vadd",),
        related_programs=("qs8-vadd-minmax",),
    )


def _checklist() -> ReviewChecklist:
    return ReviewChecklist(
        identity_signature=True,
        operand_order_types=True,
        value_semantics=True,
        fused_rounding_saturation=True,
        architectural_state=True,
        mutation_tests=True,
        evidence=(
            "tests/verification/intrinsic_dashboard/test_audit.py@sha256:"
            + _digest("intrinsic review evidence"),
        ),
    )


def _final_evidence() -> tuple[str, ...]:
    return (
        "tests/verification/intrinsic_dashboard/test_audit.py@sha256:"
        + _digest("final review evidence"),
    )


def _proof_check(
    *,
    project_sha256: str | None = None,
    status: LeanCheck = LeanCheck.PASSED,
    checked_at: str = REVIEWED_AT,
) -> ProofCheckAttestation:
    return ProofCheckAttestation(
        target="SALT.Generated.QS8VAddMinmax.Proof",
        project_sha256=project_sha256 or _digest("lean project"),
        policy_sha256=_digest("proof policy"),
        toolchain="leanprover/lean4:v4.29.0",
        status=status,
        checked_at=checked_at,
    )


def test_intrinsic_review_is_independent_and_hash_bound() -> None:
    intrinsic = _intrinsic(IntrinsicArchitecture.NEON, "vmaxq_s8")

    with pytest.raises(SelfApprovalError):
        approve_intrinsic(
            intrinsic,
            reviewer=" alice ",
            checklist=_checklist(),
            reviewed_at=REVIEWED_AT,
        )

    approved = approve_intrinsic(
        intrinsic,
        reviewer="Bob",
        checklist=_checklist(),
        reviewed_at=REVIEWED_AT,
        note="checked",
    )
    assert approved.review_state is ReviewState.REVIEWED
    assert approved.status.reviewed
    assert not approved.status.stale

    changed_source = replace(approved, source_sha256=_digest("changed source"))
    assert changed_source.review_state is ReviewState.STALE
    assert not changed_source.status.reviewed
    assert changed_source.status.stale

    changed_semantics = replace(approved, semantics_sha256=_digest("changed semantics"))
    assert changed_semantics.review_state is ReviewState.STALE


def test_incomplete_intrinsic_cannot_be_approved() -> None:
    missing = IntrinsicAudit(
        architecture=IntrinsicArchitecture.RVV,
        spelling="__riscv_unknown",
        profile="missing",
        source_path="kernels/target/missing.c",
        source_sha256=_digest("source"),
        semantics_path=None,
        semantics_sha256=None,
        author="Alice",
        generated=False,
        automated=False,
    )
    with pytest.raises(NotReviewableError):
        approve_intrinsic(
            missing,
            reviewer="Bob",
            checklist=_checklist(),
            reviewed_at=REVIEWED_AT,
        )

    with pytest.raises(AuditModelError, match="hash-bound semantics"):
        replace(missing, automated=True)


def test_review_checklist_requires_semantic_checks_and_evidence() -> None:
    with pytest.raises(NotReviewableError, match="fused_rounding_saturation"):
        replace(_checklist(), fused_rounding_saturation=False)
    with pytest.raises(NotReviewableError, match="requires evidence"):
        replace(_checklist(), evidence=())
    with pytest.raises(AuditModelError, match="sorted"):
        replace(
            _checklist(),
            evidence=(
                "tests/z.txt@sha256:" + _digest("z"),
                "tests/a.txt@sha256:" + _digest("a"),
            ),
        )
    with pytest.raises(AuditModelError, match="path@sha256"):
        replace(_checklist(), evidence=("ftp://example.com/evidence",))


def test_reconciliation_preserves_review_and_exposes_staleness() -> None:
    old = approve_intrinsic(
        _intrinsic(IntrinsicArchitecture.NEON, "vminq_s8"),
        reviewer="Bob",
        checklist=_checklist(),
        reviewed_at=REVIEWED_AT,
    )
    rescanned = replace(
        old,
        source_sha256=_digest("new source"),
        review=None,
    )

    reconciled = reconcile_reviews(
        AuditLedger(intrinsics=(rescanned,)), AuditLedger(intrinsics=(old,))
    )
    assert reconciled.intrinsics[0].review is old.review
    assert reconciled.intrinsics[0].status.stale


def test_kernel_status_requires_all_gates_and_independent_final_review() -> None:
    neon = approve_intrinsic(
        _intrinsic(IntrinsicArchitecture.NEON, "vmaxq_s8"),
        reviewer="Bob",
        checklist=_checklist(),
        reviewed_at=REVIEWED_AT,
    )
    rvv = approve_intrinsic(
        _intrinsic(IntrinsicArchitecture.RVV, "__riscv_vmax_vx_i8m2"),
        reviewer="Bob",
        checklist=_checklist(),
        reviewed_at=REVIEWED_AT,
    )
    status = build_kernel_file_status(
        kernel_family="qs8-vadd",
        program_id="qs8-vadd-minmax",
        source_path="kernels/source/qs8-vadd-minmax.c",
        artifact_sha256=_digest("qs8-vadd artifacts"),
        author="Alice",
        claim_scope=ClaimScope.SELECTED_LOCAL_BLOCK,
        neon_intrinsics=(neon,),
        rvv_intrinsics=(rvv,),
        generated_model_fresh=True,
        spec_generated=True,
        proof_generated=True,
        proof_check=_proof_check(),
    )
    assert status.neon == ApprovalCount(approved=1, total=1)
    assert status.rvv == ApprovalCount(approved=1, total=1)
    assert status.ready_for_final_review

    with pytest.raises(SelfApprovalError):
        approve_kernel_file(
            status,
            reviewer="ALICE",
            evidence=_final_evidence(),
            reviewed_at=REVIEWED_AT,
        )

    approved = approve_kernel_file(
        status,
        reviewer="Carol",
        evidence=_final_evidence(),
        reviewed_at=REVIEWED_AT,
    )
    assert approved.final_review_state is ReviewState.REVIEWED
    assert not approved.complete_c_function_verified

    regressed = replace(
        approved,
        proof_check=_proof_check(status=LeanCheck.FAILED),
    )
    assert regressed.final_review_state is ReviewState.STALE
    assert not regressed.ready_for_final_review

    changed_artifact = replace(
        approved, artifact_sha256=_digest("changed qs8-vadd artifacts")
    )
    assert changed_artifact.final_review_state is ReviewState.STALE

    stale_generated_model = replace(approved, generated_model_fresh=False)
    assert stale_generated_model.final_review_state is ReviewState.STALE
    assert not stale_generated_model.ready_for_final_review


def test_final_review_binds_stable_proof_check_and_explicit_claim_scope() -> None:
    neon = approve_intrinsic(
        _intrinsic(IntrinsicArchitecture.NEON, "vmaxq_s8"),
        reviewer="Bob",
        checklist=_checklist(),
        reviewed_at=REVIEWED_AT,
    )
    rvv = approve_intrinsic(
        _intrinsic(IntrinsicArchitecture.RVV, "__riscv_vmax_vx_i8m2"),
        reviewer="Bob",
        checklist=_checklist(),
        reviewed_at=REVIEWED_AT,
    )
    status = build_kernel_file_status(
        kernel_family="qs8-vadd",
        program_id="qs8-vadd-minmax",
        source_path="kernels/source/qs8-vadd-minmax.c",
        artifact_sha256=_digest("qs8-vadd artifacts"),
        author="Alice",
        claim_scope=ClaimScope.SELECTED_LOCAL_BLOCK,
        neon_intrinsics=(neon,),
        rvv_intrinsics=(rvv,),
        generated_model_fresh=True,
        spec_generated=True,
        proof_generated=True,
        proof_check=_proof_check(),
    )
    approved = approve_kernel_file(
        status,
        reviewer="Carol",
        evidence=_final_evidence(),
        reviewed_at=REVIEWED_AT,
    )

    rechecked = replace(
        approved,
        proof_check=replace(
            approved.proof_check,
            checked_at="2026-08-24T12:00:00+09:00",
        ),
    )
    assert rechecked.final_review_state is ReviewState.REVIEWED
    assert rechecked.review_subject_sha256 == approved.review_subject_sha256

    changed_project = replace(
        approved,
        proof_check=replace(
            approved.proof_check,
            project_sha256=_digest("changed Lean project"),
        ),
    )
    assert changed_project.final_review_state is ReviewState.STALE
    assert changed_project.review_subject_sha256 != approved.review_subject_sha256

    assert approved.claim_scope is ClaimScope.SELECTED_LOCAL_BLOCK
    assert approved.final_review_state is ReviewState.REVIEWED
    assert not approved.complete_c_function_verified

    complete_scope = approve_kernel_file(
        replace(status, claim_scope=ClaimScope.COMPLETE_C_FUNCTION),
        reviewer="Carol",
        evidence=_final_evidence(),
        reviewed_at=REVIEWED_AT,
    )
    assert complete_scope.complete_c_function_verified

    payload = approved.to_dict()
    assert KernelFileStatus.from_dict(payload) == approved
    payload["proof_check"]["binding_sha256"] = _digest("tampered binding")
    with pytest.raises(AuditModelError, match="binding digest disagrees"):
        KernelFileStatus.from_dict(payload)


def test_kernel_status_does_not_count_stale_intrinsic_reviews() -> None:
    current = approve_intrinsic(
        _intrinsic(IntrinsicArchitecture.NEON, "vminq_s8"),
        reviewer="Bob",
        checklist=_checklist(),
        reviewed_at=REVIEWED_AT,
    )
    stale = replace(current, semantics_sha256=_digest("changed"))
    assert approval_count((current, stale)) == ApprovalCount(approved=1, total=2)

    with pytest.raises(AuditModelError, match="non-Neon"):
        build_kernel_file_status(
            kernel_family="bad",
            program_id="bad",
            source_path="kernels/source/bad.c",
            artifact_sha256=_digest("bad artifacts"),
            author="Alice",
            claim_scope=ClaimScope.SELECTED_LOCAL_BLOCK,
            neon_intrinsics=(_intrinsic(IntrinsicArchitecture.RVV, "__riscv_bad"),),
            rvv_intrinsics=(),
            generated_model_fresh=False,
            spec_generated=False,
            proof_generated=False,
            proof_check=None,
        )


def test_kernel_final_review_rejects_incomplete_status() -> None:
    incomplete = build_kernel_file_status(
        kernel_family="qs8-vadd",
        program_id="qs8-vadd-minmax",
        source_path="kernels/source/qs8-vadd-minmax.c",
        artifact_sha256=_digest("incomplete artifacts"),
        author="Alice",
        claim_scope=ClaimScope.SELECTED_LOCAL_BLOCK,
        neon_intrinsics=(),
        rvv_intrinsics=(),
        generated_model_fresh=True,
        spec_generated=True,
        proof_generated=True,
        proof_check=_proof_check(),
    )
    with pytest.raises(NotReviewableError):
        approve_kernel_file(
            incomplete,
            reviewer="Bob",
            evidence=_final_evidence(),
            reviewed_at=REVIEWED_AT,
        )


def test_ledger_round_trip_and_derived_status_tamper_detection(
    tmp_path: Path,
) -> None:
    intrinsic = approve_intrinsic(
        _intrinsic(IntrinsicArchitecture.NEON, "vmaxq_s8"),
        reviewer="Bob",
        checklist=_checklist(),
        reviewed_at=REVIEWED_AT,
    )
    ledger = AuditLedger(intrinsics=(intrinsic,))
    path = tmp_path / "audit.json"

    save_ledger(path, ledger)
    first = path.read_bytes()
    assert load_ledger(path) == ledger
    save_ledger(path, ledger)
    assert path.read_bytes() == first

    tampered = json.loads(path.read_text(encoding="utf-8"))
    tampered["intrinsics"][0]["status"]["reviewed"] = False
    path.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(audit.AuditPersistenceError, match="disagrees"):
        load_ledger(path)


def test_atomic_write_preserves_old_file_on_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "audit.json"
    path.write_text("old\n", encoding="utf-8")

    def fail_replace(source: Path, destination: Path) -> None:
        raise OSError("injected failure")

    monkeypatch.setattr(audit.os, "replace", fail_replace)
    with pytest.raises(audit.AuditPersistenceError, match="injected failure"):
        save_ledger(path, AuditLedger())

    assert path.read_text(encoding="utf-8") == "old\n"
    assert list(tmp_path.glob(".audit.json.*.tmp")) == []
