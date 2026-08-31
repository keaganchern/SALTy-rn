from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

from workflow.verification.lean_backend.case_emit import CaseEmissionError
from workflow.verification.lean_backend.generate_s8_vmax_example import (
    _main,
    emit_s8_vmax_example,
    generate_s8_vmax_example,
)


ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(
    shutil.which("clang") is None, reason="system clang required"
)


def test_example_generation_is_deterministic_and_uses_both_intrinsic_models():
    first = generate_s8_vmax_example(repository_root=ROOT)
    second = generate_s8_vmax_example(repository_root=ROOT)

    assert first == second
    assert "List.replicate 16" in first
    assert "SALT.Intrinsics.Neon.vmaxq_s8" in first
    assert "SALT.Intrinsics.RVV.vmax_vx" in first


def test_example_cli_check_accepts_checked_in_model():
    assert _main(["--repository-root", str(ROOT), "--check"]) == 0


def test_example_consumes_every_selected_call():
    result = emit_s8_vmax_example(repository_root=ROOT)
    assert len(result.neon_consumed_calls) == 4
    assert len(result.rvv_consumed_calls) == 4


def test_changed_neon_pointer_stride_is_rejected(tmp_path: Path):
    source = (ROOT / "examples/s8-vmax-to-lean/neon.c").read_text(encoding="ascii")
    mutated = tmp_path / "neon.c"
    mutated.write_text(source.replace("input += 16", "input += 8", 1), encoding="ascii")

    with pytest.raises(CaseEmissionError, match="pointer/count updates changed"):
        emit_s8_vmax_example(repository_root=ROOT, neon_source=mutated)


def test_extra_top_level_neon_control_is_rejected(tmp_path: Path):
    source = (ROOT / "examples/s8-vmax-to-lean/neon.c").read_text(encoding="ascii")
    marker = "\n}\n"
    injected = """
  if (batch >= 0) {
    output -= 16;
    int8x16_t extra = vdupq_n_s8(0);
    vst1q_s8(output, extra);
  }
}
"""
    assert source.endswith(marker)
    mutated = tmp_path / "neon.c"
    mutated.write_text(source[: -len(marker)] + "\n" + injected, encoding="ascii")

    with pytest.raises(CaseEmissionError, match="Neon control shape changed"):
        emit_s8_vmax_example(repository_root=ROOT, neon_source=mutated)


def test_supported_neon_semantic_mutation_changes_model(tmp_path: Path):
    original = generate_s8_vmax_example(repository_root=ROOT)
    source = (ROOT / "examples/s8-vmax-to-lean/neon.c").read_text(encoding="ascii")
    mutated = tmp_path / "neon.c"
    mutated.write_text(source.replace("vmaxq_s8", "vminq_s8", 1), encoding="ascii")

    changed = emit_s8_vmax_example(
        repository_root=ROOT, neon_source=mutated
    ).emitted.module_text
    assert changed != original
    assert "SALT.Intrinsics.Neon.vminq_s8" in changed


@pytest.mark.skipif(shutil.which("lake") is None, reason="Lean Lake required")
def test_example_lean_audit_checks_statement_and_mutation_witness():
    lean_root = ROOT / "src/verification_bw/lean"
    build = subprocess.run(
        [
            "lake",
            "--rehash",
            "--no-cache",
            "build",
            "SALT.Example.S8VMax.Audit",
        ],
        cwd=lean_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert build.returncode == 0, build.stdout + build.stderr

    check = subprocess.run(
        [
            "lake",
            "env",
            "lean",
            "--trust=0",
            "SALT/Example/S8VMax/Audit.lean",
        ],
        cwd=lean_root,
        check=False,
        capture_output=True,
        text=True,
        timeout=120,
    )
    assert check.returncode == 0, check.stdout + check.stderr
