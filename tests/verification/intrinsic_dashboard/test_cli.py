from __future__ import annotations

import json
from hashlib import sha256
from io import StringIO
from pathlib import Path

import pytest

from src.workflow.verification.intrinsic_dashboard.activity import load_activity
from src.workflow.verification.intrinsic_dashboard.authority import (
    DEFAULT_REVIEWER_REGISTRY_RELATIVE_PATH,
)
from src.workflow.verification.intrinsic_dashboard.audit import (
    approve_intrinsic,
    build_kernel_file_status,
    load_ledger,
    reconcile_reviews,
    save_ledger,
)
from src.workflow.verification.intrinsic_dashboard.cli import (
    DigestBoundStateProvider,
    main,
)
from src.workflow.verification.intrinsic_dashboard.model import (
    AuditLedger,
    ClaimScope,
    IntrinsicArchitecture,
    IntrinsicAudit,
    LeanCheck,
    ProofCheckAttestation,
    ReviewChecklist,
    ReviewState,
)
from src.workflow.verification.intrinsic_dashboard.state import (
    DEFAULT_ACTIVITY_RELATIVE_PATH,
    DEFAULT_REVIEW_LEDGER_RELATIVE_PATH,
)


def _digest(value: str) -> str:
    return sha256(value.encode("ascii")).hexdigest()


PROJECT_DIGEST = _digest("lean-project")
POLICY_DIGEST = _digest("proof policy")


def _proof_check(
    status: LeanCheck = LeanCheck.PASSED,
    *,
    project_sha256: str = PROJECT_DIGEST,
    checked_at: str = "2026-08-23T12:00:00+00:00",
) -> ProofCheckAttestation:
    return ProofCheckAttestation(
        target="SALT.Generated.Case.Proof",
        project_sha256=project_sha256,
        policy_sha256=POLICY_DIGEST,
        toolchain="leanprover/lean4:v4.19.0",
        status=status,
        checked_at=checked_at,
    )


def _prepare_review_inputs(tmp_path: Path, *reviewer_ids: str) -> Path:
    registry = tmp_path / DEFAULT_REVIEWER_REGISTRY_RELATIVE_PATH
    registry.parent.mkdir(parents=True, exist_ok=True)
    registry.write_text(
        json.dumps(
            {
                "schema_version": 2,
                "reviewers": [
                    {
                        "id": reviewer_id,
                        "display_name": reviewer_id.title(),
                        "may_review_authors": ["translator"],
                    }
                    for reviewer_id in sorted(reviewer_ids)
                ],
            }
        ),
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence" / "review.txt"
    evidence.parent.mkdir(parents=True, exist_ok=True)
    evidence.write_text("review evidence\n", encoding="utf-8")
    return evidence.relative_to(tmp_path)


def _intrinsic(architecture: IntrinsicArchitecture, spelling: str) -> IntrinsicAudit:
    side = architecture.value
    return IntrinsicAudit(
        architecture=architecture,
        spelling=spelling,
        profile="all-configured-variants-v1",
        source_path="src/workflow/verification/lean_backend/registry.py",
        source_sha256=_digest(f"descriptor:{side}:{spelling}"),
        semantics_path=f"src/verification_bw/lean/SALT/Intrinsics/{side}.lean",
        semantics_sha256=_digest(f"semantics:{side}:{spelling}"),
        author="translator",
        generated=True,
        automated=True,
        related_kernel_families=("case",),
        related_programs=(f"kernels/{side}/case.c",),
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
            "tests/verification/intrinsic_dashboard/test_cli.py@sha256:"
            + _digest("test evidence"),
        ),
    )


class _SnapshotProvider:
    def __init__(self, lean_checks) -> None:
        self.lean_checks = dict(lean_checks)
        self.calls = 0

    def __call__(self) -> dict[str, object]:
        self.calls += 1
        return {
            "revision": "test",
            "checks": {
                key: value.status.value
                for key, value in sorted(self.lean_checks.items())
            },
        }


class _ReviewProvider:
    """Small current-ledger provider used without a real XNNPACK scan."""

    def __init__(self, review_ledger_path: Path, lean_checks) -> None:
        self.review_ledger_path = review_ledger_path
        self.lean_checks = dict(lean_checks)
        self.calls = 0
        self.neon = _intrinsic(IntrinsicArchitecture.NEON, "vmaxq_s8")
        self.rvv = _intrinsic(IntrinsicArchitecture.RVV, "__riscv_vmax_vx_i8m1")

    def current_ledger(self) -> AuditLedger:
        self.calls += 1
        previous = (
            load_ledger(self.review_ledger_path)
            if self.review_ledger_path.exists()
            else AuditLedger()
        )
        intrinsic_ledger = reconcile_reviews(
            AuditLedger(intrinsics=(self.neon, self.rvv)), previous
        )
        neon, rvv = intrinsic_ledger.intrinsics
        status = build_kernel_file_status(
            kernel_family="case",
            program_id="case",
            source_path="kernels/source/case.c",
            artifact_sha256=_digest("case-artifact"),
            author="translator",
            claim_scope=ClaimScope.SELECTED_LOCAL_BLOCK,
            neon_intrinsics=(neon,),
            rvv_intrinsics=(rvv,),
            generated_model_fresh=True,
            spec_generated=True,
            proof_generated=True,
            proof_check=self.lean_checks.get("case"),
        )
        return reconcile_reviews(
            AuditLedger(
                intrinsics=intrinsic_ledger.intrinsics,
                kernel_files=(status,),
            ),
            previous,
        )

    def __call__(self) -> dict[str, object]:
        return {"public": True}


def _all_acknowledgements() -> list[str]:
    return [
        "--ack-identity-signature",
        "--ack-operand-order-types",
        "--ack-value-semantics",
        "--ack-fused-rounding-saturation",
        "--ack-architectural-state",
        "--ack-mutation-tests",
    ]


def test_snapshot_runs_real_injected_checks_and_prints_public_state(
    tmp_path: Path,
) -> None:
    created: list[_SnapshotProvider] = []
    checker_calls: list[tuple[Path, object]] = []

    def factory(_root, **kwargs):
        provider = _SnapshotProvider(kwargs["lean_checks"])
        created.append(provider)
        return provider

    def checker(root, *, cases=None):
        checker_calls.append((root, cases))
        return {"case": _proof_check()}

    stdout = StringIO()
    result = main(
        ["snapshot", "--repository-root", str(tmp_path), "--check-lean"],
        provider_factory=factory,
        proof_checker=checker,
        project_digester=lambda _root: PROJECT_DIGEST,
        policy_digester=lambda _root: POLICY_DIGEST,
        stdout=stdout,
    )

    assert result == 0
    assert json.loads(stdout.getvalue()) == {
        "revision": "test",
        "checks": {"case": "passed"},
    }
    assert checker_calls == [(tmp_path.resolve(), None)]
    assert created[0].calls == 1


def test_digest_bound_provider_downgrades_checks_after_any_lean_change(
    tmp_path: Path,
) -> None:
    provider = _SnapshotProvider({"case": _proof_check()})
    digests = iter((PROJECT_DIGEST, PROJECT_DIGEST, _digest("changed")))
    bound = DigestBoundStateProvider(
        provider,  # type: ignore[arg-type]
        repository_root=tmp_path,
        checks={"case": _proof_check()},
        checked_digest=PROJECT_DIGEST,
        project_digester=lambda _root: next(digests),
        policy_digester=lambda _root: POLICY_DIGEST,
    )

    assert bound()["checks"] == {"case": "passed"}
    assert bound()["checks"] == {}


def test_digest_bound_provider_downgrades_checks_after_policy_change(
    tmp_path: Path,
) -> None:
    provider = _SnapshotProvider({"case": _proof_check()})
    policy_digests = iter((POLICY_DIGEST, POLICY_DIGEST, _digest("changed policy")))
    bound = DigestBoundStateProvider(
        provider,  # type: ignore[arg-type]
        repository_root=tmp_path,
        checks={"case": _proof_check()},
        checked_digest=PROJECT_DIGEST,
        project_digester=lambda _root: PROJECT_DIGEST,
        policy_digester=lambda _root: next(policy_digests),
    )

    assert bound()["checks"] == {"case": "passed"}
    assert bound()["checks"] == {}


def test_checks_that_race_with_a_lean_change_are_never_exposed(
    tmp_path: Path,
) -> None:
    provider: _SnapshotProvider | None = None

    def factory(_root, **kwargs):
        nonlocal provider
        provider = _SnapshotProvider(kwargs["lean_checks"])
        return provider

    before = _digest("before")
    after = _digest("after")
    digests = iter((before, after))
    stdout = StringIO()
    assert (
        main(
            ["snapshot", "--repository-root", str(tmp_path), "--check-lean"],
            provider_factory=factory,
            proof_checker=lambda _root, *, cases=None: {
                "case": _proof_check(project_sha256=before)
            },
            project_digester=lambda _root: next(digests),
            policy_digester=lambda _root: POLICY_DIGEST,
            stdout=stdout,
        )
        == 0
    )
    assert json.loads(stdout.getvalue())["checks"] == {}
    assert provider is not None and provider.lean_checks == {}


def test_serve_uses_cache_aware_provider_and_requested_port(tmp_path: Path) -> None:
    provider = _SnapshotProvider({})
    served: dict[str, object] = {}

    def runner(**kwargs) -> None:
        served.update(kwargs)

    result = main(
        ["serve", "--repository-root", str(tmp_path), "--port", "9123"],
        provider_factory=lambda _root, **_kwargs: provider,
        serve_runner=runner,
    )

    assert result == 0
    assert served["port"] == 9123
    assert isinstance(served["state_provider"], DigestBoundStateProvider)


def test_activity_command_atomically_writes_default_agent_directory(
    tmp_path: Path,
) -> None:
    stdout = StringIO()
    result = main(
        [
            "activity",
            "--repository-root",
            str(tmp_path),
            "--agent-id",
            "translator-1",
            "--name",
            "Translator",
            "--status",
            "running",
            "--task",
            "Map intrinsics",
            "--current-item",
            "vmaxq_s8",
            "--completed",
            "2",
            "--total",
            "5",
        ],
        stdout=stdout,
    )

    assert result == 0
    records = load_activity(tmp_path / DEFAULT_ACTIVITY_RELATIVE_PATH)
    assert len(records) == 1
    assert records[0].agent_id == "translator-1"
    assert records[0].current_item == "vmaxq_s8"
    assert "2/5" in stdout.getvalue()
    assert not list((tmp_path / DEFAULT_ACTIVITY_RELATIVE_PATH).glob(".*.tmp"))


def test_approve_intrinsic_requires_explicit_checks_and_rebuilds_counts(
    tmp_path: Path,
) -> None:
    evidence = _prepare_review_inputs(tmp_path, "reviewer")
    ledger_path = tmp_path / DEFAULT_REVIEW_LEDGER_RELATIVE_PATH
    save_ledger(ledger_path, AuditLedger())
    providers: list[_ReviewProvider] = []

    def factory(_root, **kwargs):
        provider = _ReviewProvider(kwargs["review_ledger_path"], kwargs["lean_checks"])
        providers.append(provider)
        return provider

    subject = "neon:vmaxq_s8@all-configured-variants-v1"
    result = main(
        [
            "approve-intrinsic",
            "--repository-root",
            str(tmp_path),
            "--subject",
            subject,
            "--reviewer",
            "reviewer",
            *_all_acknowledgements(),
            "--evidence",
            evidence.as_posix(),
            "--note",
            "checked against the architecture reference",
        ],
        provider_factory=factory,
    )

    assert result == 0
    saved = load_ledger(ledger_path)
    approved = next(item for item in saved.intrinsics if item.subject_id == subject)
    assert approved.review_state is ReviewState.REVIEWED
    assert approved.review is not None
    assert approved.review.reviewer == "reviewer"
    assert approved.review.checklist.evidence[0].startswith(
        f"{evidence.as_posix()}@sha256:"
    )
    assert approved.review.checklist.fused_rounding_saturation
    assert saved.kernel_files[0].neon.approved == 1
    assert saved.kernel_files[0].rvv.approved == 0
    assert providers[0].calls == 2
    assert not list(ledger_path.parent.glob(".*.tmp"))


def test_approve_intrinsic_has_no_shortcut_for_an_incomplete_checklist(
    tmp_path: Path,
) -> None:
    with pytest.raises(SystemExit) as error:
        main(
            [
                "approve-intrinsic",
                "--repository-root",
                str(tmp_path),
                "--subject",
                "neon:vmaxq_s8@all-configured-variants-v1",
                "--reviewer",
                "Reviewer",
                "--ack-identity-signature",
                "--evidence",
                "tests/evidence.txt",
            ]
        )
    assert error.value.code == 2


def test_approve_intrinsic_rejects_self_review_without_changing_ledger(
    tmp_path: Path,
) -> None:
    evidence = _prepare_review_inputs(tmp_path, "translator")
    ledger_path = tmp_path / DEFAULT_REVIEW_LEDGER_RELATIVE_PATH
    save_ledger(ledger_path, AuditLedger())
    before = ledger_path.read_bytes()
    provider = _ReviewProvider(ledger_path, {})
    stderr = StringIO()

    result = main(
        [
            "approve-intrinsic",
            "--repository-root",
            str(tmp_path),
            "--subject",
            "neon:vmaxq_s8@all-configured-variants-v1",
            "--reviewer",
            "translator",
            *_all_acknowledgements(),
            "--evidence",
            evidence.as_posix(),
        ],
        provider_factory=lambda _root, **_kwargs: provider,
        stderr=stderr,
    )

    assert result == 2
    assert "own author group" in stderr.getvalue()
    assert ledger_path.read_bytes() == before


def test_approve_intrinsic_rejects_untrusted_reviewer_without_changing_ledger(
    tmp_path: Path,
) -> None:
    evidence = _prepare_review_inputs(tmp_path, "trusted-reviewer")
    ledger_path = tmp_path / DEFAULT_REVIEW_LEDGER_RELATIVE_PATH
    save_ledger(ledger_path, AuditLedger())
    before = ledger_path.read_bytes()
    provider = _ReviewProvider(ledger_path, {})
    stderr = StringIO()

    result = main(
        [
            "approve-intrinsic",
            "--repository-root",
            str(tmp_path),
            "--subject",
            "neon:vmaxq_s8@all-configured-variants-v1",
            "--reviewer",
            "untrusted-reviewer",
            *_all_acknowledgements(),
            "--evidence",
            evidence.as_posix(),
        ],
        provider_factory=lambda _root, **_kwargs: provider,
        stderr=stderr,
    )

    assert result == 2
    assert "trusted-reviewer registry" in stderr.getvalue()
    assert ledger_path.read_bytes() == before


@pytest.mark.parametrize("evidence", ("missing.txt", "https://example.com/audit"))
def test_approve_intrinsic_rejects_unbound_evidence(
    tmp_path: Path, evidence: str
) -> None:
    _prepare_review_inputs(tmp_path, "reviewer")
    ledger_path = tmp_path / DEFAULT_REVIEW_LEDGER_RELATIVE_PATH
    save_ledger(ledger_path, AuditLedger())
    before = ledger_path.read_bytes()
    provider = _ReviewProvider(ledger_path, {})

    result = main(
        [
            "approve-intrinsic",
            "--repository-root",
            str(tmp_path),
            "--subject",
            "neon:vmaxq_s8@all-configured-variants-v1",
            "--reviewer",
            "reviewer",
            *_all_acknowledgements(),
            "--evidence",
            evidence,
        ],
        provider_factory=lambda _root, **_kwargs: provider,
    )

    assert result == 2
    assert ledger_path.read_bytes() == before


def test_approve_file_runs_checks_and_saves_only_a_ready_independent_review(
    tmp_path: Path,
) -> None:
    evidence = _prepare_review_inputs(tmp_path, "final-reviewer")
    ledger_path = tmp_path / DEFAULT_REVIEW_LEDGER_RELATIVE_PATH
    neon = approve_intrinsic(
        _intrinsic(IntrinsicArchitecture.NEON, "vmaxq_s8"),
        reviewer="Intrinsic Reviewer",
        checklist=_checklist(),
        reviewed_at="2026-08-23T12:00:00+00:00",
    )
    rvv = approve_intrinsic(
        _intrinsic(IntrinsicArchitecture.RVV, "__riscv_vmax_vx_i8m1"),
        reviewer="Intrinsic Reviewer",
        checklist=_checklist(),
        reviewed_at="2026-08-23T12:00:00+00:00",
    )
    save_ledger(ledger_path, AuditLedger(intrinsics=(neon, rvv)))
    providers: list[_ReviewProvider] = []
    checker_calls = 0

    def factory(_root, **kwargs):
        provider = _ReviewProvider(kwargs["review_ledger_path"], kwargs["lean_checks"])
        providers.append(provider)
        return provider

    def checker(_root, *, cases=None):
        nonlocal checker_calls
        checker_calls += 1
        assert cases is None
        return {"case": _proof_check()}

    result = main(
        [
            "approve-file",
            "--repository-root",
            str(tmp_path),
            "--program-id",
            "case",
            "--reviewer",
            "final-reviewer",
            "--evidence",
            evidence.as_posix(),
            "--note",
            "all gates inspected",
        ],
        provider_factory=factory,
        proof_checker=checker,
        project_digester=lambda _root: PROJECT_DIGEST,
        policy_digester=lambda _root: POLICY_DIGEST,
    )

    assert result == 0
    assert checker_calls == 1
    saved = load_ledger(ledger_path)
    assert saved.kernel_files[0].ready_for_final_review
    assert saved.kernel_files[0].final_review_state is ReviewState.REVIEWED
    assert saved.kernel_files[0].final_review is not None
    assert saved.kernel_files[0].final_review.reviewer == "final-reviewer"
    assert (
        saved.kernel_files[0]
        .final_review.evidence[0]
        .startswith(f"{evidence.as_posix()}@sha256:")
    )
    assert saved.kernel_files[0].claim_scope is ClaimScope.SELECTED_LOCAL_BLOCK
    assert not saved.kernel_files[0].complete_c_function_verified
    assert providers[0].calls == 1


def test_approve_file_rejects_missing_intrinsic_reviews_without_saving(
    tmp_path: Path,
) -> None:
    evidence = _prepare_review_inputs(tmp_path, "final-reviewer")
    ledger_path = tmp_path / DEFAULT_REVIEW_LEDGER_RELATIVE_PATH
    save_ledger(ledger_path, AuditLedger())
    before = ledger_path.read_bytes()
    provider = _ReviewProvider(ledger_path, {"case": _proof_check()})
    stderr = StringIO()

    result = main(
        [
            "approve-file",
            "--repository-root",
            str(tmp_path),
            "--program-id",
            "case",
            "--reviewer",
            "final-reviewer",
            "--evidence",
            evidence.as_posix(),
        ],
        provider_factory=lambda _root, **_kwargs: provider,
        proof_checker=lambda _root, *, cases=None: {"case": _proof_check()},
        project_digester=lambda _root: PROJECT_DIGEST,
        policy_digester=lambda _root: POLICY_DIGEST,
        stderr=stderr,
    )

    assert result == 2
    assert "every intrinsic/spec/proof/Lean gate" in stderr.getvalue()
    assert ledger_path.read_bytes() == before


def test_approve_file_rejects_attestation_for_a_different_project(
    tmp_path: Path,
) -> None:
    evidence = _prepare_review_inputs(tmp_path, "final-reviewer")
    ledger_path = tmp_path / DEFAULT_REVIEW_LEDGER_RELATIVE_PATH
    save_ledger(ledger_path, AuditLedger())
    before = ledger_path.read_bytes()
    stderr = StringIO()

    result = main(
        [
            "approve-file",
            "--repository-root",
            str(tmp_path),
            "--program-id",
            "case",
            "--reviewer",
            "final-reviewer",
            "--evidence",
            evidence.as_posix(),
        ],
        provider_factory=lambda _root, **kwargs: _ReviewProvider(
            kwargs["review_ledger_path"], kwargs["lean_checks"]
        ),
        proof_checker=lambda _root, *, cases=None: {
            "case": _proof_check(project_sha256=_digest("another-project"))
        },
        project_digester=lambda _root: PROJECT_DIGEST,
        policy_digester=lambda _root: POLICY_DIGEST,
        stderr=stderr,
    )

    assert result == 2
    assert "changed while proof checks" in stderr.getvalue()
    assert ledger_path.read_bytes() == before
