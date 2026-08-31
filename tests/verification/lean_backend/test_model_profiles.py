from __future__ import annotations

import pytest

from workflow.verification.lean_backend.case_emit import _function_header
from workflow.verification.lean_backend.model_profiles import (
    BinaryPrefixTailObligationProfile,
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


@pytest.mark.parametrize(
    ("load_lanes", "store_widths"),
    ((4, (2, 1)), (8, (4, 2, 1)), (16, (8, 4, 2, 1))),
)
def test_prefix_tail_accepts_complete_power_of_two_shapes(
    load_lanes: int, store_widths: tuple[int, ...]
) -> None:
    profile = PrefixTailProfile(
        element_c_type="uint32_t",
        load_lanes=load_lanes,
        store_widths=store_widths,
    )
    assert profile.store_widths == store_widths


def test_prefix_tail_rejects_incomplete_power_of_two_shape() -> None:
    with pytest.raises(ValueError, match="every non-full live length"):
        PrefixTailProfile(
            element_c_type="int8_t",
            load_lanes=16,
            store_widths=(8, 4, 2),
        )


def test_block_header_keeps_input_and_output_widths_distinct() -> None:
    profile = ModelProfile(
        case_id="example",
        lean_namespace="Example.Generated",
        parameter_type="Params",
        parameter_fields=(),
        rvv_scalar_types=(),
        inputs=("input",),
        neon_block_lanes=4,
        neon_loop_condition="batch >= 4",
        neon_loop_update="batch -= 4",
        input_width=32,
        output_width=16,
    )

    assert _function_header("block", profile) == [
        "def block (p : Params)",
        "    (input : List (BitVec 32)) : List (BitVec 16) :=",
    ]


@pytest.mark.parametrize(("field", "width"), (("input_width", 64), ("output_width", 1)))
def test_model_rejects_unsupported_stream_width(field: str, width: int) -> None:
    arguments = {field: width}
    with pytest.raises(ValueError, match="must be 8, 16, or 32 bits"):
        ModelProfile(
            case_id="example",
            lean_namespace="Example.Generated",
            parameter_type="Params",
            parameter_fields=(),
            rvv_scalar_types=(),
            inputs=("input",),
            neon_block_lanes=4,
            neon_loop_condition="batch >= 4",
            neon_loop_update="batch -= 4",
            **arguments,
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


def test_prefix_tail_requires_the_fixed_block_width() -> None:
    with pytest.raises(ValueError, match="must match the fixed Neon block width"):
        ModelProfile(
            case_id="example",
            lean_namespace="Example.Generated",
            parameter_type="Params",
            parameter_fields=(),
            rvv_scalar_types=(),
            inputs=("input",),
            neon_block_lanes=16,
            neon_loop_condition="batch >= 16",
            neon_loop_update="batch -= 16",
            prefix_tail=PrefixTailProfile(
                element_c_type="uint8_t",
                load_lanes=8,
                store_widths=(4, 2, 1),
            ),
        )


def test_binary_obligation_requires_exactly_two_inputs() -> None:
    obligation = BinaryPrefixTailObligationProfile(
        contract_module="Example.Contract",
        contract_namespace="Example",
        contract_predicate="WellFormed",
        claim_name="claim",
        display_name="example",
        element_width=8,
    )
    with pytest.raises(ValueError, match="needs exactly two inputs"):
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
            prefix_tail=PrefixTailProfile("uint8_t", 8, (4, 2, 1)),
            binary_prefix_tail_obligation=obligation,
        )


def test_model_rejects_both_obligation_arities() -> None:
    unary = UnaryPrefixTailObligationProfile(
        "Example.Contract", "Example", "WellFormed", "unaryClaim", "unary", 8
    )
    binary = BinaryPrefixTailObligationProfile(
        "Example.Contract", "Example", "WellFormed", "binaryClaim", "binary", 8
    )
    with pytest.raises(ValueError, match="cannot configure unary and binary"):
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
            prefix_tail=PrefixTailProfile("uint8_t", 8, (4, 2, 1)),
            unary_prefix_tail_obligation=unary,
            binary_prefix_tail_obligation=binary,
        )
