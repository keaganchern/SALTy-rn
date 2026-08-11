from workflow.verification.param_configs import get_param_ranges


def test_qs8_vcvt_uses_pinned_xnnpack_parameter_domain() -> None:
    assert get_param_ranges("qs8-vcvt") == {
        "input_zero_point": (-128, 127),
        "multiplier": (1, 32768),
        "output_zero_point": (-128, 127),
    }
