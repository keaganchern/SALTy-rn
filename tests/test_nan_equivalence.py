"""NaN-equivalent FP outputs, ARM min/max semantics, and the external qd8 fixes."""
import math
import os
from pathlib import Path
import re
import subprocess

import pytest

from src.workflow.verification.engine.emit import _match_fixture, generate_multidim
from src.workflow.verification.engine.frontend import parse_signature
from src.workflow.verification.orchestrator import compile_harness, run_verification

ROOT = Path(__file__).resolve().parents[1]
TARGETS = Path(os.environ.get("SALT_QC8W_TARGET_DIR", ROOT.parent / "SALTcur/kernels/target"))
KERNELS = ("qd8-f32-qc8w-gemm-minmax", "qd8-f32-qc8w-igemm-minmax")
pytestmark = pytest.mark.skipif(
    not (ROOT / "third_party/cvc5/install/include/cvc5/cvc5.h").exists(),
    reason="cvc5 C++ installation required",
)


def target_path(name):
    path = TARGETS / f"{name}.c"
    if not path.exists():
        pytest.skip("Set SALT_QC8W_TARGET_DIR to the external RVV candidates")
    return path


def test_nan_equivalence_and_arm_minmax_model(tmp_path):
    # Concrete expected values are independent of the symbolic min/max model:
    # either NaN propagates on ARM; RVV returns the number if exactly one is NaN.
    harness = r'''
#include "salt.hpp"
#include <cmath>
using namespace salt;
int main() {
    uint32_t values[] = {0x7fc00001, 0xffc12345, 0x7f800001, 0xff800042,
        0x7f800000, 0xff800000, 0, 0x80000000, 1, 0x80000001,
        0x3f800000, 0xbf800000};
    auto is_nan = [](uint32_t b) { return (b & 0x7fffffff) > 0x7f800000; };
    for (uint32_t a : values) for (uint32_t b : values) {
        VerificationContext ctx(128); g_ctx = &ctx;
        auto& tm = ctx.tm;
        Term ok = tm.mkBoolean(true);
        auto require = [&](Term p) { ok = ctx.land_(ok, p); };
        auto abv = tm.mkBitVector(32, a), bbv = tm.mkBitVector(32, b);
        float af, bf; std::memcpy(&af, &a, 4); std::memcpy(&bf, &b, 4);
        bool equal = (is_nan(a) && is_nan(b)) || af == bf;
        require(tm.mkTerm(Kind::EQUAL, {
            element_equal(tm, abv, bbv, ElementKind::F32), tm.mkBoolean(equal)}));
        // ULP tolerance also must reject exactly one NaN.
        if (is_nan(a) || is_nan(b))
            require(tm.mkTerm(Kind::EQUAL, {
                element_equal(tm, abv, bbv, ElementKind::F32, 4),
                tm.mkBoolean(is_nan(a) && is_nan(b))}));
        float32x4_t na(tm, {abv, abv, abv, abv}), nb(tm, {bbv, bbv, bbv, bbv});
        RVVVector ra(tm, 32, {abv}), rb(tm, 32, {bbv});
        for (bool maximum : {false, true}) {
            float expected = maximum ? std::fmax(af, bf) : std::fmin(af, bf);
            uint32_t expected_bits; std::memcpy(&expected_bits, &expected, 4);
            if (is_nan(a) && is_nan(b)) expected_bits = 0x7fc00000;
            else if (is_nan(a)) expected_bits = b;
            else if (is_nan(b)) expected_bits = a;
            auto rv = maximum ? __riscv_vfmax_vv_f32m2(ra, rb, 1)
                              : __riscv_vfmin_vv_f32m2(ra, rb, 1);
            require(element_equal(tm, rv.getElement(0),
                tm.mkBitVector(32, expected_bits), ElementKind::F32));
            if (is_nan(a) || is_nan(b)) expected_bits = 0x7fc00000;
            auto nv = maximum ? vmaxq_f32(na, nb) : vminq_f32(na, nb);
            require(element_equal(tm, nv.getLane(0),
                tm.mkBitVector(32, expected_bits), ElementKind::F32));
        }
        ctx.set_query_timeout_ms(2000);
        if (ctx.check() != CheckResult::Sat) return 2; // reject a vacuous model
        ctx.assert_(ctx.lnot_(ok));
        if (ctx.check() != CheckResult::Unsat) {
            printf("min/max mismatch: %08x %08x\n", a, b);
            return 1;
        }
    }
    return 0;
}
'''
    binary, error = compile_harness(harness, "nan_model", tmp_path / "build", "cvc5")
    assert binary, error
    result = subprocess.run([str(binary)], capture_output=True, text=True, timeout=25)
    assert result.returncode == 0, result.stdout + result.stderr


def nan_fixture(name):
    source = ROOT / "kernels/source" / f"{name}.c"
    sig = parse_signature(str(source), "test_neon")
    spec = _match_fixture(sig, source.read_text())
    spec.dims = {d: [values[0]] for d, values in spec.dims.items()}
    spec.dims.update(nc=[1, 7, 8, 9, 17], nan_case=list(range(10)))
    spec.params = ("xnn_f32_minmax_params", {
        "scalar.min": '(nan_case == 3 || nan_case == 7) ? __builtin_nanf("1") : '
                      '(nan_case == 5 ? __builtin_nansf("1") : -1.0f)',
        "scalar.max": '(nan_case == 4 || nan_case == 7) ? -__builtin_nanf("2") : '
                      '(nan_case == 6 ? __builtin_nansf("2") : 1.0f)',
    })
    spec.extra_params["quantization_params"] = ("xnn_qd8_quantization_params", {
        "zero_point": "1",
        "inv_scale": 'nan_case == 2 ? 0x1.fffffep127f : '
                     '(nan_case == 9 ? __builtin_nanf("3") : 1.0f)',
    })
    # Replace the ordinary finite-FP constraints. No input assumptions here:
    # bias (case 0) or scale (case 1) has all 32-bit patterns, including NaNs.
    depth = "ks_count * kc" if "igemm" in name else "kc"
    spec.raw_decls = [
        "    {",
        f"      const size_t fp_off = 32 + 8 * ({depth}), tile = fp_off + 64;",
        "      const uint32_t mixed[] = {0xffc12345, 0x7f800001, 0x3f000000,",
        "          0x7f800000, 0xff800000, 0, 0x80000000, 1};",
        "      for (size_t t = 0; t < (nc + 7) / 8; ++t) {",
        "        for (size_t i = 0; i < 8; ++i) {",
        "          _b_w.storeScalar(t * tile + 4*i,",
        "              ctx.tm.mkBitVector(32, nan_case == 2 ? 2 : 0), 32);",
        "          if (nan_case != 1)",
        "            _b_w.storeScalar(t * tile + fp_off + 4*i,",
        "                ctx.tm.mkBitVector(32, nan_case == 2 ? 0 : 0x3f800000), 32);",
        "          if (nan_case != 0)",
        "            _b_w.storeScalar(t * tile + fp_off + 32 + 4*i,",
        "                ctx.tm.mkBitVector(32, nan_case == 8 ? mixed[i] : 0), 32);",
        "        }",
        "        for (size_t i = 32; i < fp_off; ++i)",
        "          _b_w.storeScalar(t * tile + i, ctx.tm.mkBitVector(8, 0), 8);",
        "      }",
        "    }",
    ]
    if "igemm" in name:
        spec.dims.update(ks_count=[3], a_offset=[3], zero_mode=[2])
        spec.raw_decls += [
            "    for (size_t i = 0; i < _a_rows; ++i)",
            "      if (i % 2 == 0) a_tbl[i] = zero_arr.data();",
        ]
    spec.config_tag = "qc8w_nan_equivalence"
    return source, sig, spec


@pytest.mark.parametrize("name", KERNELS)
@pytest.mark.parametrize("old_clamp", [True, False])
def test_qd8_nan_cases_accept_fix_and_reject_old_clamp(tmp_path, name, old_clamp):
    candidate = target_path(name)
    if old_clamp:
        code = candidate.read_text()
        code, count = re.subn(
            r"    // NEON min/max propagates NaNs\..*?(?=    __riscv_vse32)",
            "    vout = __riscv_vfmax_vf_f32m2(vout, params->scalar.min, vl);\n"
            "    vout = __riscv_vfmin_vf_f32m2(vout, params->scalar.max, vl);\n\n",
            code, flags=re.S,
        )
        assert count == 1
        candidate = tmp_path / "old_clamp.c"
        candidate.write_text(code)
    source, sig, spec = nan_fixture(name)
    harness = generate_multidim(str(source), str(candidate), name, sig,
                               parse_signature(str(candidate), "test_rvv"), spec)
    binary, error = compile_harness(harness, "nan_qd8", tmp_path / "build", "cvc5")
    assert binary, error
    for vlen in ([128] if old_clamp else [128, 256, 512]):
        result = run_verification(binary, name, time_budget=30, vlen=vlen)
        assert result.verdict == ("COUNTEREXAMPLE" if old_clamp else "ALL_PASSED"), result
        if not old_clamp:
            assert len(result.verified_batches) == math.prod(map(len, spec.dims.values()))


@pytest.mark.parametrize("name", KERNELS)
def test_qd8_finite_symbolic_tail_regression(tmp_path, name):
    candidate = target_path(name)
    source = ROOT / "kernels/source" / f"{name}.c"
    sig = parse_signature(str(source), "test_neon")
    spec = _match_fixture(sig, source.read_text())
    spec.dims = {d: [values[0]] for d, values in spec.dims.items()}
    spec.dims.update(param_case=[0, 1, 2], nc=[9], kc=[9])
    if "igemm" in name:
        spec.dims.update(ks_count=[3], a_offset=[3], zero_mode=[2])
    harness = generate_multidim(str(source), str(candidate), name, sig,
                               parse_signature(str(candidate), "test_rvv"), spec)
    binary, error = compile_harness(harness, "finite_qd8", tmp_path / "build", "cvc5")
    assert binary, error
    result = run_verification(binary, name, time_budget=60, vlen=128)
    assert result.verdict == "ALL_PASSED", result
    assert len(result.verified_batches) == 3
