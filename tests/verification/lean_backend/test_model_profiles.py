from __future__ import annotations

import pytest

from workflow.verification.lean_backend.model_profiles import (
    ModelProfile,
    PrefixTailProfile,
    UnaryPrefixTailObligationProfile,
)


def test_prefix_tail_rejects_non_power_of_two_load_width() -> None:
    with pytest.raises(ValueError, match="power-of-two load"):
        PrefixTailProfile(
            element_c_type="int8_t",
            load_lanes=7,
            store_widths=(4, 2),
        )


def test_prefix_tail_rejects_unimplemented_power_of_two_shape() -> None:
    with pytest.raises(ValueError, match="supports exactly"):
        PrefixTailProfile(
            element_c_type="int8_t",
            load_lanes=16,
            store_widths=(8, 4, 2, 1),
        )


def test_unary_obligation_requires_unary_prefix_tail_model() -> None:
    obligation = UnaryPrefixTailObligationProfile(
        contract_module="Example.Contract",
        contract_namespace="Example",
        contract_predicate="WellFormed",
        claim_name="claim",
        display_name="example",
        element_width=8,
    )
    with pytest.raises(ValueError, match="needs a tail profile"):
        ModelProfile(
            case_id="example",
            lean_namespace="Example.Generated",
            parameter_type="Params",
            parameter_fields=(),
            rvv_scalar_types=(),
            inputs=("input",),
            neon_block_lanes=8,
            neon_loop_condition="batch >= 8",
            neon_loop_update="batch -= 8",
            unary_prefix_tail_obligation=obligation,
        )
