import subprocess
from pathlib import Path

import pytest

from src.workflow.verification.intrinsic_dashboard.checks import (
    PROOF_TARGETS,
    lean_project_digest,
    lean_toolchain,
    run_lean_proof_checks,
)
from src.workflow.verification.intrinsic_dashboard.model import (
    LeanCheck,
    ProofCheckAttestation,
)
from src.workflow.verification.intrinsic_dashboard.proof_policy import (
    resolve_lean_toolchain,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[3]


def test_proof_checks_report_actual_process_status() -> None:
    calls: list[tuple[list[str], Path]] = []
    events: list[str] = []

    def runner(command, *, cwd, **_kwargs):
        events.append(f"build:{command[-1]}")
        calls.append((command, cwd))
        return subprocess.CompletedProcess(
            command, 0 if "S8VClamp" in command[-1] else 1
        )

    def policy_checker(_root, *, cases=None):
        events.append("audit")
        return {case_id: True for case_id in cases or ()}

    result = run_lean_proof_checks(
        REPOSITORY_ROOT,
        cases=("s8-vclamp", "qs8-vcvt"),
        runner=runner,
        policy_checker=policy_checker,
        policy_digester=lambda _root: "f" * 64,
        expected_project_digester=lean_project_digest,
        protected_project_digester=lean_project_digest,
    )

    assert all(isinstance(item, ProofCheckAttestation) for item in result.values())
    assert result["s8-vclamp"].status is LeanCheck.PASSED
    assert result["qs8-vcvt"].status is LeanCheck.FAILED
    assert result["s8-vclamp"].target == PROOF_TARGETS["s8-vclamp"]
    assert result["s8-vclamp"].project_sha256 == lean_project_digest(REPOSITORY_ROOT)
    assert result["s8-vclamp"].toolchain == lean_toolchain(REPOSITORY_ROOT)
    assert Path(calls[0][0][0]).name == "lake"
    assert calls[0][0][1:] == [
        "--rehash",
        "--no-cache",
        "build",
        PROOF_TARGETS["s8-vclamp"],
    ]
    assert calls[0][1] == REPOSITORY_ROOT / "src/verification_bw/lean"
    assert events == [
        f"build:{PROOF_TARGETS['s8-vclamp']}",
        f"build:{PROOF_TARGETS['qs8-vcvt']}",
        "audit",
    ]


def test_proof_checks_reject_unknown_cases() -> None:
    with pytest.raises(ValueError, match="unknown proof-check"):
        run_lean_proof_checks(REPOSITORY_ROOT, cases=("unknown",))


def test_successful_build_fails_when_proof_policy_fails() -> None:
    def runner(command, *, cwd, **_kwargs):
        return subprocess.CompletedProcess(command, 0)

    result = run_lean_proof_checks(
        REPOSITORY_ROOT,
        cases=("s8-vclamp",),
        runner=runner,
        policy_checker=lambda _root, *, cases=None: {"s8-vclamp": False},
        policy_digester=lambda _root: "f" * 64,
    )["s8-vclamp"]

    assert result.status is LeanCheck.FAILED


def test_candidate_live_digest_need_not_equal_protected_review_digest(
    tmp_path: Path,
) -> None:
    lean_root = tmp_path / "src/verification_bw/lean"
    lean_root.mkdir(parents=True)
    (lean_root / "lakefile.toml").write_text('name = "test"\n', encoding="ascii")
    (lean_root / "CandidateProof.lean").write_text(
        "theorem candidate : True := by trivial\n", encoding="ascii"
    )
    live_digest = lean_project_digest(tmp_path)
    protected_digest = "a" * 64
    resolved_toolchain = resolve_lean_toolchain(REPOSITORY_ROOT)

    result = run_lean_proof_checks(
        tmp_path,
        cases=("s8-vclamp",),
        runner=lambda command, **_kwargs: subprocess.CompletedProcess(command, 0),
        policy_checker=lambda _root, *, cases=None: {"s8-vclamp": True},
        policy_digester=lambda _root: "f" * 64,
        expected_project_digester=lambda _root: protected_digest,
        protected_project_digester=lambda _root: protected_digest,
        toolchain_resolver=lambda _root: resolved_toolchain,
    )["s8-vclamp"]

    assert live_digest != protected_digest
    assert result.project_sha256 == live_digest
    assert result.status is LeanCheck.PASSED


def test_lean_project_digest_changes_with_source(tmp_path: Path) -> None:
    lean_root = tmp_path / "src/verification_bw/lean"
    source = lean_root / "SALT/Test.lean"
    source.parent.mkdir(parents=True)
    source.write_text("def value := 1\n", encoding="ascii")
    (lean_root / "lean-toolchain").write_text("leanprover/lean4:v4.19.0\n")

    before = lean_project_digest(tmp_path)
    source.write_text("def value := 2\n", encoding="ascii")
    assert lean_project_digest(tmp_path) != before


def test_successful_process_fails_closed_if_project_changes_during_check(
    tmp_path: Path,
) -> None:
    lean_root = tmp_path / "src/verification_bw/lean"
    source = lean_root / "SALT/Test.lean"
    source.parent.mkdir(parents=True)
    source.write_text("def value := 1\n", encoding="ascii")
    (lean_root / "lakefile.toml").write_text('name = "test"\n', encoding="ascii")
    (lean_root / "lean-toolchain").write_text(
        "leanprover/lean4:v4.29.0\n", encoding="ascii"
    )

    before = lean_project_digest(tmp_path)
    resolved_toolchain = resolve_lean_toolchain(REPOSITORY_ROOT)

    def runner(command, *, cwd, **_kwargs):
        source.write_text("def value := 2\n", encoding="ascii")
        return subprocess.CompletedProcess(command, 0)

    result = run_lean_proof_checks(
        tmp_path,
        cases=("s8-vclamp",),
        runner=runner,
        policy_checker=lambda _root, *, cases=None: {"s8-vclamp": True},
        policy_digester=lambda _root: "f" * 64,
        expected_project_digester=lambda _root: before,
        protected_project_digester=lean_project_digest,
        toolchain_resolver=lambda _root: resolved_toolchain,
    )["s8-vclamp"]

    assert result.project_sha256 == before
    assert result.status is LeanCheck.FAILED
    assert result.target == PROOF_TARGETS["s8-vclamp"]


def test_stable_tree_different_from_reviewed_baseline_is_not_built(
    tmp_path: Path,
) -> None:
    lean_root = tmp_path / "src/verification_bw/lean"
    source = lean_root / "SALT/Test.lean"
    source.parent.mkdir(parents=True)
    source.write_text("def value := 1\n", encoding="ascii")
    (lean_root / "lakefile.toml").write_text('name = "test"\n', encoding="ascii")
    (lean_root / "lean-toolchain").write_text(
        "leanprover/lean4:v4.29.0\n", encoding="ascii"
    )
    reviewed_digest = lean_project_digest(tmp_path)
    source.write_text("def value := True\n", encoding="ascii")
    resolved_toolchain = resolve_lean_toolchain(REPOSITORY_ROOT)
    calls = 0

    def runner(command, **_kwargs):
        nonlocal calls
        calls += 1
        return subprocess.CompletedProcess(command, 0)

    result = run_lean_proof_checks(
        tmp_path,
        cases=("s8-vclamp",),
        runner=runner,
        policy_checker=lambda _root, *, cases=None: {"s8-vclamp": True},
        policy_digester=lambda _root: "f" * 64,
        expected_project_digester=lambda _root: reviewed_digest,
        protected_project_digester=lean_project_digest,
        toolchain_resolver=lambda _root: resolved_toolchain,
    )["s8-vclamp"]

    assert calls == 0
    assert result.status is LeanCheck.FAILED
