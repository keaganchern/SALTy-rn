from workflow.verification.param_configs import PARAM_CONSTRAINTS, get_param_ranges


def test_qs8_vcvt_uses_pinned_xnnpack_parameter_domain() -> None:
    assert get_param_ranges("qs8-vcvt") == {
        "input_zero_point": (-128, 127),
        "multiplier": (1, 32768),
        "output_zero_point": (-128, 127),
    }


def test_qs8_vlrelu_uses_pinned_xnnpack_parameter_domain() -> None:
    assert get_param_ranges("qs8-vlrelu") == {
        "input_zero_point": (-128, 127),
        "output_zero_point": (-128, 127),
        "positive_multiplier": (1, 32768),
        "negative_multiplier": (-32767, 32768),
    }
    assert ("BV_NE", "negative_multiplier", 0) in PARAM_CONSTRAINTS[
        "xnn_qs8_lrelu_params"
    ]


def test_add_ranges_cover_pinned_xnnpack_multiplier_domain() -> None:
    for kernel_name in ("qs8-vadd-minmax", "qs8-vaddc", "qu8-vadd-minmax", "qu8-vaddc"):
        ranges = get_param_ranges(kernel_name)
        assert ranges["a_multiplier"] == (1, 2097152)
        assert ranges["b_multiplier"] == (1, 2097152)
        assert ranges["shift"] == (0, 31)
