"""Harness-generation fixes: binding clamp profiles, RVV redeclarations, packw holes."""
from pathlib import Path
import re

import pytest

from src.workflow.verification.engine.emit import (
    _binding_clamp, _strip_kernel_redeclarations, generate_harness,
)

ROOT = Path(__file__).resolve().parents[1]


def harness(name, **kw):
    return generate_harness(str(ROOT / "kernels/source" / f"{name}.c"),
                            str(ROOT / "kernels/target" / f"{name}.c"), name, **kw)


def clamp_pairs(src):
    names = re.findall(r'case \d+: return "([^"]*)";', src)
    pairs = []
    for n in names:
        lo = re.search(r"(?:^|,)(?:output_)?min=(-?\d+)", n)
        hi = re.search(r"(?:^|,)(?:output_)?max=(-?\d+)", n)
        if lo and hi:
            pairs.append((int(lo.group(1)), int(hi.group(1))))
    return pairs


@pytest.mark.parametrize("name, lo, hi", [
    ("qu8-vadd-minmax", 0, 255),
    ("qs8-vadd-minmax", -128, 127),
    ("s8-vclamp", -128, 127),
])
def test_integer_clamp_profiles_are_valid_and_bind(name, lo, hi):
    pairs = clamp_pairs(harness(name, params_mode="concrete"))
    assert pairs, "no clamp configs generated"
    assert all(lo <= a <= b <= hi for a, b in pairs)
    assert (lo, hi) in pairs                       # identity clamp as the base
    assert any((a, b) != (lo, hi) for a, b in pairs)   # and clamps that bind
    assert (128, 127) not in pairs                 # old signed defaults on uint8 fields


def test_finite_band_narrows_wide_float_clamp():
    wide = {"scalar.min": "-1e30f", "scalar.max": "1e30f"}
    assert _binding_clamp(wide, None) == wide
    assert _binding_clamp(wide, (-1000.0, 1000.0)) == {"scalar.min": "-500.0f", "scalar.max": "500.0f"}
    conv = harness("f32-conv-hwc2chw", params_mode="concrete", input_range=(-1000.0, 1000.0))
    assert "params.scalar.min = -500.0f;" in conv and "params.scalar.max = 500.0f;" in conv


def test_rvv_redeclarations_are_stripped():
    src = (
        '#include "xnnpack/math.h"  // for `round_up_po2`\n'
        "struct xnn_f32_default_params;\n"
        "struct xnn_f32_minmax_params {\n"
        "  struct {\n"
        "    float min;\n"
        "    float max;\n"
        "  } scalar;\n"
        "};\n"
        "void test_rvv(size_t n, const struct xnn_f32_minmax_params* params) {\n"
        "  const struct xnn_f32_default_params* unused = 0;\n"
        "}\n")
    out = _strip_kernel_redeclarations(src)
    assert "xnnpack/math.h" not in out
    assert not re.search(r"^struct xnn_", out, flags=re.M)
    assert "void test_rvv(size_t n, const struct xnn_f32_minmax_params* params) {" in out
    assert "const struct xnn_f32_default_params* unused = 0;" in out


def test_packw_compares_only_elements_the_reference_wrote():
    src = harness("x32-packw-gemm-goi", params_mode="concrete")
    assert "_packed_weights_init.push_back(_b_packed_weights_neon.getByte(_i));" in src
    assert "buffers_equal_written(ctx.tm, _b_packed_weights_neon, _b_packed_weights_rvv" in src
    assert "ref_element_untouched(_b_packed_weights_neon, _packed_weights_init" in src
