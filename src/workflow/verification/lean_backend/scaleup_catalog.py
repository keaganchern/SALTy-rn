"""Exact intrinsic catalogs for the next four integer kernel pairs.

This module is inventory only.  It deliberately does not register these cases with
the current ``qs8-vadd-minmax`` frontend or emitter.  Each catalog fixes exact C
spellings, call signatures, operation classes, and exported Lean semantic names
so that later frontend work has a reviewable target.

Existing ``qs8-vadd-minmax`` entries are reused by object identity when both their
signature and lowering contract apply unchanged.  A same-spelling entry is replaced
locally when the new case needs additional semantic operands, notably RVV rounding
shift and narrowing modes or the signed shift used by ``qu8-vadd-minmax``.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType

from .registry import (
    I8,
    I8X8,
    I8X16,
    I16,
    I16X4,
    I16X8,
    I32,
    I32X4,
    INT,
    QS8_VADD_MINMAX_REGISTRY,
    SIZE_T,
    U16,
    U16X4,
    U32,
    U32X2,
    UINT,
    VI8M2,
    VI16M4,
    VI32M8,
    VOID,
    build_registry,
)
from .schema import (
    Architecture,
    FunctionSignature,
    ImmediateConstraint,
    IntrinsicSpec,
    LeanArgument,
    OperandTransform,
    OperationShape,
    Parameter,
    PointerType,
    ScalarType,
    ScheduleIntrinsic,
    ScheduleOp,
    SemanticIntrinsic,
    Signedness,
    StructuralIntrinsic,
    StructuralOp,
    ValueType,
    VectorType,
)


U1 = ScalarType("_Bool", 1, Signedness.UNSIGNED)
U8 = ScalarType("uint8_t", 8, Signedness.UNSIGNED)

CONST_U8_PTR = PointerType(U8, const=True)
U8_PTR = PointerType(U8)
I8_PTR = PointerType(I8)
U16_PTR = PointerType(U16)
U32_PTR = PointerType(U32)

U8X8 = VectorType("uint8x8_t", U8, fixed_lanes=8)
U8X16 = VectorType("uint8x16_t", U8, fixed_lanes=16)
U16X8 = VectorType("uint16x8_t", U16, fixed_lanes=8)

VI8M8 = VectorType("vint8m8_t", I8, lmul="m8")
VU8M2 = VectorType("vuint8m2_t", U8, lmul="m2")
VU16M4 = VectorType("vuint16m4_t", U16, lmul="m4")

# ``vbool4_t`` is a scalable one-bit mask whose boolean grouping is b4.  The
# current schema has no distinct mask type, so ``lmul`` records the exact b4
# spelling category rather than claiming that b4 is an integer-vector LMUL.
VBOOL4 = VectorType("vbool4_t", U1, lmul="b4")


def _signature(result: ValueType, *parameters: tuple[str, ValueType]) -> FunctionSignature:
    return FunctionSignature(tuple(Parameter(name, type_) for name, type_ in parameters), result)


def _constraint(
    index: int,
    *values: int | str,
    erased_from_semantics: bool = True,
) -> ImmediateConstraint:
    return ImmediateConstraint(index, frozenset(values), erased_from_semantics)


def _semantic_constraint(index: int, *values: int | str) -> ImmediateConstraint:
    return _constraint(index, *values, erased_from_semantics=False)


def _arg(index: int, transform: OperandTransform = OperandTransform.IDENTITY) -> LeanArgument:
    return LeanArgument(index, transform)


def _structural(
    spelling: str,
    architecture: Architecture,
    signature: FunctionSignature,
    shape: OperationShape,
    operation: StructuralOp,
    *constraints: ImmediateConstraint,
) -> StructuralIntrinsic:
    return StructuralIntrinsic(
        spelling,
        architecture,
        signature,
        shape,
        operation,
        tuple(constraints),
    )


def _semantic(
    spelling: str,
    architecture: Architecture,
    signature: FunctionSignature,
    shape: OperationShape,
    lean_name: str,
    lean_arguments: tuple[LeanArgument, ...],
    *constraints: ImmediateConstraint,
) -> SemanticIntrinsic:
    return SemanticIntrinsic(
        spelling,
        architecture,
        signature,
        shape,
        lean_name,
        lean_arguments,
        tuple(constraints),
    )


def _schedule(spelling: str, signature: FunctionSignature) -> ScheduleIntrinsic:
    return ScheduleIntrinsic(
        spelling,
        Architecture.RVV,
        signature,
        OperationShape.SCHEDULE,
        ScheduleOp.SET_ACTIVE_LENGTH,
    )


def _existing(spelling: str, architecture: Architecture) -> IntrinsicSpec:
    spec = QS8_VADD_MINMAX_REGISTRY[spelling]
    if spec.architecture is not architecture:
        raise ValueError(f"{spelling} is not a reviewed {architecture.value} entry")
    return spec


@dataclass(frozen=True, slots=True)
class KernelIntrinsicCatalog:
    """Immutable, bidirectional intrinsic inventory for one C kernel pair."""

    kernel_name: str
    neon_specs: tuple[IntrinsicSpec, ...]
    rvv_specs: tuple[IntrinsicSpec, ...]
    registry: Mapping[str, IntrinsicSpec] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.kernel_name:
            raise ValueError("kernel catalog needs a non-empty name")
        if any(spec.architecture is not Architecture.NEON for spec in self.neon_specs):
            raise ValueError(f"{self.kernel_name} Neon inventory has a non-Neon entry")
        if any(spec.architecture is not Architecture.RVV for spec in self.rvv_specs):
            raise ValueError(f"{self.kernel_name} RVV inventory has a non-RVV entry")
        object.__setattr__(
            self,
            "registry",
            build_registry(self.neon_specs + self.rvv_specs),
        )

    @property
    def specs(self) -> tuple[IntrinsicSpec, ...]:
        return self.neon_specs + self.rvv_specs


# ---------------------------------------------------------------------------
# s8-vclamp
# ---------------------------------------------------------------------------

S8_VCLAMP_NEON_SPECS: tuple[IntrinsicSpec, ...] = (
    _existing("vdupq_n_s8", Architecture.NEON),
    _structural(
        "vld1q_s8",
        Architecture.NEON,
        _signature(I8X16, ("base", PointerType(I8, const=True))),
        OperationShape.LOAD,
        StructuralOp.LOAD,
    ),
    _semantic(
        "vmaxq_s8",
        Architecture.NEON,
        _signature(I8X16, ("left", I8X16), ("right", I8X16)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vmaxq_s8",
        (_arg(0), _arg(1)),
    ),
    _semantic(
        "vminq_s8",
        Architecture.NEON,
        _signature(I8X16, ("left", I8X16), ("right", I8X16)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vminq_s8",
        (_arg(0), _arg(1)),
    ),
    _existing("vst1q_s8", Architecture.NEON),
    _existing("vld1_s8", Architecture.NEON),
    _existing("vget_low_s8", Architecture.NEON),
    _semantic(
        "vmin_s8",
        Architecture.NEON,
        _signature(I8X8, ("left", I8X8), ("right", I8X8)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vmin_s8_vec",
        (_arg(0), _arg(1)),
    ),
    _semantic(
        "vmax_s8",
        Architecture.NEON,
        _signature(I8X8, ("left", I8X8), ("right", I8X8)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vmax_s8_vec",
        (_arg(0), _arg(1)),
    ),
    _existing("vst1_s8", Architecture.NEON),
    _existing("vreinterpret_u32_s8", Architecture.NEON),
    _existing("vst1_lane_u32", Architecture.NEON),
    _existing("vext_s8", Architecture.NEON),
    _existing("vreinterpret_u16_s8", Architecture.NEON),
    _existing("vst1_lane_u16", Architecture.NEON),
    _existing("vst1_lane_s8", Architecture.NEON),
)

S8_VCLAMP_RVV_SPECS: tuple[IntrinsicSpec, ...] = (
    _schedule("__riscv_vsetvl_e8m8", _signature(SIZE_T, ("avl", SIZE_T))),
    _structural(
        "__riscv_vle8_v_i8m8",
        Architecture.RVV,
        _signature(VI8M8, ("base", PointerType(I8, const=True)), ("vl", SIZE_T)),
        OperationShape.LOAD,
        StructuralOp.LOAD,
    ),
    _semantic(
        "__riscv_vmax_vx_i8m8",
        Architecture.RVV,
        _signature(VI8M8, ("vector", VI8M8), ("scalar", I8), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vmax_vx",
        (_arg(0), _arg(1)),
    ),
    _semantic(
        "__riscv_vmin_vx_i8m8",
        Architecture.RVV,
        _signature(VI8M8, ("vector", VI8M8), ("scalar", I8), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vmin_vx",
        (_arg(0), _arg(1)),
    ),
    _structural(
        "__riscv_vse8_v_i8m8",
        Architecture.RVV,
        _signature(VOID, ("base", I8_PTR), ("value", VI8M8), ("vl", SIZE_T)),
        OperationShape.STORE,
        StructuralOp.STORE,
    ),
)

S8_VCLAMP_CATALOG = KernelIntrinsicCatalog(
    "s8-vclamp", S8_VCLAMP_NEON_SPECS, S8_VCLAMP_RVV_SPECS
)
S8_VCLAMP_REGISTRY = S8_VCLAMP_CATALOG.registry


# ---------------------------------------------------------------------------
# qs8-vcvt
# ---------------------------------------------------------------------------

QS8_VCVT_NEON_SPECS: tuple[IntrinsicSpec, ...] = (
    _existing("vdupq_n_s16", Architecture.NEON),
    _existing("vld1_s8", Architecture.NEON),
    _semantic(
        "vsubw_s8",
        Architecture.NEON,
        _signature(I16X8, ("wide", I16X8), ("narrow", I8X8)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vsubw_s8",
        (_arg(0), _arg(1)),
    ),
    _semantic(
        "vshlq_n_s16",
        Architecture.NEON,
        _signature(I16X8, ("vector", I16X8), ("shift", INT)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.Neon.vshlq_n_s16",
        (_arg(0), _arg(1, OperandTransform.TO_NAT)),
        _semantic_constraint(1, 7),
    ),
    _semantic(
        "vqrdmulhq_s16",
        Architecture.NEON,
        _signature(I16X8, ("left", I16X8), ("right", I16X8)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vqrdmulhq_s16",
        (_arg(0), _arg(1)),
    ),
    _existing("vqaddq_s16", Architecture.NEON),
    _existing("vqmovn_s16", Architecture.NEON),
    _existing("vst1_s8", Architecture.NEON),
    _existing("vreinterpret_u32_s8", Architecture.NEON),
    _existing("vst1_lane_u32", Architecture.NEON),
    _existing("vext_s8", Architecture.NEON),
    _existing("vreinterpret_u16_s8", Architecture.NEON),
    _existing("vst1_lane_u16", Architecture.NEON),
    _existing("vst1_lane_s8", Architecture.NEON),
)

QS8_VCVT_RVV_SPECS: tuple[IntrinsicSpec, ...] = (
    _existing("__riscv_vsetvl_e8m2", Architecture.RVV),
    _existing("__riscv_vle8_v_i8m2", Architecture.RVV),
    _semantic(
        "__riscv_vsext_vf2_i16m4",
        Architecture.RVV,
        _signature(VI16M4, ("vector", VI8M2), ("vl", SIZE_T)),
        OperationShape.VECTOR_UNARY,
        "SALT.Intrinsics.RVV.vsext_vf2_i16",
        (_arg(0),),
    ),
    _semantic(
        "__riscv_vrsub_vx_i16m4",
        Architecture.RVV,
        _signature(VI16M4, ("vector", VI16M4), ("scalar", I16), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vrsub_vx_i16",
        (_arg(0), _arg(1)),
    ),
    _semantic(
        "__riscv_vsll_vx_i16m4",
        Architecture.RVV,
        _signature(VI16M4, ("vector", VI16M4), ("shift", SIZE_T), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vsll_vx_i16",
        (_arg(0), _arg(1, OperandTransform.TO_NAT)),
        _semantic_constraint(1, 7),
    ),
    _semantic(
        "__riscv_vwmul_vx_i32m8",
        Architecture.RVV,
        _signature(VI32M8, ("vector", VI16M4), ("scalar", I16), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vwmul_vx_i32",
        (_arg(0), _arg(1)),
    ),
    _semantic(
        "__riscv_vsll_vx_i32m8",
        Architecture.RVV,
        _signature(VI32M8, ("vector", VI32M8), ("shift", SIZE_T), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vsll_vx_i32",
        (_arg(0), _arg(1, OperandTransform.TO_NAT)),
        _semantic_constraint(1, 1),
    ),
    _semantic(
        "__riscv_vnclip_wx_i16m4",
        Architecture.RVV,
        _signature(
            VI16M4,
            ("vector", VI32M8),
            ("shift", SIZE_T),
            ("vxrm", UINT),
            ("vl", SIZE_T),
        ),
        OperationShape.VECTOR_TERNARY,
        "SALT.Intrinsics.RVV.vnclip_wx_i16_mode",
        (_arg(0), _arg(1, OperandTransform.TO_NAT), _arg(2)),
        _semantic_constraint(1, 16),
        _semantic_constraint(2, 0),
    ),
    _existing("__riscv_vsadd_vx_i16m4", Architecture.RVV),
    _semantic(
        "__riscv_vnclip_wx_i8m2",
        Architecture.RVV,
        _signature(
            VI8M2,
            ("vector", VI16M4),
            ("shift", SIZE_T),
            ("vxrm", UINT),
            ("vl", SIZE_T),
        ),
        OperationShape.VECTOR_TERNARY,
        "SALT.Intrinsics.RVV.vnclip_wx_i8_mode",
        (_arg(0), _arg(1, OperandTransform.TO_NAT), _arg(2)),
        _semantic_constraint(1, 0),
        _semantic_constraint(2, 2),
    ),
    _existing("__riscv_vse8_v_i8m2", Architecture.RVV),
)

QS8_VCVT_CATALOG = KernelIntrinsicCatalog(
    "qs8-vcvt", QS8_VCVT_NEON_SPECS, QS8_VCVT_RVV_SPECS
)
QS8_VCVT_REGISTRY = QS8_VCVT_CATALOG.registry


# ---------------------------------------------------------------------------
# qs8-vlrelu
# ---------------------------------------------------------------------------

QS8_VLRELU_NEON_SPECS: tuple[IntrinsicSpec, ...] = (
    _existing("vdupq_n_s16", Architecture.NEON),
    _existing("vld1_s8", Architecture.NEON),
    _semantic(
        "vsubw_s8",
        Architecture.NEON,
        _signature(I16X8, ("wide", I16X8), ("narrow", I8X8)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vsubw_s8",
        (_arg(0), _arg(1)),
    ),
    _structural(
        "vmovq_n_s16",
        Architecture.NEON,
        _signature(I16X8, ("value", I16)),
        OperationShape.BROADCAST,
        StructuralOp.BROADCAST,
    ),
    _semantic(
        "vcltq_s16",
        Architecture.NEON,
        _signature(U16X8, ("left", I16X8), ("right", I16X8)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vcltq_s16",
        (_arg(0), _arg(1)),
    ),
    _semantic(
        "vshlq_n_s16",
        Architecture.NEON,
        _signature(I16X8, ("vector", I16X8), ("shift", INT)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.Neon.vshlq_n_s16",
        (_arg(0), _arg(1, OperandTransform.TO_NAT)),
        _semantic_constraint(1, 7),
    ),
    _semantic(
        "vbslq_s16",
        Architecture.NEON,
        _signature(
            I16X8,
            ("mask", U16X8),
            ("if_true", I16X8),
            ("if_false", I16X8),
        ),
        OperationShape.VECTOR_TERNARY,
        "SALT.Intrinsics.Neon.vbslq_s16",
        (_arg(0), _arg(1), _arg(2)),
    ),
    _semantic(
        "vqrdmulhq_s16",
        Architecture.NEON,
        _signature(I16X8, ("left", I16X8), ("right", I16X8)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vqrdmulhq_s16",
        (_arg(0), _arg(1)),
    ),
    _existing("vqaddq_s16", Architecture.NEON),
    _existing("vqmovn_s16", Architecture.NEON),
    _existing("vst1_s8", Architecture.NEON),
    _existing("vreinterpret_u32_s8", Architecture.NEON),
    _existing("vst1_lane_u32", Architecture.NEON),
    _existing("vext_s8", Architecture.NEON),
    _existing("vreinterpret_u16_s8", Architecture.NEON),
    _existing("vst1_lane_u16", Architecture.NEON),
    _existing("vst1_lane_s8", Architecture.NEON),
)

QS8_VLRELU_RVV_SPECS: tuple[IntrinsicSpec, ...] = (
    _existing("__riscv_vsetvl_e8m2", Architecture.RVV),
    _existing("__riscv_vle8_v_i8m2", Architecture.RVV),
    _semantic(
        "__riscv_vsext_vf2_i16m4",
        Architecture.RVV,
        _signature(VI16M4, ("vector", VI8M2), ("vl", SIZE_T)),
        OperationShape.VECTOR_UNARY,
        "SALT.Intrinsics.RVV.vsext_vf2_i16",
        (_arg(0),),
    ),
    _semantic(
        "__riscv_vrsub_vx_i16m4",
        Architecture.RVV,
        _signature(VI16M4, ("vector", VI16M4), ("scalar", I16), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vrsub_vx_i16",
        (_arg(0), _arg(1)),
    ),
    _semantic(
        "__riscv_vmslt_vx_i16m4_b4",
        Architecture.RVV,
        _signature(VBOOL4, ("vector", VI16M4), ("scalar", I16), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vmslt_vx_i16",
        (_arg(0), _arg(1)),
    ),
    _semantic(
        "__riscv_vsll_vx_i16m4",
        Architecture.RVV,
        _signature(VI16M4, ("vector", VI16M4), ("shift", SIZE_T), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vsll_vx_i16",
        (_arg(0), _arg(1, OperandTransform.TO_NAT)),
        _semantic_constraint(1, 7),
    ),
    _structural(
        "__riscv_vmv_v_x_i16m4",
        Architecture.RVV,
        _signature(VI16M4, ("value", I16), ("vl", SIZE_T)),
        OperationShape.BROADCAST,
        StructuralOp.BROADCAST,
    ),
    _semantic(
        "__riscv_vmerge_vxm_i16m4",
        Architecture.RVV,
        _signature(
            VI16M4,
            ("if_false", VI16M4),
            ("if_true", I16),
            ("mask", VBOOL4),
            ("vl", SIZE_T),
        ),
        OperationShape.VECTOR_TERNARY,
        "SALT.Intrinsics.RVV.vmerge_vxm_i16",
        (_arg(0), _arg(1), _arg(2)),
    ),
    _semantic(
        "__riscv_vwmul_vv_i32m8",
        Architecture.RVV,
        _signature(VI32M8, ("left", VI16M4), ("right", VI16M4), ("vl", SIZE_T)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.RVV.vwmul_vv_i32",
        (_arg(0), _arg(1)),
    ),
    _semantic(
        "__riscv_vnclip_wx_i16m4",
        Architecture.RVV,
        _signature(
            VI16M4,
            ("vector", VI32M8),
            ("shift", SIZE_T),
            ("vxrm", UINT),
            ("vl", SIZE_T),
        ),
        OperationShape.VECTOR_TERNARY,
        "SALT.Intrinsics.RVV.vnclip_wx_i16_mode",
        (_arg(0), _arg(1, OperandTransform.TO_NAT), _arg(2)),
        _semantic_constraint(1, 15),
        _semantic_constraint(2, 0),
    ),
    _existing("__riscv_vsadd_vx_i16m4", Architecture.RVV),
    _semantic(
        "__riscv_vnclip_wx_i8m2",
        Architecture.RVV,
        _signature(
            VI8M2,
            ("vector", VI16M4),
            ("shift", SIZE_T),
            ("vxrm", UINT),
            ("vl", SIZE_T),
        ),
        OperationShape.VECTOR_TERNARY,
        "SALT.Intrinsics.RVV.vnclip_wx_i8_mode",
        (_arg(0), _arg(1, OperandTransform.TO_NAT), _arg(2)),
        _semantic_constraint(1, 0),
        _semantic_constraint(2, 2),
    ),
    _existing("__riscv_vse8_v_i8m2", Architecture.RVV),
)

QS8_VLRELU_CATALOG = KernelIntrinsicCatalog(
    "qs8-vlrelu", QS8_VLRELU_NEON_SPECS, QS8_VLRELU_RVV_SPECS
)
QS8_VLRELU_REGISTRY = QS8_VLRELU_CATALOG.registry


# ---------------------------------------------------------------------------
# qu8-vadd-minmax
# ---------------------------------------------------------------------------

QU8_VADD_MINMAX_NEON_SPECS: tuple[IntrinsicSpec, ...] = (
    _structural(
        "vdup_n_u8",
        Architecture.NEON,
        _signature(U8X8, ("value", U8)),
        OperationShape.BROADCAST,
        StructuralOp.BROADCAST,
    ),
    _existing("vdupq_n_s32", Architecture.NEON),
    _existing("vdupq_n_s16", Architecture.NEON),
    _structural(
        "vld1_u8",
        Architecture.NEON,
        _signature(U8X8, ("base", CONST_U8_PTR)),
        OperationShape.LOAD,
        StructuralOp.LOAD,
    ),
    _semantic(
        "vsubl_u8",
        Architecture.NEON,
        _signature(U16X8, ("left", U8X8), ("right", U8X8)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vsubl_u8",
        (_arg(0), _arg(1)),
    ),
    _structural(
        "vreinterpretq_s16_u16",
        Architecture.NEON,
        _signature(I16X8, ("value", U16X8)),
        OperationShape.REINTERPRET,
        StructuralOp.BITCAST,
    ),
    _existing("vget_low_s16", Architecture.NEON),
    _existing("vget_high_s16", Architecture.NEON),
    _existing("vmovl_s16", Architecture.NEON),
    _existing("vmulq_s32", Architecture.NEON),
    _existing("vmlaq_s32", Architecture.NEON),
    _semantic(
        "vrshlq_s32",
        Architecture.NEON,
        _signature(I32X4, ("vector", I32X4), ("shift", I32X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vrshlq_s32_vec",
        (_arg(0), _arg(1)),
    ),
    _existing("vqmovn_s32", Architecture.NEON),
    _existing("vcombine_s16", Architecture.NEON),
    _existing("vqaddq_s16", Architecture.NEON),
    _semantic(
        "vqmovun_s16",
        Architecture.NEON,
        _signature(U8X8, ("vector", I16X8)),
        OperationShape.VECTOR_UNARY,
        "SALT.Intrinsics.Neon.vqmovun_s16",
        (_arg(0),),
    ),
    _semantic(
        "vmax_u8",
        Architecture.NEON,
        _signature(U8X8, ("left", U8X8), ("right", U8X8)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vmax_u8",
        (_arg(0), _arg(1)),
    ),
    _semantic(
        "vmin_u8",
        Architecture.NEON,
        _signature(U8X8, ("left", U8X8), ("right", U8X8)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vmin_u8",
        (_arg(0), _arg(1)),
    ),
    _structural(
        "vst1_u8",
        Architecture.NEON,
        _signature(VOID, ("base", U8_PTR), ("value", U8X8)),
        OperationShape.STORE,
        StructuralOp.STORE,
    ),
    _structural(
        "vreinterpret_u32_u8",
        Architecture.NEON,
        _signature(U32X2, ("value", U8X8)),
        OperationShape.REINTERPRET,
        StructuralOp.BITCAST,
    ),
    _existing("vst1_lane_u32", Architecture.NEON),
    _structural(
        "vext_u8",
        Architecture.NEON,
        _signature(U8X8, ("left", U8X8), ("right", U8X8), ("offset", INT)),
        OperationShape.SLIDE,
        StructuralOp.EXTRACT_FROM_CONCAT,
        _constraint(2, 2, 4),
    ),
    _structural(
        "vreinterpret_u16_u8",
        Architecture.NEON,
        _signature(U16X4, ("value", U8X8)),
        OperationShape.REINTERPRET,
        StructuralOp.BITCAST,
    ),
    _existing("vst1_lane_u16", Architecture.NEON),
    _structural(
        "vst1_lane_u8",
        Architecture.NEON,
        _signature(VOID, ("base", U8_PTR), ("value", U8X8), ("lane", INT)),
        OperationShape.LANE_STORE,
        StructuralOp.LANE_STORE,
        _constraint(2, 0),
    ),
)

QU8_VADD_MINMAX_RVV_SPECS: tuple[IntrinsicSpec, ...] = (
    _existing("__riscv_vsetvl_e8m2", Architecture.RVV),
    _structural(
        "__riscv_vle8_v_u8m2",
        Architecture.RVV,
        _signature(VU8M2, ("base", CONST_U8_PTR), ("vl", SIZE_T)),
        OperationShape.LOAD,
        StructuralOp.LOAD,
    ),
    _semantic(
        "__riscv_vwsubu_vx_u16m4",
        Architecture.RVV,
        _signature(VU16M4, ("vector", VU8M2), ("scalar", U8), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vwsubu_vx_u16",
        (_arg(0), _arg(1)),
    ),
    _structural(
        "__riscv_vreinterpret_v_u16m4_i16m4",
        Architecture.RVV,
        _signature(VI16M4, ("value", VU16M4)),
        OperationShape.REINTERPRET,
        StructuralOp.BITCAST,
    ),
    _existing("__riscv_vsext_vf2_i32m8", Architecture.RVV),
    _existing("__riscv_vmul_vx_i32m8", Architecture.RVV),
    _existing("__riscv_vmacc_vx_i32m8", Architecture.RVV),
    _semantic(
        "__riscv_vssra_vx_i32m8",
        Architecture.RVV,
        _signature(
            VI32M8,
            ("vector", VI32M8),
            ("shift", SIZE_T),
            ("vxrm", UINT),
            ("vl", SIZE_T),
        ),
        OperationShape.VECTOR_TERNARY,
        "SALT.Intrinsics.RVV.vssra_vx_i32_mode",
        (_arg(0), _arg(1, OperandTransform.TO_NAT), _arg(2)),
        _semantic_constraint(2, 0),
    ),
    _semantic(
        "__riscv_vsll_vx_i32m8",
        Architecture.RVV,
        _signature(VI32M8, ("vector", VI32M8), ("shift", SIZE_T), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vsll_vx_i32",
        (_arg(0), _arg(1, OperandTransform.TO_NAT)),
    ),
    _semantic(
        "__riscv_vnclip_wx_i16m4",
        Architecture.RVV,
        _signature(
            VI16M4,
            ("vector", VI32M8),
            ("shift", SIZE_T),
            ("vxrm", UINT),
            ("vl", SIZE_T),
        ),
        OperationShape.VECTOR_TERNARY,
        "SALT.Intrinsics.RVV.vnclip_wx_i16_mode",
        (_arg(0), _arg(1, OperandTransform.TO_NAT), _arg(2)),
        _semantic_constraint(1, 0),
        _semantic_constraint(2, 2),
    ),
    _existing("__riscv_vsadd_vx_i16m4", Architecture.RVV),
    _semantic(
        "__riscv_vmax_vx_i16m4",
        Architecture.RVV,
        _signature(VI16M4, ("vector", VI16M4), ("scalar", I16), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vmax_vx_i16",
        (_arg(0), _arg(1)),
    ),
    _structural(
        "__riscv_vreinterpret_v_i16m4_u16m4",
        Architecture.RVV,
        _signature(VU16M4, ("value", VI16M4)),
        OperationShape.REINTERPRET,
        StructuralOp.BITCAST,
    ),
    _semantic(
        "__riscv_vnclipu_wx_u8m2",
        Architecture.RVV,
        _signature(
            VU8M2,
            ("vector", VU16M4),
            ("shift", SIZE_T),
            ("vxrm", UINT),
            ("vl", SIZE_T),
        ),
        OperationShape.VECTOR_TERNARY,
        "SALT.Intrinsics.RVV.vnclipu_wx_u8_mode",
        (_arg(0), _arg(1, OperandTransform.TO_NAT), _arg(2)),
        _semantic_constraint(1, 0),
        _semantic_constraint(2, 2),
    ),
    _semantic(
        "__riscv_vmaxu_vx_u8m2",
        Architecture.RVV,
        _signature(VU8M2, ("vector", VU8M2), ("scalar", U8), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vmaxu_vx_u8",
        (_arg(0), _arg(1)),
    ),
    _semantic(
        "__riscv_vminu_vx_u8m2",
        Architecture.RVV,
        _signature(VU8M2, ("vector", VU8M2), ("scalar", U8), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vminu_vx_u8",
        (_arg(0), _arg(1)),
    ),
    _structural(
        "__riscv_vse8_v_u8m2",
        Architecture.RVV,
        _signature(VOID, ("base", U8_PTR), ("value", VU8M2), ("vl", SIZE_T)),
        OperationShape.STORE,
        StructuralOp.STORE,
    ),
)

QU8_VADD_MINMAX_CATALOG = KernelIntrinsicCatalog(
    "qu8-vadd-minmax", QU8_VADD_MINMAX_NEON_SPECS, QU8_VADD_MINMAX_RVV_SPECS
)
QU8_VADD_MINMAX_REGISTRY = QU8_VADD_MINMAX_CATALOG.registry


SCALEUP_CATALOGS: Mapping[str, KernelIntrinsicCatalog] = MappingProxyType(
    {
        catalog.kernel_name: catalog
        for catalog in (
            S8_VCLAMP_CATALOG,
            QS8_VCVT_CATALOG,
            QS8_VLRELU_CATALOG,
            QU8_VADD_MINMAX_CATALOG,
        )
    }
)


CATALOG_SCHEMA_LIMITATIONS: tuple[str, ...] = (
    "vbool4_t is represented as a scalable one-bit VectorType with lmul='b4'; "
    "the schema does not yet distinguish mask grouping from integer-vector LMUL",
    "RVV vxrm operands remain typed UINT values in the C catalog and are passed "
    "as numeric Nat modes to Lean, which decodes them to VXRoundingMode; the "
    "schema does not yet expose a distinct C enum/mode type",
    "qu8-vadd-minmax needs signed bidirectional vrshlq_s32 semantics; its local "
    "entry intentionally does not reuse the right-shift-only qs8 lowering",
    "the current Lean RVV vmslt model uses List Bool, while Neon vclt uses "
    "all-zero/all-one BitVec 16 lanes; the RVV abstraction is faithful for the "
    "reviewed compare-merge pipeline but is not a standalone mask-register semantics",
)
