"""Curated parameter data for the verification engine.

Everything the engine (src/workflow/verification/engine/emit.py) needs when it binds
a kernel's params struct:
  - EDGE_VALUES / FIELD_EDGES : concrete edge-case values per field (concrete-params mode)
  - PARAM_CONSTRAINTS         : validity asserts for symbolic params (min ≤ max, shift∈[0,31], …)
  - PARAM_RANGES              : per-field [lo,hi] bounds for symbolic-int params (narrows the solver)

This is the merge of the old `param_configs` + `kernel_profiles` modules. The legacy
config-generation / harness-prologue helpers and the full KernelProfile bodies that the
old Shape engine used are gone — only the data the engine actually reads remains.
"""

# ---------------------------------------------------------------------------
# Edge values per field type (concrete-params mode)
# ---------------------------------------------------------------------------
EDGE_VALUES = {
    "int8_t":       [-128, -1, 0, 1, 127],
    "uint8_t":      [0, 1, 127, 255],
    "int16_t":      [-128, -1, 0, 1, 127],      # stay in int8 range for sanity
    "uint16_t":     [0, 1, 255],
    "int32_t":      [-1, 0, 1, 127],
    "uint32_t":     [0, 1, 31],
    "float":        [0.0, 1.0, 0.5],
    "xnn_float16":  [0.0, 1.0, 0.5],            # constructor takes float
}

# ---------------------------------------------------------------------------
# Per-field semantic edge cases (override the generic type-based values)
# ---------------------------------------------------------------------------
FIELD_EDGES = {
    # Shift fields — 0 disables rounding, max meaningful is ~31
    "shift":         [0, 1, 4, 8, 15],
    "right_pre_shift":  [0, 1, 8],
    "right_post_shift": [0, 1, 8],

    # Multipliers — 1 is identity, test small and large
    "a_multiplier":  [1, 3, 127],
    "b_multiplier":  [1, 2, 64],
    "multiplier":    [1, 3, 127],
    "positive_multiplier": [1, 256, 32768],
    "negative_multiplier": [-32767, -1, 1, 32768],

    # Zero points — 0 is common, test nonzero
    "a_zero_point":      [0, 1, -5],
    "b_zero_point":      [0, 1, 5],
    "input_zero_point":  [0, 1, -10],
    "output_zero_point": [0, 5, -5],
    "zero_point":        [0, 1, -5],
    "kernel_zero_point": [0, 1, 128],

    # Output bounds
    "output_min": [-128],    # usually fixed at type min
    "output_max": [127],     # usually fixed at type max
    "min":        [-128],
    "max":        [127],

    # FP scales
    "scale":     [0.5, 1.0, 2.0],
    "inv_scale": [0.5, 1.0, 2.0],
    "prescale":  [1.0],
    "alpha":     [1.0],
    "beta":      [1.0],
    "slope":     [0.1, 0.5, 1.0],

    # Bias
    "bias": [0],

    # Magic bias (NEON-specific conversion trick)
    "magic_bias": [12582912.0],
    "magic_bias_less_output_zero_point": [0x4B400000],
    "magic_bias_less_zero_point":        [0x4B400000],

    # Rounding (RNDNU quantization)
    "rounding":  [0],

    # Padding (filler bytes, usually 0)
    "padding": [0],
}

# ---------------------------------------------------------------------------
# Validity constraints for symbolic params (op, field_name, field_name|const)
# ---------------------------------------------------------------------------
PARAM_CONSTRAINTS = {
    "xnn_qs8_add_minmax_params": [
        ("BV_SLE", "output_min", "output_max"),
        ("BV_SGE", "shift", 0),
        ("BV_SLE", "shift", 31),
        ("BV_SGT", "a_multiplier", 0),
        ("BV_SGT", "b_multiplier", 0),
    ],
    "xnn_qu8_add_minmax_params": [
        ("BV_ULE", "output_min", "output_max"),
        ("BV_SGE", "shift", 0),
        ("BV_SLE", "shift", 31),
        ("BV_SGT", "a_multiplier", 0),
        ("BV_SGT", "b_multiplier", 0),
    ],
    "xnn_qs8_mul_minmax_params": [
        ("BV_SLE", "output_min", "output_max"),
    ],
    "xnn_qs8_conv_minmax_params": [
        ("BV_SLE", "output_min", "output_max"),
    ],
    "xnn_qs8_qc8w_conv_minmax_params": [
        ("BV_SLE", "output_min", "output_max"),
    ],
    "xnn_qu8_conv_minmax_params": [
        ("BV_ULE", "output_min", "output_max"),
    ],
    "xnn_qs8_lrelu_params": [
        ("BV_SGT", "positive_multiplier", 0),
        ("BV_NE", "negative_multiplier", 0),
    ],
    "xnn_qs8_cvt_params": [
        ("BV_SGT", "multiplier", 0),
    ],
    "xnn_s8_minmax_params": [
        ("BV_SLE", "min", "max"),
    ],
    "xnn_u8_minmax_params": [
        ("BV_ULE", "min", "max"),
    ],
}

# ---------------------------------------------------------------------------
# Per-field [lo, hi] bounds for symbolic-int params (was KernelProfile.param_ranges).
# Restricts the solver to the valid domain for kernels proved with symbolic params.
# ---------------------------------------------------------------------------
PARAM_RANGES = {
    "qs8-vadd": {"a_zero_point": (-128, 127), "b_zero_point": (-128, 127),
                 "a_multiplier": (1, 65535), "b_multiplier": (1, 65535), "shift": (0, 31),
                 "output_zero_point": (-128, 127), "output_min": (-128, 127), "output_max": (-128, 127)},
    "qs8-vaddc": {"a_zero_point": (-128, 127), "b_zero_point": (-128, 127),
                  "a_multiplier": (1, 65535), "b_multiplier": (1, 65535), "shift": (0, 31),
                  "output_zero_point": (-128, 127), "output_min": (-128, 127), "output_max": (-128, 127)},
    "qs8-vmul": {"a_zero_point": (-128, 127), "b_zero_point": (-128, 127),
                 "output_zero_point": (-128, 127), "output_min": (-128, 127), "output_max": (-128, 127)},
    "qs8-vmulc": {"a_zero_point": (-128, 127), "b_zero_point": (-128, 127),
                  "output_zero_point": (-128, 127), "output_min": (-128, 127), "output_max": (-128, 127)},
    # XNNPACK@867d5a3 constructs these LReLU multipliers in [1, 32768] and
    # [-32767, 32768] \ {0}, respectively.
    "qs8-vlrelu": {"input_zero_point": (-128, 127), "output_zero_point": (-128, 127),
                   "positive_multiplier": (1, 32768),
                   "negative_multiplier": (-32767, 32768)},
    # XNNPACK@867d5a3 constructs this Q8 multiplier in [1, 32768].
    "qs8-vcvt": {"input_zero_point": (-128, 127), "multiplier": (1, 32768),
                 "output_zero_point": (-128, 127)},
    "qu8-vadd": {"a_zero_point": (0, 255), "b_zero_point": (0, 255),
                 "a_multiplier": (1, 65535), "b_multiplier": (1, 65535), "shift": (0, 31),
                 "output_zero_point": (0, 255), "output_min": (0, 255), "output_max": (0, 255)},
    "qu8-vaddc": {"a_zero_point": (0, 255), "b_zero_point": (0, 255),
                  "a_multiplier": (1, 65535), "b_multiplier": (1, 65535), "shift": (0, 31),
                  "output_zero_point": (0, 255), "output_min": (0, 255), "output_max": (0, 255)},
    "qu8-vmul": {"a_zero_point": (0, 255), "b_zero_point": (0, 255),
                 "output_zero_point": (0, 255), "output_min": (0, 255), "output_max": (0, 255)},
    "qu8-vmulc": {"a_zero_point": (0, 255), "b_zero_point": (0, 255),
                  "output_zero_point": (0, 255), "output_min": (0, 255), "output_max": (0, 255)},
    "qu8-vlrelu": {"input_zero_point": (0, 255), "output_zero_point": (0, 255),
                   "positive_multiplier": (1, 255), "negative_multiplier": (1, 255)},
    "qu8-vcvt": {"input_zero_point": (0, 255), "multiplier": (1, 65535),
                 "output_zero_point": (0, 255)},
}


def get_param_ranges(kernel_name: str) -> dict:
    """Per-field (lo, hi) bounds for a kernel's symbolic-int params, or {} if none.

    Longest-substring match (mirrors the old get_profile lookup): e.g. a name like
    'qs8-vaddc-rndnu' resolves to 'qs8-vaddc', and the longer 'qs8-vaddc' wins over
    a shorter 'qs8-vadd' substring.
    """
    best_key, best = "", {}
    for key, ranges in PARAM_RANGES.items():
        if key in kernel_name and len(key) > len(best_key):
            best_key, best = key, ranges
    return best
