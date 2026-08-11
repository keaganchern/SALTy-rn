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
