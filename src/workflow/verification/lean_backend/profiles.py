"""Reviewed Clang-frontend profiles for supported integer kernel pairs.

These profiles contain parsing contracts only: exact C function types, parameter
spellings, assertions, target triples, and intrinsic declarations.  They do not
assign Lean, C, or ISA semantics to an intrinsic.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping

from .registry import QS8_VADD_MINMAX_NEON_SPECS, QS8_VADD_MINMAX_RVV_SPECS
from .schema import Architecture, IntrinsicSpec, render_clang_function_type


_FACADE_DIRECTORY = Path(__file__).with_name("facade")


@dataclass(frozen=True, slots=True)
class FrontendIntrinsicSpec:
    """One exact intrinsic spelling and the Clang function type it must have."""

    spelling: str
    arity: int
    function_type: str

    def __post_init__(self) -> None:
        if not self.spelling or self.spelling.strip() != self.spelling:
            raise ValueError("frontend intrinsic spelling must be an exact non-empty token")
        if self.arity < 0:
            raise ValueError("frontend intrinsic arity must be non-negative")
        if not self.function_type:
            raise ValueError("frontend intrinsic function type must not be empty")


@dataclass(frozen=True, slots=True)
class FrontendAssertion:
    """One exact assertion invocation and its containing control node."""

    source_text: str
    parent_control: str | None

    def __post_init__(self) -> None:
        if not self.source_text:
            raise ValueError("frontend assertion source text must not be empty")


@dataclass(frozen=True, slots=True)
class FrontendSideProfile:
    """Complete parse contract for one architecture side of a kernel pair."""

    architecture: Architecture
    facade_path: Path
    intrinsic_specs: tuple[FrontendIntrinsicSpec, ...]
    function_name: str
    target_triple: str
    function_type: str
    parameters: tuple[tuple[str, str], ...]
    assertions: tuple[FrontendAssertion, ...]
    member_roots: frozenset[str] = frozenset({"params"})

    def __post_init__(self) -> None:
        if not self.function_name:
            raise ValueError("frontend function name must not be empty")
        if not self.target_triple:
            raise ValueError("frontend target triple must not be empty")
        if not self.function_type:
            raise ValueError("frontend function type must not be empty")
        spellings = [spec.spelling for spec in self.intrinsic_specs]
        if len(spellings) != len(set(spellings)):
            raise ValueError("frontend intrinsic spellings must be unique within one side")
        parameter_names = [name for name, _ in self.parameters]
        if len(parameter_names) != len(set(parameter_names)):
            raise ValueError("frontend parameter names must be unique")
        if not self.member_roots:
            raise ValueError("frontend member roots must not be empty")

    @property
    def arities(self) -> dict[str, int]:
        return {spec.spelling: spec.arity for spec in self.intrinsic_specs}

    @property
    def signatures(self) -> dict[str, str]:
        return {spec.spelling: spec.function_type for spec in self.intrinsic_specs}


@dataclass(frozen=True, slots=True)
class FrontendProfile:
    """Named Neon/RVV pair of reviewed frontend contracts."""

    kernel_name: str
    neon: FrontendSideProfile
    rvv: FrontendSideProfile

    def __post_init__(self) -> None:
        if not self.kernel_name:
            raise ValueError("frontend kernel name must not be empty")
        if self.neon.architecture is not Architecture.NEON:
            raise ValueError("frontend Neon side must use the Neon architecture")
        if self.rvv.architecture is not Architecture.RVV:
            raise ValueError("frontend RVV side must use the RVV architecture")

    def side(self, architecture: Architecture) -> FrontendSideProfile:
        return self.neon if architecture is Architecture.NEON else self.rvv


def _call(spelling: str, result: str, *parameters: str) -> FrontendIntrinsicSpec:
    rendered_parameters = ", ".join(parameters)
    return FrontendIntrinsicSpec(
        spelling=spelling,
        arity=len(parameters),
        function_type=f"{result} ({rendered_parameters})",
    )


def _from_registry(specs: tuple[IntrinsicSpec, ...]) -> tuple[FrontendIntrinsicSpec, ...]:
    return tuple(
        FrontendIntrinsicSpec(
            spelling=spec.spelling,
            arity=len(spec.signature.parameters),
            function_type=render_clang_function_type(spec.signature),
        )
        for spec in specs
    )


def _side(
    architecture: Architecture,
    facade: str,
    intrinsic_specs: tuple[FrontendIntrinsicSpec, ...],
    function_type: str,
    parameters: tuple[tuple[str, str], ...],
    assertions: tuple[FrontendAssertion, ...],
) -> FrontendSideProfile:
    return FrontendSideProfile(
        architecture=architecture,
        facade_path=_FACADE_DIRECTORY / facade,
        intrinsic_specs=intrinsic_specs,
        function_name="test_neon" if architecture is Architecture.NEON else "test_rvv",
        target_triple=(
            "aarch64-none-elf"
            if architecture is Architecture.NEON
            else "riscv64-none-elf"
        ),
        function_type=function_type,
        parameters=parameters,
        assertions=assertions,
    )


def _assertion(
    source_text: str, parent_control: str | None = None
) -> FrontendAssertion:
    return FrontendAssertion(source_text, parent_control)


_SIGNED_UNARY_PARAMETERS = (
    ("batch", "unsigned long"),
    ("input", "const int8_t *"),
    ("output", "int8_t *"),
)
_SIGNED_UNARY_ASSERTIONS = (
    _assertion("assert(batch!=0);"),
    _assertion("assert(batch%sizeof(int8_t)==0);"),
    _assertion("assert(input!=NULL);"),
    _assertion("assert(output!=NULL);"),
)
_SIGNED_BINARY_PARAMETERS = (
    ("batch", "unsigned long"),
    ("input_a", "const int8_t *"),
    ("input_b", "const int8_t *"),
    ("output", "int8_t *"),
)
_SIGNED_BINARY_ASSERTIONS = (
    _assertion("assert(batch!=0);"),
    _assertion("assert(batch%sizeof(int8_t)==0);"),
    _assertion("assert(input_a!=NULL);"),
    _assertion("assert(input_b!=NULL);"),
    _assertion("assert(output!=NULL);"),
)
_PARTIAL_SIGNED_ASSERTIONS = _SIGNED_UNARY_ASSERTIONS + (
    _assertion("assert(batch>=1*sizeof(int8_t));", "control_0001"),
    _assertion("assert(batch<=7*sizeof(int8_t));", "control_0001"),
)


QS8_VADD_MINMAX = FrontendProfile(
    kernel_name="qs8-vadd-minmax",
    neon=_side(
        Architecture.NEON,
        "qs8_vadd_minmax.h",
        _from_registry(QS8_VADD_MINMAX_NEON_SPECS),
        (
            "void (size_t, const int8_t *, const int8_t *, int8_t *, "
            "const struct xnn_qs8_add_minmax_params *restrict)"
        ),
        _SIGNED_BINARY_PARAMETERS
        + (("params", "const struct xnn_qs8_add_minmax_params *restrict"),),
        _SIGNED_BINARY_ASSERTIONS,
    ),
    rvv=_side(
        Architecture.RVV,
        "qs8_vadd_minmax.h",
        _from_registry(QS8_VADD_MINMAX_RVV_SPECS),
        (
            "void (size_t, const int8_t *, const int8_t *, int8_t *, "
            "const struct xnn_qs8_add_minmax_params *restrict)"
        ),
        _SIGNED_BINARY_PARAMETERS
        + (("params", "const struct xnn_qs8_add_minmax_params *restrict"),),
        _SIGNED_BINARY_ASSERTIONS,
    ),
)


_S8_VCLAMP_NEON = (
    _call("vdupq_n_s8", "int8x16_t", "int8_t"),
    _call("vld1q_s8", "int8x16_t", "const int8_t *"),
    _call("vmaxq_s8", "int8x16_t", "int8x16_t", "int8x16_t"),
    _call("vminq_s8", "int8x16_t", "int8x16_t", "int8x16_t"),
    _call("vst1q_s8", "void", "int8_t *", "int8x16_t"),
    _call("vld1_s8", "int8x8_t", "const int8_t *"),
    _call("vget_low_s8", "int8x8_t", "int8x16_t"),
    _call("vmin_s8", "int8x8_t", "int8x8_t", "int8x8_t"),
    _call("vmax_s8", "int8x8_t", "int8x8_t", "int8x8_t"),
    _call("vst1_s8", "void", "int8_t *", "int8x8_t"),
    _call("vreinterpret_u32_s8", "uint32x2_t", "int8x8_t"),
    _call("vst1_lane_u32", "void", "uint32_t *", "uint32x2_t", "int"),
    _call("vext_s8", "int8x8_t", "int8x8_t", "int8x8_t", "int"),
    _call("vreinterpret_u16_s8", "uint16x4_t", "int8x8_t"),
    _call("vst1_lane_u16", "void", "uint16_t *", "uint16x4_t", "int"),
    _call("vst1_lane_s8", "void", "int8_t *", "int8x8_t", "int"),
)
_S8_VCLAMP_RVV = (
    _call("__riscv_vsetvl_e8m8", "size_t", "size_t"),
    _call("__riscv_vle8_v_i8m8", "vint8m8_t", "const int8_t *", "size_t"),
    _call("__riscv_vmax_vx_i8m8", "vint8m8_t", "vint8m8_t", "int8_t", "size_t"),
    _call("__riscv_vmin_vx_i8m8", "vint8m8_t", "vint8m8_t", "int8_t", "size_t"),
    _call("__riscv_vse8_v_i8m8", "void", "int8_t *", "vint8m8_t", "size_t"),
)

S8_VCLAMP = FrontendProfile(
    kernel_name="s8-vclamp",
    neon=_side(
        Architecture.NEON,
        "s8_vclamp.h",
        _S8_VCLAMP_NEON,
        (
            "void (size_t, const int8_t *, int8_t *, "
            "const struct xnn_s8_minmax_params *restrict)"
        ),
        _SIGNED_UNARY_PARAMETERS
        + (("params", "const struct xnn_s8_minmax_params *restrict"),),
        _SIGNED_UNARY_ASSERTIONS,
    ),
    rvv=_side(
        Architecture.RVV,
        "s8_vclamp.h",
        _S8_VCLAMP_RVV,
        (
            "void (size_t, const int8_t *, int8_t *, "
            "const struct xnn_s8_minmax_params *restrict)"
        ),
        _SIGNED_UNARY_PARAMETERS
        + (("params", "const struct xnn_s8_minmax_params *restrict"),),
        _SIGNED_UNARY_ASSERTIONS,
    ),
)


_SIGNED_PARTIAL_NEON = (
    _call("vdupq_n_s16", "int16x8_t", "int16_t"),
    _call("vld1_s8", "int8x8_t", "const int8_t *"),
    _call("vsubw_s8", "int16x8_t", "int16x8_t", "int8x8_t"),
    _call("vshlq_n_s16", "int16x8_t", "int16x8_t", "int"),
    _call("vqrdmulhq_s16", "int16x8_t", "int16x8_t", "int16x8_t"),
    _call("vqaddq_s16", "int16x8_t", "int16x8_t", "int16x8_t"),
    _call("vqmovn_s16", "int8x8_t", "int16x8_t"),
    _call("vst1_s8", "void", "int8_t *", "int8x8_t"),
    _call("vreinterpret_u32_s8", "uint32x2_t", "int8x8_t"),
    _call("vst1_lane_u32", "void", "uint32_t *", "uint32x2_t", "int"),
    _call("vext_s8", "int8x8_t", "int8x8_t", "int8x8_t", "int"),
    _call("vreinterpret_u16_s8", "uint16x4_t", "int8x8_t"),
    _call("vst1_lane_u16", "void", "uint16_t *", "uint16x4_t", "int"),
    _call("vst1_lane_s8", "void", "int8_t *", "int8x8_t", "int"),
)
_QS8_CONVERSION_RVV = (
    _call("__riscv_vsetvl_e8m2", "size_t", "size_t"),
    _call("__riscv_vle8_v_i8m2", "vint8m2_t", "const int8_t *", "size_t"),
    _call("__riscv_vsext_vf2_i16m4", "vint16m4_t", "vint8m2_t", "size_t"),
    _call("__riscv_vrsub_vx_i16m4", "vint16m4_t", "vint16m4_t", "int16_t", "size_t"),
    _call("__riscv_vsll_vx_i16m4", "vint16m4_t", "vint16m4_t", "size_t", "size_t"),
    _call("__riscv_vwmul_vx_i32m8", "vint32m8_t", "vint16m4_t", "int16_t", "size_t"),
    _call("__riscv_vsll_vx_i32m8", "vint32m8_t", "vint32m8_t", "size_t", "size_t"),
    _call(
        "__riscv_vnclip_wx_i16m4",
        "vint16m4_t",
        "vint32m8_t",
        "size_t",
        "unsigned int",
        "size_t",
    ),
    _call("__riscv_vsadd_vx_i16m4", "vint16m4_t", "vint16m4_t", "int16_t", "size_t"),
    _call(
        "__riscv_vnclip_wx_i8m2",
        "vint8m2_t",
        "vint16m4_t",
        "size_t",
        "unsigned int",
        "size_t",
    ),
    _call("__riscv_vse8_v_i8m2", "void", "int8_t *", "vint8m2_t", "size_t"),
)

QS8_VCVT = FrontendProfile(
    kernel_name="qs8-vcvt",
    neon=_side(
        Architecture.NEON,
        "qs8_vcvt.h",
        _SIGNED_PARTIAL_NEON,
        (
            "void (size_t, const int8_t *, int8_t *, "
            "const struct xnn_qs8_cvt_params *restrict)"
        ),
        _SIGNED_UNARY_PARAMETERS
        + (("params", "const struct xnn_qs8_cvt_params *restrict"),),
        _PARTIAL_SIGNED_ASSERTIONS,
    ),
    rvv=_side(
        Architecture.RVV,
        "qs8_vcvt.h",
        _QS8_CONVERSION_RVV,
        (
            "void (size_t, const int8_t *, int8_t *, "
            "const struct xnn_qs8_cvt_params *restrict)"
        ),
        _SIGNED_UNARY_PARAMETERS
        + (("params", "const struct xnn_qs8_cvt_params *restrict"),),
        _SIGNED_UNARY_ASSERTIONS,
    ),
)


_QS8_VLRELU_NEON = _SIGNED_PARTIAL_NEON + (
    _call("vmovq_n_s16", "int16x8_t", "int16_t"),
    _call("vcltq_s16", "uint16x8_t", "int16x8_t", "int16x8_t"),
    _call("vbslq_s16", "int16x8_t", "uint16x8_t", "int16x8_t", "int16x8_t"),
)
_QS8_VLRELU_RVV = (
    _call("__riscv_vsetvl_e8m2", "size_t", "size_t"),
    _call("__riscv_vle8_v_i8m2", "vint8m2_t", "const int8_t *", "size_t"),
    _call("__riscv_vsext_vf2_i16m4", "vint16m4_t", "vint8m2_t", "size_t"),
    _call("__riscv_vrsub_vx_i16m4", "vint16m4_t", "vint16m4_t", "int16_t", "size_t"),
    _call("__riscv_vmslt_vx_i16m4_b4", "vbool4_t", "vint16m4_t", "int16_t", "size_t"),
    _call("__riscv_vsll_vx_i16m4", "vint16m4_t", "vint16m4_t", "size_t", "size_t"),
    _call("__riscv_vmv_v_x_i16m4", "vint16m4_t", "int16_t", "size_t"),
    _call(
        "__riscv_vmerge_vxm_i16m4",
        "vint16m4_t",
        "vint16m4_t",
        "int16_t",
        "vbool4_t",
        "size_t",
    ),
    _call("__riscv_vwmul_vv_i32m8", "vint32m8_t", "vint16m4_t", "vint16m4_t", "size_t"),
    _call(
        "__riscv_vnclip_wx_i16m4",
        "vint16m4_t",
        "vint32m8_t",
        "size_t",
        "unsigned int",
        "size_t",
    ),
    _call("__riscv_vsadd_vx_i16m4", "vint16m4_t", "vint16m4_t", "int16_t", "size_t"),
    _call(
        "__riscv_vnclip_wx_i8m2",
        "vint8m2_t",
        "vint16m4_t",
        "size_t",
        "unsigned int",
        "size_t",
    ),
    _call("__riscv_vse8_v_i8m2", "void", "int8_t *", "vint8m2_t", "size_t"),
)

QS8_VLRELU = FrontendProfile(
    kernel_name="qs8-vlrelu",
    neon=_side(
        Architecture.NEON,
        "qs8_vlrelu.h",
        _QS8_VLRELU_NEON,
        (
            "void (size_t, const int8_t *, int8_t *, "
            "const struct xnn_qs8_lrelu_params *restrict)"
        ),
        _SIGNED_UNARY_PARAMETERS
        + (("params", "const struct xnn_qs8_lrelu_params *restrict"),),
        _PARTIAL_SIGNED_ASSERTIONS,
    ),
    rvv=_side(
        Architecture.RVV,
        "qs8_vlrelu.h",
        _QS8_VLRELU_RVV,
        (
            "void (size_t, const int8_t *, int8_t *, "
            "const struct xnn_qs8_lrelu_params *restrict)"
        ),
        _SIGNED_UNARY_PARAMETERS
        + (("params", "const struct xnn_qs8_lrelu_params *restrict"),),
        _SIGNED_UNARY_ASSERTIONS,
    ),
)


_QU8_VADD_NEON = (
    _call("vdup_n_u8", "uint8x8_t", "uint8_t"),
    _call("vdupq_n_s32", "int32x4_t", "int32_t"),
    _call("vdupq_n_s16", "int16x8_t", "int16_t"),
    _call("vld1_u8", "uint8x8_t", "const uint8_t *"),
    _call("vsubl_u8", "uint16x8_t", "uint8x8_t", "uint8x8_t"),
    _call("vreinterpretq_s16_u16", "int16x8_t", "uint16x8_t"),
    _call("vget_low_s16", "int16x4_t", "int16x8_t"),
    _call("vget_high_s16", "int16x4_t", "int16x8_t"),
    _call("vmovl_s16", "int32x4_t", "int16x4_t"),
    _call("vmulq_s32", "int32x4_t", "int32x4_t", "int32x4_t"),
    _call("vmlaq_s32", "int32x4_t", "int32x4_t", "int32x4_t", "int32x4_t"),
    _call("vrshlq_s32", "int32x4_t", "int32x4_t", "int32x4_t"),
    _call("vqmovn_s32", "int16x4_t", "int32x4_t"),
    _call("vcombine_s16", "int16x8_t", "int16x4_t", "int16x4_t"),
    _call("vqaddq_s16", "int16x8_t", "int16x8_t", "int16x8_t"),
    _call("vqmovun_s16", "uint8x8_t", "int16x8_t"),
    _call("vmax_u8", "uint8x8_t", "uint8x8_t", "uint8x8_t"),
    _call("vmin_u8", "uint8x8_t", "uint8x8_t", "uint8x8_t"),
    _call("vst1_u8", "void", "uint8_t *", "uint8x8_t"),
    _call("vreinterpret_u32_u8", "uint32x2_t", "uint8x8_t"),
    _call("vst1_lane_u32", "void", "uint32_t *", "uint32x2_t", "int"),
    _call("vext_u8", "uint8x8_t", "uint8x8_t", "uint8x8_t", "int"),
    _call("vreinterpret_u16_u8", "uint16x4_t", "uint8x8_t"),
    _call("vst1_lane_u16", "void", "uint16_t *", "uint16x4_t", "int"),
    _call("vst1_lane_u8", "void", "uint8_t *", "uint8x8_t", "int"),
)
_QU8_VADD_RVV = (
    _call("__riscv_vsetvl_e8m2", "size_t", "size_t"),
    _call("__riscv_vle8_v_u8m2", "vuint8m2_t", "const uint8_t *", "size_t"),
    _call("__riscv_vwsubu_vx_u16m4", "vuint16m4_t", "vuint8m2_t", "uint8_t", "size_t"),
    _call("__riscv_vreinterpret_v_u16m4_i16m4", "vint16m4_t", "vuint16m4_t"),
    _call("__riscv_vsext_vf2_i32m8", "vint32m8_t", "vint16m4_t", "size_t"),
    _call("__riscv_vmul_vx_i32m8", "vint32m8_t", "vint32m8_t", "int32_t", "size_t"),
    _call(
        "__riscv_vmacc_vx_i32m8",
        "vint32m8_t",
        "vint32m8_t",
        "int32_t",
        "vint32m8_t",
        "size_t",
    ),
    _call(
        "__riscv_vssra_vx_i32m8",
        "vint32m8_t",
        "vint32m8_t",
        "size_t",
        "unsigned int",
        "size_t",
    ),
    _call("__riscv_vsll_vx_i32m8", "vint32m8_t", "vint32m8_t", "size_t", "size_t"),
    _call(
        "__riscv_vnclip_wx_i16m4",
        "vint16m4_t",
        "vint32m8_t",
        "size_t",
        "unsigned int",
        "size_t",
    ),
    _call("__riscv_vsadd_vx_i16m4", "vint16m4_t", "vint16m4_t", "int16_t", "size_t"),
    _call("__riscv_vmax_vx_i16m4", "vint16m4_t", "vint16m4_t", "int16_t", "size_t"),
    _call("__riscv_vreinterpret_v_i16m4_u16m4", "vuint16m4_t", "vint16m4_t"),
    _call(
        "__riscv_vnclipu_wx_u8m2",
        "vuint8m2_t",
        "vuint16m4_t",
        "size_t",
        "unsigned int",
        "size_t",
    ),
    _call("__riscv_vmaxu_vx_u8m2", "vuint8m2_t", "vuint8m2_t", "uint8_t", "size_t"),
    _call("__riscv_vminu_vx_u8m2", "vuint8m2_t", "vuint8m2_t", "uint8_t", "size_t"),
    _call("__riscv_vse8_v_u8m2", "void", "uint8_t *", "vuint8m2_t", "size_t"),
)

_UNSIGNED_BINARY_PARAMETERS = (
    ("batch", "unsigned long"),
    ("input_a", "const uint8_t *"),
    ("input_b", "const uint8_t *"),
    ("output", "uint8_t *"),
)
_UNSIGNED_BINARY_ASSERTIONS = (
    _assertion("assert(batch!=0);"),
    _assertion("assert(batch%sizeof(uint8_t)==0);"),
    _assertion("assert(input_a!=NULL);"),
    _assertion("assert(input_b!=NULL);"),
    _assertion("assert(output!=NULL);"),
)

QU8_VADD_MINMAX = FrontendProfile(
    kernel_name="qu8-vadd-minmax",
    neon=_side(
        Architecture.NEON,
        "qu8_vadd_minmax.h",
        _QU8_VADD_NEON,
        (
            "void (size_t, const uint8_t *, const uint8_t *, uint8_t *, "
            "const struct xnn_qu8_add_minmax_params *restrict)"
        ),
        _UNSIGNED_BINARY_PARAMETERS
        + (("params", "const struct xnn_qu8_add_minmax_params *restrict"),),
        _UNSIGNED_BINARY_ASSERTIONS,
    ),
    rvv=_side(
        Architecture.RVV,
        "qu8_vadd_minmax.h",
        _QU8_VADD_RVV,
        (
            "void (size_t, const uint8_t *, const uint8_t *, uint8_t *, "
            "const struct xnn_qu8_add_minmax_params *restrict)"
        ),
        _UNSIGNED_BINARY_PARAMETERS
        + (("params", "const struct xnn_qu8_add_minmax_params *restrict"),),
        _UNSIGNED_BINARY_ASSERTIONS,
    ),
)


FRONTEND_PROFILES: Mapping[str, FrontendProfile] = MappingProxyType(
    {
        profile.kernel_name: profile
        for profile in (
            QS8_VADD_MINMAX,
            S8_VCLAMP,
            QS8_VCVT,
            QS8_VLRELU,
            QU8_VADD_MINMAX,
        )
    }
)


def frontend_profile(kernel_name: str) -> FrontendProfile:
    """Return one reviewed exact-name profile or reject the lookup."""

    try:
        return FRONTEND_PROFILES[kernel_name]
    except KeyError as error:
        raise KeyError(f"unknown frontend profile {kernel_name!r}") from error
