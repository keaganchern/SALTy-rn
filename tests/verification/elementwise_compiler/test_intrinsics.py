from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.intrinsics import (
    _implementation_digest,
    resolve_intrinsics,
)
from workflow.verification.lean_backend.frontend import parse_kernel_explicit
from workflow.verification.lean_backend.intrinsic_library import (
    ELEMENTWISE_SHARED_SPECS,
)
from workflow.verification.lean_backend.schema import Architecture


ROOT = Path(__file__).resolve().parents[3]
FACADE_ROOT = ROOT / "src/workflow/verification/lean_backend/facade"
pytestmark = pytest.mark.skipif(shutil.which("clang") is None, reason="system clang required")


def _pair(case: str):
    facade = FACADE_ROOT / f"{case.replace('-', '_')}.h"
    return (
        parse_kernel_explicit(
            ROOT / "kernels/source" / f"{case}.c",
            architecture=Architecture.NEON,
            function_name="test_neon",
            facade=facade,
            target_triple="aarch64-none-elf",
        ),
        parse_kernel_explicit(
            ROOT / "kernels/target" / f"{case}.c",
            architecture=Architecture.RVV,
            function_name="test_rvv",
            facade=facade,
            target_triple="riscv64-none-elf",
        ),
    )


@pytest.mark.parametrize(
    "case",
    (
        "qs8-vadd-minmax",
        "s8-vclamp",
        "qs8-vcvt",
        "qs8-vlrelu",
        "qu8-vadd-minmax",
    ),
)
def test_global_information_preserving_policy_resolves_existing_integer_pairs(
    case: str,
) -> None:
    resolved = resolve_intrinsics(*_pair(case), repository_root=ROOT)
    assert resolved.capabilities
    assert all("case" not in capability.capability_id for capability in resolved.capabilities)
    assert len(resolved.refs) == len(resolved.capabilities)


def test_global_policy_selects_full_vector_and_rounding_semantics() -> None:
    resolved = resolve_intrinsics(*_pair("qs8-vcvt"), repository_root=ROOT)
    semantic_symbols = {
        capability.spelling: capability.semantic_symbol
        for capability in resolved.capabilities
    }
    assert semantic_symbols["__riscv_vnclip_wx_i8m2"] == (
        "SALT.Intrinsics.RVV.vnclip_wx_i8_mode"
    )
    assert semantic_symbols["__riscv_vsll_vx_i32m8"] == (
        "SALT.Intrinsics.RVV.vsll_vx_i32"
    )

    clamp = resolve_intrinsics(*_pair("s8-vclamp"), repository_root=ROOT)
    clamp_symbols = {
        capability.spelling: capability.semantic_symbol
        for capability in clamp.capabilities
    }
    assert clamp_symbols["vmaxq_s8"] == "SALT.Intrinsics.Neon.vmaxq_s8"
    assert clamp_symbols["vmax_s8"] == "SALT.Intrinsics.Neon.vmax_s8_vec"


def test_structural_implementation_digest_binds_context_specific_lowering(
    tmp_path: Path,
) -> None:
    backend = tmp_path / "src/workflow/verification/lean_backend"
    backend.mkdir(parents=True)
    (backend / "emit_lean.py").write_text("generic\n", encoding="utf-8")
    case_emitter = backend / "case_emit.py"
    case_emitter.write_text("lane zero\n", encoding="utf-8")
    spec = next(
        item for item in ELEMENTWISE_SHARED_SPECS if item.spelling == "vst1_lane_f32"
    )

    before = _implementation_digest(tmp_path, spec)
    case_emitter.write_text("lane selected\n", encoding="utf-8")

    assert _implementation_digest(tmp_path, spec) != before
