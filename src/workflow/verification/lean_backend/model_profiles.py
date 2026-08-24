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
    """Reviewed byte-tail grammar for one fixed-width unary Neon loop."""

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
