"""Fixture routing, symbolic activation reads, and nonvacuous solver checks."""
from pathlib import Path
import subprocess

import pytest

from src.workflow.verification.engine.emit import (
    _gen_configs, _match_fixture, _neon_void_load_adapters, _rewrite_scalar_broadcast,
    generate_harness, generate_multidim,
)
from src.workflow.verification.engine.frontend import parse_signature
from src.workflow.verification.orchestrator import compile_harness, run_verification

ROOT = Path(__file__).resolve().parents[1]
KERNELS = (
    "qd8-f32-qc8w-gemm-minmax",
    "qd8-f32-qc8w-igemm-minmax",
    "qs8-qc8w-gemm-minmax-fp32",
)
HAS_CVC5 = (ROOT / "third_party/cvc5/install/include/cvc5/cvc5.h").exists()


def fixture(name):
    path = ROOT / "kernels/source" / f"{name}.c"
    sig = parse_signature(str(path), "test_neon")
    return path, sig, _match_fixture(sig, path.read_text())


@pytest.mark.parametrize("name", KERNELS)
def test_quantized_dispatch_has_byte_weights_and_tail_tiles(name):
    _, _, spec = fixture(name)
    assert spec.elem == "int8_t"
    assert max(spec.dims["nc"]) > 8
    assert {1, 7, 8, 9} <= set(spec.dims["kc"])
    assert spec.params[0] != "xnn_f32_qc4w_minmax_params"
    assert "ks_count" in spec.dims if "igemm" in name else "a_stride" in spec.strides
    if "igemm" in name:
        assert set(spec.dims["zero_mode"]) == {0, 1, 2}
        assert spec.strides["ks"] == "ks_count * sizeof(void*)"
        assert "zero_data" in spec.extents


def test_qc4w_and_float_fixtures_remain_distinct():
    _, _, qc4 = fixture("qd8-f32-qc4w-gemm-minmax")
    _, _, f32 = fixture("f32-gemm-minmax")
    _, _, ig = fixture("f32-igemm-minmax")
    assert qc4.params[0] == "xnn_f32_qc4w_minmax_params"
    assert f32.elem == ig.elem == "float"
    assert "zero_data" not in ig.extents


def test_u8_clamp_profiles_are_valid_and_include_nonconstant_clamps():
    paths, profiles = _gen_configs([], struct_name="xnn_u8_minmax_params")
    assert paths == ["scalar.min", "scalar.max"]
    pairs = [(int(lo), int(hi)) for lo, hi in profiles]
    assert all(0 <= lo <= hi <= 255 for lo, hi in pairs)
    assert {(0, 255), (64, 192), (127, 128), (255, 255)} <= set(pairs)


def test_scalar_postincrement_keeps_pointer_declaration_and_signed_cast():
    src = """void test_rvv(const int8_t* a) {
  const int8_t* restrict a0 = a;
  const int16_t x = (int16_t) *a0++;
  const int16_t y = (int16_t) *a0;
}"""
    code = _rewrite_scalar_broadcast(src, ["a0"])
    assert "const int8_t* restrict a0 = a;" in code
    assert "const auto x = salt_scalar(a0++).cast<int16_t>();" in code
    assert "const auto y = salt_scalar(a0).cast<int16_t>();" in code


@pytest.mark.parametrize("options,message", [
    ({"params_mode": "symbolic"}, "three concrete"),
    ({"params_mode": "concrete", "input_range": (-1, 1)}, "packed FP"),
])
def test_qc8w_does_not_silently_ignore_requested_domain(tmp_path, options, message):
    source, _, _ = fixture(KERNELS[0])
    candidate = tmp_path / "control.c"
    candidate.write_text(source.read_text().replace("test_neon", "test_rvv"))
    with pytest.raises(NotImplementedError, match=message):
        generate_harness(str(source), str(candidate), KERNELS[0], **options)


@pytest.mark.skipif(not HAS_CVC5, reason="cvc5 C++ installation required")
@pytest.mark.parametrize("name", KERNELS)
@pytest.mark.parametrize("mutant", [False, True])
def test_solver_accepts_reference_and_rejects_missing_store(tmp_path, name, mutant):
    # Use the reference as a control, not the candidate under investigation.
    # This isolates fixture validity from the quality of any LLM translation.
    path, sig, spec = fixture(name)
    code = path.read_text().replace("test_neon", "test_rvv")
    if mutant:
        # Remove the final lane write for nc=1. Independent output poison must
        # make this satisfiable, even with all the fixture's constraints active.
        code = code.replace("vst1_lane_f32(c0, vout0x01, 0);", "")
        code = code.replace("vst1_lane_s8(c0, vout0x01234567, 0);", "")
    candidate = tmp_path / "control.c"
    candidate.write_text(_neon_void_load_adapters(code) + "\n" + code)
    spec.dims = {d: [values[0]] for d, values in spec.dims.items()}
    harness = generate_multidim(str(path), str(candidate), name, sig,
                               parse_signature(str(candidate), "test_rvv"), spec)
    binary, error = compile_harness(harness, "qc8w_control", tmp_path / "build", "cvc5")
    assert binary, error
    result = run_verification(binary, name, time_budget=15, vlen=128)
    assert result.verdict == ("COUNTEREXAMPLE" if mutant else "ALL_PASSED")
    assert len(result.verified_batches) == 1


@pytest.mark.skipif(not HAS_CVC5, reason="cvc5 C++ installation required")
@pytest.mark.parametrize("branch", ["zero_data", "a_offset"])
def test_igemm_addressing_mutations_are_detected(tmp_path, branch):
    name = "qd8-f32-qc8w-igemm-minmax"
    path, sig, spec = fixture(name)
    code = path.read_text().replace("test_neon", "test_rvv")
    if branch == "zero_data":
        code = code.replace("a0 = zero_data;", "a0 = zero;")
    else:
        code = code.replace("(uintptr_t) a0 + a_offset", "(uintptr_t) a0")
    candidate = tmp_path / "control.c"
    candidate.write_text(_neon_void_load_adapters(code) + "\n" + code)
    spec.dims = {d: [values[0]] for d, values in spec.dims.items()}
    spec.dims["a_offset"] = [3]
    spec.dims["zero_mode"] = [1 if branch == "zero_data" else 0]
    # Concrete unit weights isolate addressing from nonlinear FP solving.
    spec.raw_decls[:0] = [
        "    for (size_t i = 0; i < 8; ++i) {",
        "      _b_w.storeScalar(i * 4, ctx.tm.mkBitVector(32, 0), 32);",
        "      _b_w.storeScalar(32 + i, ctx.tm.mkBitVector(8, 1), 8);",
        "      _b_w.storeScalar(40 + i * 4, ctx.tm.mkBitVector(32, 0x3F800000), 32);",
        "      _b_w.storeScalar(72 + i * 4, ctx.tm.mkBitVector(32, 0), 32);",
        "    }",
    ]
    harness = generate_multidim(str(path), str(candidate), name, sig,
                               parse_signature(str(candidate), "test_rvv"), spec)
    binary, error = compile_harness(harness, "igemm_address", tmp_path / "build", "cvc5")
    assert binary, error
    result = run_verification(binary, name, time_budget=15, vlen=128)
    assert result.verdict == "COUNTEREXAMPLE"


@pytest.mark.skipif(not HAS_CVC5, reason="cvc5 C++ installation required")
def test_symbolic_widening_mac_matches_neon_full_domain(tmp_path):
    # Independent NEON lane and RVV scalar paths: signed 16-bit extrema and
    # 32-bit accumulator overflow are included in the unconstrained inputs.
    harness = r'''
#include "salt.hpp"
using namespace salt;
int main() {
    VerificationContext ctx(128); g_ctx = &ctx;
    int16_t x[1]{}, y[4]{}; int32_t acc[4]{};
    auto& bx = ctx.registerBuffer("x", sizeof(x)); bx.bind(x);
    auto& by = ctx.registerBuffer("y", sizeof(y)); by.bind(y);
    auto& ba = ctx.registerBuffer("acc", sizeof(acc)); ba.bind(acc);
    auto n = vmlal_lane_s16(vld1q_s32(acc), vld1_s16(y),
                            vdup_n_s16(SymbolicScalar<int16_t>(bx, 0)), 0);
    auto r = __riscv_vwmacc_vx_i32m2(__riscv_vle32_v_i32m2(acc, 4),
        SymbolicScalar<int16_t>(bx, 0), __riscv_vle16_v_i16m1(y, 4), 4);
    Term eq = ctx.tm.mkBoolean(true);
    for (size_t i = 0; i < 4; ++i)
        eq = ctx.land_(eq, ctx.tm.mkTerm(Kind::EQUAL, {n.getLane(i), r.getElement(i)}));
    ctx.assert_(ctx.lnot_(eq)); ctx.set_query_timeout_ms(10000);
    return ctx.check() == CheckResult::Unsat ? 0 : 1;
}
'''
    binary, error = compile_harness(harness, "scalar_mac", tmp_path / "build", "cvc5")
    assert binary, error
    assert subprocess.run([str(binary)], timeout=15, capture_output=True).returncode == 0
