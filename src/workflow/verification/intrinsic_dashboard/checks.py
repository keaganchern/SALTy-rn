"""Executable, policy-bound proof checks used by the local dashboard.

The result says only that the protected Lean statement passed the tracked local
proof policy and built successfully against one stable tree. It is not an
intrinsic adequacy or C/ISA correspondence result.
"""

from __future__ import annotations

import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Mapping, Sequence

from .model import LeanCheck, ProofCheckAttestation
from .proof_policy import (
    ResolvedLeanToolchain,
    expected_lean_project_digest,
    lean_project_digest,
    proof_policy_digest,
    resolve_lean_toolchain,
    run_proof_policy_checks,
)
from .targets import PROOF_CASES


PROOF_TARGETS: Mapping[str, str] = {
    case_id: target.module for case_id, target in PROOF_CASES.items()
}


def lean_toolchain(repository_root: Path) -> str:
    """Read the exact non-empty Lean toolchain selector for an attestation."""

    path = repository_root.resolve() / "src/verification_bw/lean/lean-toolchain"
    try:
        toolchain = path.read_text(encoding="utf-8").strip()
    except (OSError, UnicodeError) as error:
        raise FileNotFoundError(f"cannot read Lean toolchain: {path}") from error
    if not toolchain:
        raise ValueError(f"Lean toolchain is empty: {path}")
    return toolchain


def run_lean_proof_checks(
    repository_root: Path,
    *,
    cases: Sequence[str] | None = None,
    runner: Callable[..., subprocess.CompletedProcess[str]] = subprocess.run,
    policy_checker: Callable[..., Mapping[str, bool]] = run_proof_policy_checks,
    policy_digester: Callable[[Path], str] = proof_policy_digest,
    expected_project_digester: Callable[[Path], str] = expected_lean_project_digest,
    toolchain_resolver: Callable[
        [Path], ResolvedLeanToolchain
    ] = resolve_lean_toolchain,
) -> dict[str, ProofCheckAttestation]:
    """Build selected targets and return input-bound proof-check attestations.

    A nominally successful build is reported as failed if any Lean source,
    configuration, or toolchain input changes while that target is being built.
    Such a run did not check one stable project state and cannot be approval
    evidence.
    """

    root = repository_root.resolve()
    lean_root = root / "src/verification_bw/lean"
    if (
        not (lean_root / "lakefile.toml").is_file()
        and not (lean_root / "lakefile.lean").is_file()
    ):
        raise FileNotFoundError(f"Lean project is missing: {lean_root}")

    selected = tuple(PROOF_TARGETS) if cases is None else tuple(cases)
    unknown = sorted(set(selected) - set(PROOF_TARGETS))
    if unknown:
        raise ValueError(f"unknown proof-check cases: {unknown}")

    policy_sha256 = policy_digester(root)
    project_sha256 = lean_project_digest(root)
    expected_project_sha256 = expected_project_digester(root)
    toolchain = toolchain_resolver(root)
    build_results: dict[str, bool] = {}
    for case_id in selected:
        target = PROOF_TARGETS[case_id]
        if project_sha256 != expected_project_sha256:
            build_results[case_id] = False
            continue
        completed = runner(
            [
                str(toolchain.lake_path),
                "--rehash",
                "--no-cache",
                "build",
                target,
            ],
            cwd=lean_root,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            check=False,
            env=toolchain.subprocess_environment(),
        )
        build_results[case_id] = completed.returncode == 0

    inputs_stable = (
        project_sha256 == expected_project_sha256
        and lean_project_digest(root) == project_sha256
        and policy_digester(root) == policy_sha256
    )
    try:
        policy_results = (
            dict(policy_checker(root, cases=selected)) if inputs_stable else {}
        )
    except (
        OSError,
        UnicodeError,
        RuntimeError,
        ValueError,
        subprocess.SubprocessError,
    ):
        policy_results = {}
    policy_stable = (
        inputs_stable
        and lean_project_digest(root) == project_sha256
        and policy_digester(root) == policy_sha256
        and set(policy_results) == set(selected)
        and all(type(value) is bool for value in policy_results.values())
    )

    results: dict[str, ProofCheckAttestation] = {}
    for case_id in selected:
        target = PROOF_TARGETS[case_id]
        status = (
            LeanCheck.PASSED
            if build_results[case_id] and policy_stable and policy_results[case_id]
            else LeanCheck.FAILED
        )
        results[case_id] = ProofCheckAttestation(
            target=target,
            project_sha256=project_sha256,
            policy_sha256=policy_sha256,
            toolchain=toolchain.selector,
            status=status,
            checked_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )
    return results
