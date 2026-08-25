from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest

import src.workflow.verification.intrinsic_dashboard.proof_policy as proof_policy
from src.workflow.verification.intrinsic_dashboard.checks import PROOF_TARGETS
from src.workflow.verification.intrinsic_dashboard.proof_policy import (
    AUDIT_OUTPUT_PREFIX,
    POLICY_RELATIVE_PATH,
    ElaboratedTheoremAudit,
    ProofPolicyError,
    _run_elaborated_audit,
    _forbidden_tokens_absent,
    _strip_lean_comments_and_strings,
    _toolchain_runtime_digest,
    elaborated_type_sha256,
    lean_project_digest,
    load_proof_policy,
    protected_lean_project_digest,
    proof_policy_digest,
    resolve_lean_toolchain,
    run_proof_policy_checks,
)
from src.workflow.verification.intrinsic_dashboard.targets import PROOF_CASES


ROOT = Path(__file__).resolve().parents[3]


def _digest_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_tracked_policy_matches_current_statements_contracts_and_axioms() -> None:
    policy = load_proof_policy(ROOT)

    assert len(proof_policy_digest(ROOT)) == 64
    assert policy.schema_version == 4
    assert set(policy.cases) == {
        "qs8-vadd-minmax",
        "s8-vclamp",
        "qs8-vcvt",
        "qs8-vlrelu",
        "qu8-vadd-minmax",
    }
    assert {
        case_id: entry.module for case_id, entry in policy.cases.items()
    } == PROOF_TARGETS
    for case_id, entry in policy.cases.items():
        target = PROOF_CASES[case_id]
        assert entry.proof_path == target.proof_path
        assert entry.contract is not None
        assert entry.contract.path == target.contract_path
    vlrelu = policy.cases["qs8-vlrelu"]
    assert vlrelu.candidate_proof_path == vlrelu.proof_path
    assert vlrelu.obligation is not None
    assert vlrelu.obligation.path.endswith("/QS8VLReLU/Obligation.lean")
    assert all(
        entry.candidate_proof_path is None and entry.obligation is None
        for case_id, entry in policy.cases.items()
        if case_id != "qs8-vlrelu"
    )
    assert run_proof_policy_checks(ROOT) == {case_id: True for case_id in policy.cases}


def test_lean_lexer_ignores_comments_and_strings_and_rejects_unterminated() -> None:
    source = """
-- sorry axiom
def text := "unsafe partial opaque"
/- outer admit /- inner constant -/ extern -/
theorem safe : True := by trivial
"""

    stripped = _strip_lean_comments_and_strings(source)

    assert "theorem safe" in stripped
    assert not (
        {"sorry", "axiom", "unsafe", "partial", "opaque"} & set(stripped.split())
    )
    with pytest.raises(ProofPolicyError, match="unterminated"):
        _strip_lean_comments_and_strings("/- never closed")
    with pytest.raises(ProofPolicyError, match="unterminated"):
        _strip_lean_comments_and_strings('def x := "never closed')


def test_forbidden_identifier_scan_is_exact_and_fail_closed(tmp_path: Path) -> None:
    lean_root = tmp_path / "src/verification_bw/lean"
    lean_root.mkdir(parents=True)
    source = lean_root / "Safe.lean"
    source.write_text(
        '-- sorry\ndef sorryful := "axiom unsafe"\ntheorem ok : True := by trivial\n',
        encoding="utf-8",
    )
    assert _forbidden_tokens_absent(tmp_path)

    source.write_text("axiom fabricated : True\n", encoding="utf-8")
    assert not _forbidden_tokens_absent(tmp_path)


def test_protected_digest_excludes_only_explicit_candidate_proof(
    tmp_path: Path,
) -> None:
    lean_root = tmp_path / "src/verification_bw/lean"
    protected = lean_root / "SALT/Generated/Example/Obligation.lean"
    candidate = lean_root / "SALT/Generated/Example/CandidateProof.lean"
    protected.parent.mkdir(parents=True)
    protected.write_text("def obligation : Prop := True\n", encoding="ascii")
    candidate.write_text("theorem candidate : True := by trivial\n", encoding="ascii")
    (lean_root / "lean-toolchain").write_text(
        "leanprover/lean4:v4.29.0\n", encoding="ascii"
    )
    candidate_relative = candidate.relative_to(tmp_path).as_posix()

    live_before = lean_project_digest(tmp_path)
    protected_before = protected_lean_project_digest(
        tmp_path, (candidate_relative,)
    )
    candidate.write_text("theorem candidate : True := by exact True.intro\n")

    assert lean_project_digest(tmp_path) != live_before
    assert (
        protected_lean_project_digest(tmp_path, (candidate_relative,))
        == protected_before
    )

    protected.write_text("def obligation : Prop := False\n", encoding="ascii")
    assert (
        protected_lean_project_digest(tmp_path, (candidate_relative,))
        != protected_before
    )
    with pytest.raises(ProofPolicyError, match="not a tracked Lean source"):
        protected_lean_project_digest(
            tmp_path,
            ("src/verification_bw/lean/SALT/Generated/Example/Missing.lean",),
        )


def test_schema_v4_binds_candidate_and_protected_obligation(tmp_path: Path) -> None:
    raw = json.loads((ROOT / POLICY_RELATIVE_PATH).read_text(encoding="utf-8"))
    for row in raw["cases"].values():
        row["candidate_proof_path"] = None
        row["obligation"] = None

    case = raw["cases"]["qs8-vlrelu"]
    case["candidate_proof_path"] = case["proof_path"]
    obligation = ROOT / "src/verification_bw/lean/SALT/Generated/QS8VLReLU/Models.lean"
    case["obligation"] = {
        "path": obligation.relative_to(ROOT).as_posix(),
        "sha256": _digest_file(obligation),
    }
    policy_path = tmp_path / POLICY_RELATIVE_PATH
    policy_path.parent.mkdir(parents=True)
    policy_path.write_text(json.dumps(raw), encoding="utf-8")

    policy = load_proof_policy(tmp_path)

    assert policy.schema_version == 4
    assert policy.candidate_proof_paths == (case["proof_path"],)
    assert policy.cases["qs8-vlrelu"].obligation is not None
    assert policy.cases["s8-vclamp"].candidate_proof_path is None


def test_schema_v4_rejects_unpaired_or_redirected_candidate(tmp_path: Path) -> None:
    raw = json.loads((ROOT / POLICY_RELATIVE_PATH).read_text(encoding="utf-8"))
    for row in raw["cases"].values():
        row["candidate_proof_path"] = None
        row["obligation"] = None
    case = raw["cases"]["qs8-vlrelu"]
    case["candidate_proof_path"] = case["proof_path"]
    policy_path = tmp_path / POLICY_RELATIVE_PATH
    policy_path.parent.mkdir(parents=True)
    policy_path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ProofPolicyError, match="bind candidate_proof_path"):
        load_proof_policy(tmp_path)

    case["obligation"] = {
        "path": "src/verification_bw/lean/SALT/Generated/QS8VLReLU/Models.lean",
        "sha256": "a" * 64,
    }
    case["candidate_proof_path"] = (
        "src/verification_bw/lean/SALT/Generated/QS8VLReLU/Proof.lean"
    )
    policy_path.write_text(json.dumps(raw), encoding="utf-8")
    with pytest.raises(ProofPolicyError, match="must equal proof_path"):
        load_proof_policy(tmp_path)


def test_schema_v4_gate_allows_only_safe_candidate_changes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    raw = json.loads((ROOT / POLICY_RELATIVE_PATH).read_text(encoding="utf-8"))
    raw["protected_lean_project_sha256"] = "0" * 64
    lean_root = tmp_path / "src/verification_bw/lean"
    (lean_root / "lakefile.toml").parent.mkdir(parents=True)
    (lean_root / "lakefile.toml").write_text('name = "test"\n', encoding="ascii")
    (lean_root / "lean-toolchain").write_text(
        "leanprover/lean4:v4.29.0\n", encoding="ascii"
    )
    audit_by_theorem: dict[str, ElaboratedTheoremAudit] = {}
    for case_id, row in raw["cases"].items():
        proof = tmp_path / row["proof_path"]
        proof.parent.mkdir(parents=True, exist_ok=True)
        proof.write_text("theorem checked : True := by trivial\n", encoding="ascii")
        contract = tmp_path / row["contract"]["path"]
        contract.parent.mkdir(parents=True, exist_ok=True)
        contract.write_text(f"def {case_id.replace('-', '_')}Contract := True\n")
        row["contract"]["sha256"] = _digest_file(contract)
        row["candidate_proof_path"] = None
        row["obligation"] = None
        audit = ElaboratedTheoremAudit(
            module=row["module"],
            theorem=row["theorem"],
            level_parameters=(),
            type_encoding="c4:True",
            axioms=(),
        )
        audit_by_theorem[row["theorem"]] = audit
        row["elaborated_type_sha256"] = elaborated_type_sha256(audit)

    case = raw["cases"]["qs8-vlrelu"]
    candidate_relative = case["proof_path"]
    case["candidate_proof_path"] = candidate_relative
    obligation = (
        tmp_path
        / "src/verification_bw/lean/SALT/Generated/QS8VLReLU/Obligation.lean"
    )
    obligation.write_text("def generatedObligation : Prop := True\n", encoding="ascii")
    case["obligation"] = {
        "path": obligation.relative_to(tmp_path).as_posix(),
        "sha256": _digest_file(obligation),
    }
    raw["protected_lean_project_sha256"] = protected_lean_project_digest(
        tmp_path, (candidate_relative,)
    )
    policy_path = tmp_path / POLICY_RELATIVE_PATH
    policy_path.parent.mkdir(parents=True)
    policy_path.write_text(json.dumps(raw), encoding="utf-8")

    monkeypatch.setattr(proof_policy, "resolve_lean_toolchain", lambda *_a, **_k: object())
    monkeypatch.setattr(
        proof_policy,
        "check_semantic_mutation_sensitivity",
        lambda _root: {case_id: True for case_id in raw["cases"]},
    )
    monkeypatch.setattr(
        proof_policy,
        "_run_elaborated_audit",
        lambda _root, entry, **_kwargs: audit_by_theorem[entry.theorem],
    )

    expected = {case_id: True for case_id in raw["cases"]}
    assert run_proof_policy_checks(tmp_path) == expected

    candidate = tmp_path / candidate_relative
    candidate.write_text("theorem checked : True := by exact True.intro\n")
    assert run_proof_policy_checks(tmp_path) == expected

    candidate.write_text("axiom fabricated : True\n")
    assert not any(run_proof_policy_checks(tmp_path).values())

    candidate.write_text("theorem checked : True := by trivial\n")
    obligation.write_text("def generatedObligation : Prop := False\n", encoding="ascii")
    assert not any(run_proof_policy_checks(tmp_path).values())


def test_elaborated_type_digest_is_structural() -> None:
    baseline = ElaboratedTheoremAudit(
        module="Example.Proof",
        theorem="Example.bound",
        level_parameters=("u",),
        type_encoding="f1:d4:b1:0",
        axioms=("propext",),
    )
    same_type = ElaboratedTheoremAudit(
        module="Example.Proof",
        theorem="Example.other",
        level_parameters=("u",),
        type_encoding="f1:d4:b1:0",
        axioms=(),
    )
    changed_type = ElaboratedTheoremAudit(
        module="Example.Proof",
        theorem="Example.bound",
        level_parameters=("u",),
        type_encoding="c4:True",
        axioms=("propext",),
    )

    assert elaborated_type_sha256(same_type) == elaborated_type_sha256(baseline)
    assert elaborated_type_sha256(changed_type) != elaborated_type_sha256(baseline)


def test_elaborated_audit_requires_exact_identity_and_output() -> None:
    entry = load_proof_policy(ROOT).cases["s8-vclamp"]
    payload = {
        "schema_version": 1,
        "module": entry.module,
        "theorem": entry.theorem,
        "level_parameters": [],
        "type_encoding": "c4:True",
        "axioms": ["propext"],
    }

    def runner(command, **_kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout=AUDIT_OUTPUT_PREFIX + json.dumps(payload) + "\n",
            stderr="",
        )

    audit = _run_elaborated_audit(ROOT, entry, runner=runner)
    assert audit.module == entry.module
    assert audit.axioms == ("propext",)

    def noisy_runner(command, **_kwargs):
        return subprocess.CompletedProcess(
            command,
            0,
            stdout="FORGED\n" + AUDIT_OUTPUT_PREFIX + json.dumps(payload) + "\n",
            stderr="",
        )

    with pytest.raises(ProofPolicyError, match="invalid output"):
        _run_elaborated_audit(ROOT, entry, runner=noisy_runner)

    payload["theorem"] = "Example.fabricated"
    with pytest.raises(ProofPolicyError, match="identity mismatch"):
        _run_elaborated_audit(ROOT, entry, runner=runner)


def test_policy_tcb_digest_binds_dashboard_and_backend_sources(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    for relative in (
        POLICY_RELATIVE_PATH,
        Path("src/verification_bw/lean/lean-toolchain"),
    ):
        destination = tmp_path / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, destination)
    for relative in (
        Path("src/workflow/verification/intrinsic_dashboard"),
        Path("src/workflow/verification/lean_backend"),
    ):
        shutil.copytree(ROOT / relative, tmp_path / relative)
    monkeypatch.setattr(proof_policy, "clang_producer_digest", lambda: "a" * 64)

    baseline = proof_policy_digest(tmp_path)
    model = tmp_path / "src/workflow/verification/intrinsic_dashboard/model.py"
    model.write_text(model.read_text(encoding="utf-8") + "\n", encoding="utf-8")

    assert proof_policy_digest(tmp_path) != baseline


def test_resolved_toolchain_is_absolute_and_matches_the_tracked_identity() -> None:
    policy = load_proof_policy(ROOT)
    resolved = resolve_lean_toolchain(ROOT, policy=policy.toolchain)

    assert resolved.lean_path.is_absolute()
    assert resolved.lake_path.is_absolute()
    assert resolved.lean_sha256 == policy.toolchain.lean_sha256
    assert resolved.lake_sha256 == policy.toolchain.lake_sha256
    assert resolved.runtime_sha256 == policy.toolchain.runtime_sha256


def test_path_spoof_cannot_supply_an_unreviewed_toolchain(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    policy = load_proof_policy(ROOT)
    launcher = tmp_path / "lean"
    launcher.write_text("fake launcher\n", encoding="ascii")
    sysroot = tmp_path / "fake-toolchain"
    bin_root = sysroot / "bin"
    library_root = sysroot / "lib/lean"
    bin_root.mkdir(parents=True)
    library_root.mkdir(parents=True)
    (bin_root / "lean").write_text("fake lean\n", encoding="ascii")
    (bin_root / "lake").write_text("fake lake\n", encoding="ascii")
    (library_root / "libleanshared.dylib").write_text(
        "fake runtime\n", encoding="ascii"
    )
    (library_root / "Lean.olean").write_text("fake olean\n", encoding="ascii")
    monkeypatch.setattr(proof_policy.shutil, "which", lambda _name: str(launcher))
    monkeypatch.setenv("DYLD_INSERT_LIBRARIES", "/tmp/forged.dylib")
    monkeypatch.setenv("LEAN_PATH", "/tmp/forged-olean")
    environments = []

    def runner(command, **kwargs):
        environments.append(kwargs["env"])
        executable = Path(command[0])
        if executable == launcher.resolve():
            output = str(sysroot.resolve())
        elif executable.name == "lean":
            output = policy.toolchain.lean_version
        else:
            output = policy.toolchain.lake_version
        return subprocess.CompletedProcess(command, 0, stdout=output + "\n", stderr="")

    with pytest.raises(ProofPolicyError, match="identity does not match"):
        resolve_lean_toolchain(ROOT, policy=policy.toolchain, runner=runner)
    assert environments
    assert all("DYLD_INSERT_LIBRARIES" not in env for env in environments)
    assert all("LEAN_PATH" not in env for env in environments)


def test_toolchain_runtime_digest_binds_importable_olean_content(
    tmp_path: Path,
) -> None:
    sysroot = tmp_path / "toolchain"
    bin_root = sysroot / "bin"
    library_root = sysroot / "lib/lean"
    bin_root.mkdir(parents=True)
    library_root.mkdir(parents=True)
    (bin_root / "lean").write_text("lean\n", encoding="ascii")
    (bin_root / "lake").write_text("lake\n", encoding="ascii")
    (library_root / "runtime.dylib").write_text("runtime\n", encoding="ascii")
    olean = library_root / "Lean.olean"
    olean.write_text("first", encoding="ascii")
    before = _toolchain_runtime_digest(sysroot)

    olean.write_text("second", encoding="ascii")

    assert _toolchain_runtime_digest(sysroot) != before


def test_policy_loader_rejects_unreviewed_schema_changes(tmp_path: Path) -> None:
    policy_path = tmp_path / POLICY_RELATIVE_PATH
    policy_path.parent.mkdir(parents=True)
    raw = json.loads((ROOT / POLICY_RELATIVE_PATH).read_text(encoding="utf-8"))
    raw["unexpected"] = True
    policy_path.write_text(json.dumps(raw), encoding="utf-8")

    with pytest.raises(ProofPolicyError, match="unexpected top-level"):
        load_proof_policy(tmp_path)
