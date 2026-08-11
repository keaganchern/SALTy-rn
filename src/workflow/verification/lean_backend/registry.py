"""Exact intrinsic registry for the first ``qs8-vadd-minmax`` vertical slice.

This table is intentionally kernel-scoped.  It contains every intrinsic token
that occurs in the selected Neon/RVV pair and no wildcard, suffix inference, or
architecture aliasing.  Adding another spelling requires adding and reviewing a
new entry with its complete C signature and lowering metadata.
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from types import MappingProxyType

from .schema import (
    Architecture,
    FunctionSignature,
    ImmediateConstraint,
    IntrinsicNode,
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
    TypedOperand,
    ValueType,
    VectorType,
    VoidType,
    make_node,
)


class DuplicateIntrinsicError(ValueError):
    """Two reviewed entries claim the same exact C spelling."""


class UnknownIntrinsicError(LookupError):
    """No reviewed entry exists for the exact source spelling."""


class ArchitectureMismatchError(LookupError):
    """The spelling exists, but not for the architecture being translated."""


# Canonical source-level scalar and vector types used by this kernel pair.
I8 = ScalarType("int8_t", 8, Signedness.SIGNED)
I16 = ScalarType("int16_t", 16, Signedness.SIGNED)
I32 = ScalarType("int32_t", 32, Signedness.SIGNED)
U16 = ScalarType("uint16_t", 16, Signedness.UNSIGNED)
U32 = ScalarType("uint32_t", 32, Signedness.UNSIGNED)
INT = ScalarType("int", 32, Signedness.SIGNED)
UINT = ScalarType("unsigned int", 32, Signedness.UNSIGNED)
# ``size_t`` width belongs to the pinned Clang target, so it is not guessed here.
SIZE_T = ScalarType("size_t", None, Signedness.UNSIGNED)
VOID = VoidType()

CONST_I8_PTR = PointerType(I8, const=True)
I8_PTR = PointerType(I8)
U16_PTR = PointerType(U16)
U32_PTR = PointerType(U32)

I8X8 = VectorType("int8x8_t", I8, fixed_lanes=8)
I8X16 = VectorType("int8x16_t", I8, fixed_lanes=16)
I16X4 = VectorType("int16x4_t", I16, fixed_lanes=4)
I16X8 = VectorType("int16x8_t", I16, fixed_lanes=8)
I32X4 = VectorType("int32x4_t", I32, fixed_lanes=4)
U16X4 = VectorType("uint16x4_t", U16, fixed_lanes=4)
U32X2 = VectorType("uint32x2_t", U32, fixed_lanes=2)

VI8M2 = VectorType("vint8m2_t", I8, lmul="m2")
VI16M4 = VectorType("vint16m4_t", I16, lmul="m4")
VI32M8 = VectorType("vint32m8_t", I32, lmul="m8")


def _signature(result: ValueType, *parameters: tuple[str, ValueType]) -> FunctionSignature:
    return FunctionSignature(tuple(Parameter(name, type_) for name, type_ in parameters), result)


def _constraint(index: int, *values: int | str) -> ImmediateConstraint:
    return ImmediateConstraint(index, frozenset(values))


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


QS8_VADD_MINMAX_NEON_SPECS: tuple[IntrinsicSpec, ...] = (
    _structural(
        "vdup_n_s8", Architecture.NEON, _signature(I8X8, ("value", I8)),
        OperationShape.BROADCAST, StructuralOp.BROADCAST,
    ),
    _structural(
        "vdupq_n_s8", Architecture.NEON, _signature(I8X16, ("value", I8)),
        OperationShape.BROADCAST, StructuralOp.BROADCAST,
    ),
    _structural(
        "vdupq_n_s16", Architecture.NEON, _signature(I16X8, ("value", I16)),
        OperationShape.BROADCAST, StructuralOp.BROADCAST,
    ),
    _structural(
        "vdupq_n_s32", Architecture.NEON, _signature(I32X4, ("value", I32)),
        OperationShape.BROADCAST, StructuralOp.BROADCAST,
    ),
    _structural(
        "vld1_s8", Architecture.NEON, _signature(I8X8, ("base", CONST_I8_PTR)),
        OperationShape.LOAD, StructuralOp.LOAD,
    ),
    _semantic(
        "vsubl_s8", Architecture.NEON,
        _signature(I16X8, ("left", I8X8), ("right", I8X8)),
        OperationShape.VECTOR_VECTOR, "SALT.Intrinsics.Neon.vsubl_s8",
        (_arg(0), _arg(1)),
    ),
    _structural(
        "vget_low_s16", Architecture.NEON, _signature(I16X4, ("vector", I16X8)),
        OperationShape.EXTRACT, StructuralOp.TAKE_LOW,
    ),
    _structural(
        "vget_high_s16", Architecture.NEON, _signature(I16X4, ("vector", I16X8)),
        OperationShape.EXTRACT, StructuralOp.TAKE_HIGH,
    ),
    _structural(
        "vget_low_s8", Architecture.NEON, _signature(I8X8, ("vector", I8X16)),
        OperationShape.EXTRACT, StructuralOp.TAKE_LOW,
    ),
    _semantic(
        "vmovl_s16", Architecture.NEON, _signature(I32X4, ("vector", I16X4)),
        OperationShape.VECTOR_UNARY, "SALT.Intrinsics.Neon.vmovl_s16", (_arg(0),),
    ),
    _semantic(
        "vmulq_s32", Architecture.NEON,
        _signature(I32X4, ("left", I32X4), ("right", I32X4)),
        OperationShape.VECTOR_VECTOR, "SALT.Intrinsics.Neon.vmulq_s32",
        (_arg(0), _arg(1, OperandTransform.UNBROADCAST)),
    ),
    _semantic(
        "vmlaq_s32", Architecture.NEON,
        _signature(I32X4, ("acc", I32X4), ("left", I32X4), ("right", I32X4)),
        OperationShape.VECTOR_TERNARY, "SALT.Intrinsics.Neon.vmlaq_s32",
        (_arg(0), _arg(1), _arg(2, OperandTransform.UNBROADCAST)),
    ),
    _semantic(
        "vrshlq_s32", Architecture.NEON,
        _signature(I32X4, ("vector", I32X4), ("shift", I32X4)),
        OperationShape.VECTOR_VECTOR, "SALT.Intrinsics.Neon.vrshlq_s32",
        (_arg(0), _arg(1, OperandTransform.NEGATED_UNBROADCAST_TO_NAT)),
    ),
    _semantic(
        "vqmovn_s32", Architecture.NEON, _signature(I16X4, ("vector", I32X4)),
        OperationShape.VECTOR_UNARY, "SALT.Intrinsics.Neon.vqmovn_s32", (_arg(0),),
    ),
    _structural(
        "vcombine_s16", Architecture.NEON,
        _signature(I16X8, ("low", I16X4), ("high", I16X4)),
        OperationShape.CONCATENATE, StructuralOp.CONCATENATE,
    ),
    _semantic(
        "vqaddq_s16", Architecture.NEON,
        _signature(I16X8, ("left", I16X8), ("right", I16X8)),
        OperationShape.VECTOR_VECTOR, "SALT.Intrinsics.Neon.vqaddq_s16",
        (_arg(0), _arg(1, OperandTransform.UNBROADCAST)),
    ),
    _semantic(
        "vqmovn_s16", Architecture.NEON, _signature(I8X8, ("vector", I16X8)),
        OperationShape.VECTOR_UNARY, "SALT.Intrinsics.Neon.vqmovn_s16", (_arg(0),),
    ),
    _structural(
        "vcombine_s8", Architecture.NEON,
        _signature(I8X16, ("low", I8X8), ("high", I8X8)),
        OperationShape.CONCATENATE, StructuralOp.CONCATENATE,
    ),
    _semantic(
        "vmaxq_s8", Architecture.NEON,
        _signature(I8X16, ("left", I8X16), ("right", I8X16)),
        OperationShape.VECTOR_VECTOR, "SALT.Intrinsics.Neon.vmax_s8",
        (_arg(0), _arg(1, OperandTransform.UNBROADCAST)),
    ),
    _semantic(
        "vminq_s8", Architecture.NEON,
        _signature(I8X16, ("left", I8X16), ("right", I8X16)),
        OperationShape.VECTOR_VECTOR, "SALT.Intrinsics.Neon.vmin_s8",
        (_arg(0), _arg(1, OperandTransform.UNBROADCAST)),
    ),
    _structural(
        "vst1q_s8", Architecture.NEON,
        _signature(VOID, ("base", I8_PTR), ("value", I8X16)),
        OperationShape.STORE, StructuralOp.STORE,
    ),
    _semantic(
        "vmax_s8", Architecture.NEON,
        _signature(I8X8, ("left", I8X8), ("right", I8X8)),
        OperationShape.VECTOR_VECTOR, "SALT.Intrinsics.Neon.vmax_s8",
        (_arg(0), _arg(1, OperandTransform.UNBROADCAST)),
    ),
    _semantic(
        "vmin_s8", Architecture.NEON,
        _signature(I8X8, ("left", I8X8), ("right", I8X8)),
        OperationShape.VECTOR_VECTOR, "SALT.Intrinsics.Neon.vmin_s8",
        (_arg(0), _arg(1, OperandTransform.UNBROADCAST)),
    ),
    _structural(
        "vst1_s8", Architecture.NEON,
        _signature(VOID, ("base", I8_PTR), ("value", I8X8)),
        OperationShape.STORE, StructuralOp.STORE,
    ),
    _structural(
        "vreinterpret_u32_s8", Architecture.NEON, _signature(U32X2, ("value", I8X8)),
        OperationShape.REINTERPRET, StructuralOp.BITCAST,
    ),
    _structural(
        "vst1_lane_u32", Architecture.NEON,
        _signature(VOID, ("base", U32_PTR), ("value", U32X2), ("lane", INT)),
        OperationShape.LANE_STORE, StructuralOp.LANE_STORE, _constraint(2, 0),
    ),
    _structural(
        "vext_s8", Architecture.NEON,
        _signature(I8X8, ("left", I8X8), ("right", I8X8), ("offset", INT)),
        OperationShape.SLIDE, StructuralOp.EXTRACT_FROM_CONCAT, _constraint(2, 2, 4),
    ),
    _structural(
        "vreinterpret_u16_s8", Architecture.NEON, _signature(U16X4, ("value", I8X8)),
        OperationShape.REINTERPRET, StructuralOp.BITCAST,
    ),
    _structural(
        "vst1_lane_u16", Architecture.NEON,
        _signature(VOID, ("base", U16_PTR), ("value", U16X4), ("lane", INT)),
        OperationShape.LANE_STORE, StructuralOp.LANE_STORE, _constraint(2, 0),
    ),
    _structural(
        "vst1_lane_s8", Architecture.NEON,
        _signature(VOID, ("base", I8_PTR), ("value", I8X8), ("lane", INT)),
        OperationShape.LANE_STORE, StructuralOp.LANE_STORE, _constraint(2, 0),
    ),
)


QS8_VADD_MINMAX_RVV_SPECS: tuple[IntrinsicSpec, ...] = (
    ScheduleIntrinsic(
        "__riscv_vsetvl_e8m2", Architecture.RVV,
        _signature(SIZE_T, ("avl", SIZE_T)), OperationShape.SCHEDULE,
        ScheduleOp.SET_ACTIVE_LENGTH,
    ),
    _structural(
        "__riscv_vle8_v_i8m2", Architecture.RVV,
        _signature(VI8M2, ("base", CONST_I8_PTR), ("vl", SIZE_T)),
        OperationShape.LOAD, StructuralOp.LOAD,
    ),
    _semantic(
        "__riscv_vwsub_vx_i16m4", Architecture.RVV,
        _signature(VI16M4, ("vector", VI8M2), ("scalar", I8), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR, "SALT.Intrinsics.RVV.vwsub_vx",
        (_arg(0), _arg(1)),
    ),
    _semantic(
        "__riscv_vsext_vf2_i32m8", Architecture.RVV,
        _signature(VI32M8, ("vector", VI16M4), ("vl", SIZE_T)),
        OperationShape.VECTOR_UNARY, "SALT.Intrinsics.RVV.vsext_vf2", (_arg(0),),
    ),
    _semantic(
        "__riscv_vmul_vx_i32m8", Architecture.RVV,
        _signature(VI32M8, ("vector", VI32M8), ("scalar", I32), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR, "SALT.Intrinsics.RVV.vmul_vx",
        (_arg(0), _arg(1)),
    ),
    _semantic(
        "__riscv_vmacc_vx_i32m8", Architecture.RVV,
        _signature(
            VI32M8, ("destination", VI32M8), ("scalar", I32),
            ("source", VI32M8), ("vl", SIZE_T),
        ),
        OperationShape.VECTOR_SCALAR_VECTOR, "SALT.Intrinsics.RVV.vmacc_vx",
        (_arg(0), _arg(1), _arg(2)),
    ),
    _semantic(
        "__riscv_vssra_vx_i32m8", Architecture.RVV,
        _signature(
            VI32M8, ("vector", VI32M8), ("shift", SIZE_T),
            ("vxrm", UINT), ("vl", SIZE_T),
        ),
        OperationShape.VECTOR_SCALAR, "SALT.Intrinsics.RVV.vssra_vx_rnu",
        (_arg(0), _arg(1, OperandTransform.TO_NAT)),
        _constraint(2, 0),
    ),
    _semantic(
        "__riscv_vnclip_wx_i16m4", Architecture.RVV,
        _signature(
            VI16M4, ("vector", VI32M8), ("shift", SIZE_T),
            ("vxrm", UINT), ("vl", SIZE_T),
        ),
        OperationShape.VECTOR_UNARY, "SALT.Intrinsics.RVV.vnclip_wx_i16", (_arg(0),),
        _constraint(1, 0), _constraint(2, 2),
    ),
    _semantic(
        "__riscv_vsadd_vx_i16m4", Architecture.RVV,
        _signature(VI16M4, ("vector", VI16M4), ("scalar", I16), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR, "SALT.Intrinsics.RVV.vsadd_vx",
        (_arg(0), _arg(1)),
    ),
    _semantic(
        "__riscv_vnclip_wx_i8m2", Architecture.RVV,
        _signature(
            VI8M2, ("vector", VI16M4), ("shift", SIZE_T),
            ("vxrm", UINT), ("vl", SIZE_T),
        ),
        OperationShape.VECTOR_UNARY, "SALT.Intrinsics.RVV.vnclip_wx_i8", (_arg(0),),
        _constraint(1, 0), _constraint(2, 2),
    ),
    _semantic(
        "__riscv_vmax_vx_i8m2", Architecture.RVV,
        _signature(VI8M2, ("vector", VI8M2), ("scalar", I8), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR, "SALT.Intrinsics.RVV.vmax_vx",
        (_arg(0), _arg(1)),
    ),
    _semantic(
        "__riscv_vmin_vx_i8m2", Architecture.RVV,
        _signature(VI8M2, ("vector", VI8M2), ("scalar", I8), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR, "SALT.Intrinsics.RVV.vmin_vx",
        (_arg(0), _arg(1)),
    ),
    _structural(
        "__riscv_vse8_v_i8m2", Architecture.RVV,
        _signature(VOID, ("base", I8_PTR), ("value", VI8M2), ("vl", SIZE_T)),
        OperationShape.STORE, StructuralOp.STORE,
    ),
)


def build_registry(specs: Iterable[IntrinsicSpec]) -> Mapping[str, IntrinsicSpec]:
    """Build an immutable exact-token table and reject duplicate definitions."""

    result: dict[str, IntrinsicSpec] = {}
    for spec in specs:
        if spec.spelling in result:
            raise DuplicateIntrinsicError(f"duplicate intrinsic: {spec.spelling}")
        result[spec.spelling] = spec
    return MappingProxyType(result)


QS8_VADD_MINMAX_SPECS = QS8_VADD_MINMAX_NEON_SPECS + QS8_VADD_MINMAX_RVV_SPECS
QS8_VADD_MINMAX_REGISTRY = build_registry(QS8_VADD_MINMAX_SPECS)


def lookup_intrinsic(
    spelling: str,
    architecture: Architecture | None = None,
) -> IntrinsicSpec:
    """Return one reviewed exact-spelling entry or reject the call.

    Deliberately absent: trimming, case folding, suffix parsing, prefix matching,
    and fallback to a similarly named intrinsic.
    """

    try:
        spec = QS8_VADD_MINMAX_REGISTRY[spelling]
    except (KeyError, TypeError) as error:
        raise UnknownIntrinsicError(f"unsupported intrinsic: {spelling!r}") from error
    if architecture is not None and spec.architecture is not architecture:
        raise ArchitectureMismatchError(
            f"{spelling!r} is registered for {spec.architecture.value}, "
            f"not {architecture.value}"
        )
    return spec


def resolve_call(
    spelling: str,
    operands: tuple[TypedOperand, ...],
    architecture: Architecture | None = None,
) -> IntrinsicNode:
    """Exact lookup followed by typed and immediate-constrained node creation."""

    return make_node(lookup_intrinsic(spelling, architecture), operands)
