"""Reviewed Lean block-model interfaces for the scale-up kernel set.

Profiles without a reviewed tail schema describe only the local block/chunk
theorem boundary.  A configured tail schema can drive a complete value-loop
model, but still does not establish C byte-memory behavior.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ParameterField:
    name: str
    width: int


@dataclass(frozen=True, slots=True)
class PrefixTailProfile:
    """Reviewed byte-tail grammar for one fixed-width Neon loop."""

    element_c_type: str
    load_lanes: int
    store_widths: tuple[int, ...]
    input_advances_after_load: bool = False

    def __post_init__(self) -> None:
        if self.load_lanes <= 1 or self.load_lanes & (self.load_lanes - 1):
            raise ValueError(
                "a prefix tail needs a power-of-two load wider than one lane"
            )
        if not self.store_widths:
            raise ValueError("a prefix tail needs at least one store width")
        if tuple(sorted(self.store_widths, reverse=True)) != self.store_widths:
            raise ValueError("prefix-tail store widths must be strictly descending")
        if len(set(self.store_widths)) != len(self.store_widths):
            raise ValueError("prefix-tail store widths must be unique")
        if any(width <= 0 or width & (width - 1) for width in self.store_widths):
            raise ValueError("prefix-tail store widths must be positive powers of two")
        if sum(self.store_widths) != self.load_lanes - 1:
            raise ValueError(
                "prefix-tail stores must encode every non-full live length"
            )
        if self.load_lanes != 8 or self.store_widths != (4, 2, 1):
            raise ValueError(
                "the current prefix-tail emitter supports exactly an 8-lane "
                "load with 4/2/1 stores"
            )


@dataclass(frozen=True, slots=True)
class UnaryPrefixTailObligationProfile:
    """Reviewed interface for one generated arbitrary-length value claim."""

    contract_module: str
    contract_namespace: str
    contract_predicate: str
    claim_name: str
    display_name: str
    element_width: int

    def __post_init__(self) -> None:
        for field in (
            self.contract_module,
            self.contract_namespace,
            self.contract_predicate,
            self.claim_name,
            self.display_name,
        ):
            if not field:
                raise ValueError("obligation profile fields must be non-empty")
        if self.element_width <= 0:
            raise ValueError("obligation element width must be positive")


@dataclass(frozen=True, slots=True)
class BinaryPrefixTailObligationProfile:
    """Reviewed interface for one generated binary arbitrary-length claim."""

    contract_module: str
    contract_namespace: str
    contract_predicate: str
    claim_name: str
    display_name: str
    element_width: int

    def __post_init__(self) -> None:
        for field in (
            self.contract_module,
            self.contract_namespace,
            self.contract_predicate,
            self.claim_name,
            self.display_name,
        ):
            if not field:
                raise ValueError("obligation profile fields must be non-empty")
        if self.element_width <= 0:
            raise ValueError("obligation element width must be positive")


@dataclass(frozen=True, slots=True)
class ModelProfile:
    case_id: str
    lean_namespace: str
    parameter_type: str
    parameter_fields: tuple[ParameterField, ...]
    rvv_scalar_types: tuple[tuple[str, str], ...]
    inputs: tuple[str, ...]
    neon_block_lanes: int
    neon_loop_condition: str
    neon_loop_update: str
    prefix_tail: PrefixTailProfile | None = None
    unary_prefix_tail_obligation: UnaryPrefixTailObligationProfile | None = None
    binary_prefix_tail_obligation: BinaryPrefixTailObligationProfile | None = None
    rvv_signed_shift_branch: bool = False

    def __post_init__(self) -> None:
        if (
            self.unary_prefix_tail_obligation is not None
            and self.binary_prefix_tail_obligation is not None
        ):
            raise ValueError("a model cannot configure unary and binary obligations")
        if (
            self.prefix_tail is not None
            and self.neon_block_lanes != self.prefix_tail.load_lanes
        ):
            raise ValueError(
                "a prefix-tail load width must match the fixed Neon block width"
            )
        if self.unary_prefix_tail_obligation is not None:
            if self.prefix_tail is None:
                raise ValueError("a unary prefix-tail obligation needs a tail profile")
            if len(self.inputs) != 1:
                raise ValueError("a unary prefix-tail obligation needs exactly one input")
        if self.binary_prefix_tail_obligation is not None:
            if self.prefix_tail is None:
                raise ValueError("a binary prefix-tail obligation needs a tail profile")
            if len(self.inputs) != 2:
                raise ValueError(
                    "a binary prefix-tail obligation needs exactly two inputs"
                )

    @property
    def generated_directory(self) -> str:
        return self.lean_namespace.rsplit(".", 1)[-1]

    @property
    def neon_function(self) -> str:
        return f"neonBlock{self.neon_block_lanes}FromIntrinsics"

    @property
    def rvv_function(self) -> str:
        return "rvvChunkFromIntrinsics"


S8_VCLAMP_MODEL = ModelProfile(
    case_id="s8-vclamp",
    lean_namespace="SALT.Generated.S8VClamp",
    parameter_type="S8ClampParams",
    parameter_fields=(ParameterField("min", 32), ParameterField("max", 32)),
    rvv_scalar_types=(("min", "signed char"), ("max", "signed char")),
    inputs=("input",),
    neon_block_lanes=64,
    neon_loop_condition="batch >= 64",
    neon_loop_update="batch -= 64",
)

QS8_VCVT_MODEL = ModelProfile(
    case_id="qs8-vcvt",
    lean_namespace="SALT.Generated.QS8VCvt",
    parameter_type="QS8CvtParams",
    parameter_fields=(
        ParameterField("input_zero_point", 16),
        ParameterField("multiplier", 32),
        ParameterField("output_zero_point", 16),
    ),
    rvv_scalar_types=(
        ("input_zero_point", "short"),
        ("multiplier", "short"),
        ("output_zero_point", "short"),
    ),
    inputs=("input",),
    neon_block_lanes=8,
    neon_loop_condition="batch >= 8 * sizeof(int8_t)",
    neon_loop_update="batch -= 8 * sizeof(int8_t)",
    prefix_tail=PrefixTailProfile(
        element_c_type="int8_t",
        load_lanes=8,
        store_widths=(4, 2, 1),
    ),
)

QS8_VLRELU_MODEL = ModelProfile(
    case_id="qs8-vlrelu",
    lean_namespace="SALT.Generated.QS8VLReLU",
    parameter_type="QS8LReLUParams",
    parameter_fields=(
        ParameterField("input_zero_point", 32),
        ParameterField("positive_multiplier", 32),
        ParameterField("negative_multiplier", 32),
        ParameterField("output_zero_point", 32),
    ),
    rvv_scalar_types=(
        ("input_zero_point", "short"),
        ("positive_multiplier", "short"),
        ("negative_multiplier", "short"),
        ("output_zero_point", "short"),
    ),
    inputs=("input",),
    neon_block_lanes=8,
    neon_loop_condition="batch >= 8 * sizeof(int8_t)",
    neon_loop_update="batch -= 8 * sizeof(int8_t)",
    prefix_tail=PrefixTailProfile(
        element_c_type="int8_t",
        load_lanes=8,
        store_widths=(4, 2, 1),
    ),
    unary_prefix_tail_obligation=UnaryPrefixTailObligationProfile(
        contract_module="SALT.Kernel.QS8VLReLU.Contract",
        contract_namespace="SALT.Kernel.QS8VLReLU",
        contract_predicate="WellFormedParams",
        claim_name="allLengthsValueEqualWithOverreadClaim",
        display_name="QS8 LReLU",
        element_width=8,
    ),
)

QU8_VADD_MINMAX_MODEL = ModelProfile(
    case_id="qu8-vadd-minmax",
    lean_namespace="SALT.Generated.QU8VAddMinmax",
    parameter_type="QU8AddMinmaxParams",
    parameter_fields=(
        ParameterField("a_zero_point", 8),
        ParameterField("b_zero_point", 8),
        ParameterField("a_multiplier", 32),
        ParameterField("b_multiplier", 32),
        ParameterField("shift", 32),
        ParameterField("output_zero_point", 16),
        ParameterField("output_min", 8),
        ParameterField("output_max", 8),
    ),
    rvv_scalar_types=(
        ("a_zero_point", "unsigned char"),
        ("b_zero_point", "unsigned char"),
        ("a_multiplier", "int"),
        ("b_multiplier", "int"),
        ("shift", "int"),
        ("output_zero_point", "short"),
        ("output_min", "unsigned char"),
        ("output_max", "unsigned char"),
    ),
    inputs=("input_a", "input_b"),
    neon_block_lanes=8,
    neon_loop_condition="batch >= 8 * sizeof(uint8_t)",
    neon_loop_update="batch -= 8 * sizeof(uint8_t)",
    prefix_tail=PrefixTailProfile(
        element_c_type="uint8_t",
        load_lanes=8,
        store_widths=(4, 2, 1),
    ),
    binary_prefix_tail_obligation=BinaryPrefixTailObligationProfile(
        contract_module="SALT.Kernel.QU8VAddMinmax.Contract",
        contract_namespace="SALT.Kernel.QU8VAddMinmax",
        contract_predicate="WellFormedParams",
        claim_name="allLengthsValueEqualWithOverreadClaim",
        display_name="QU8 VAdd Minmax",
        element_width=8,
    ),
    rvv_signed_shift_branch=True,
)

SCALE_UP_MODELS = {
    profile.case_id: profile
    for profile in (
        S8_VCLAMP_MODEL,
        QS8_VCVT_MODEL,
        QS8_VLRELU_MODEL,
        QU8_VADD_MINMAX_MODEL,
    )
}
