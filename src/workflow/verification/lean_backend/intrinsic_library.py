"""Program-independent exact intrinsic descriptors for the elementwise compiler.

Unlike the historical kernel catalogs, this library is organized by reusable
typed operation families.  Adding an entry here makes one exact C signature
available to every structurally compatible program; it does not register a
program or select a proof target.
"""

from __future__ import annotations

from .registry import I8, I16, I32, INT, SIZE_T, U16, U32, VOID
from .schema import (
    Architecture,
    FloatingType,
    FunctionSignature,
    ImmediateConstraint,
    IntrinsicSpec,
    LeanArgument,
    OperationShape,
    OperandTransform,
    Parameter,
    PointerType,
    ScheduleIntrinsic,
    ScheduleOp,
    SemanticIntrinsic,
    ScalarType,
    Signedness,
    StructuralIntrinsic,
    StructuralOp,
    ValueType,
    VectorType,
    render_clang_type,
)


F32 = FloatingType("float", 32)
U8 = ScalarType("uint8_t", 8, Signedness.UNSIGNED)
CONST_F32_PTR = PointerType(F32, const=True)
F32_PTR = PointerType(F32)
U16_PTR = PointerType(U16)
F32X2 = VectorType("float32x2_t", F32, fixed_lanes=2)
F32X4 = VectorType("float32x4_t", F32, fixed_lanes=4)
I32X4 = VectorType("int32x4_t", I32, fixed_lanes=4)
I8X8 = VectorType("int8x8_t", I8, fixed_lanes=8)
I16X4 = VectorType("int16x4_t", I16, fixed_lanes=4)
I16X8 = VectorType("int16x8_t", I16, fixed_lanes=8)
U8X8 = VectorType("uint8x8_t", U8, fixed_lanes=8)
U16X8 = VectorType("uint16x8_t", U16, fixed_lanes=8)
U16X4 = VectorType("uint16x4_t", U16, fixed_lanes=4)
U32X2 = VectorType("uint32x2_t", U32, fixed_lanes=2)
U32X4 = VectorType("uint32x4_t", U32, fixed_lanes=4)
VF32M8 = VectorType("vfloat32m8_t", F32, lmul="m8")
VI8M2 = VectorType("vint8m2_t", I8, lmul="m2")
VI16M4 = VectorType("vint16m4_t", I16, lmul="m4")
VI32M8 = VectorType("vint32m8_t", I32, lmul="m8")
VU8M2 = VectorType("vuint8m2_t", U8, lmul="m2")
VU16M4 = VectorType("vuint16m4_t", U16, lmul="m4")
VU32M8 = VectorType("vuint32m8_t", U32, lmul="m8")
VBOOL4 = VectorType("vbool4_t", U32, lmul="mf8")


def _signature(
    result: ValueType, *parameters: tuple[str, ValueType]
) -> FunctionSignature:
    return FunctionSignature(
        tuple(Parameter(name, value_type) for name, value_type in parameters),
        result,
    )


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
    *argument_indices: int | LeanArgument,
    immediate_constraints: tuple[ImmediateConstraint, ...] = (),
) -> SemanticIntrinsic:
    return SemanticIntrinsic(
        spelling,
        architecture,
        signature,
        shape,
        lean_name,
        tuple(
            index if isinstance(index, LeanArgument) else LeanArgument(index)
            for index in argument_indices
        ),
        immediate_constraints,
    )


# First high-fanout batch: value-preserving F32 loads, stores, half extraction,
# and RVV active-length selection.  Arithmetic semantics are intentionally not
# included in this structural batch.
ELEMENTWISE_SHARED_SPECS: tuple[IntrinsicSpec, ...] = (
    _structural(
        "vget_high_f32",
        Architecture.NEON,
        _signature(F32X2, ("vector", F32X4)),
        OperationShape.EXTRACT,
        StructuralOp.TAKE_HIGH,
    ),
    _structural(
        "vget_low_f32",
        Architecture.NEON,
        _signature(F32X2, ("vector", F32X4)),
        OperationShape.EXTRACT,
        StructuralOp.TAKE_LOW,
    ),
    _structural(
        "vld1q_f32",
        Architecture.NEON,
        _signature(F32X4, ("base", CONST_F32_PTR)),
        OperationShape.LOAD,
        StructuralOp.LOAD,
    ),
    _structural(
        "vld1q_dup_f32",
        Architecture.NEON,
        _signature(F32X4, ("base", CONST_F32_PTR)),
        OperationShape.LOAD,
        StructuralOp.LOAD_BROADCAST,
    ),
    _structural(
        "vst1_f32",
        Architecture.NEON,
        _signature(VOID, ("base", F32_PTR), ("value", F32X2)),
        OperationShape.STORE,
        StructuralOp.STORE,
    ),
    _structural(
        "vst1_lane_f32",
        Architecture.NEON,
        _signature(
            VOID,
            ("base", F32_PTR),
            ("value", F32X2),
            ("lane", INT),
        ),
        OperationShape.LANE_STORE,
        StructuralOp.LANE_STORE,
        ImmediateConstraint(2, frozenset({0, 1})),
    ),
    _structural(
        "vst1q_f32",
        Architecture.NEON,
        _signature(VOID, ("base", F32_PTR), ("value", F32X4)),
        OperationShape.STORE,
        StructuralOp.STORE,
    ),
    ScheduleIntrinsic(
        "__riscv_vsetvl_e32m8",
        Architecture.RVV,
        _signature(SIZE_T, ("avl", SIZE_T)),
        OperationShape.SCHEDULE,
        ScheduleOp.SET_ACTIVE_LENGTH,
    ),
    _structural(
        "__riscv_vle32_v_f32m8",
        Architecture.RVV,
        _signature(VF32M8, ("base", CONST_F32_PTR), ("vl", SIZE_T)),
        OperationShape.LOAD,
        StructuralOp.LOAD,
    ),
    _structural(
        "__riscv_vse32_v_f32m8",
        Architecture.RVV,
        _signature(
            VOID,
            ("base", F32_PTR),
            ("value", VF32M8),
            ("vl", SIZE_T),
        ),
        OperationShape.STORE,
        StructuralOp.STORE,
    ),
    _structural(
        "vdupq_n_f32",
        Architecture.NEON,
        _signature(F32X4, ("value", F32)),
        OperationShape.BROADCAST,
        StructuralOp.BROADCAST,
    ),
    _semantic(
        "vabsq_f32",
        Architecture.NEON,
        _signature(F32X4, ("value", F32X4)),
        OperationShape.VECTOR_UNARY,
        "SALT.Intrinsics.Neon.vabsq_f32",
        0,
    ),
    _semantic(
        "vaddq_f32",
        Architecture.NEON,
        _signature(F32X4, ("left", F32X4), ("right", F32X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vaddq_f32",
        0,
        1,
    ),
    _semantic(
        "vdivq_f32",
        Architecture.NEON,
        _signature(F32X4, ("left", F32X4), ("right", F32X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vdivq_f32",
        0,
        1,
    ),
    _semantic(
        "vmulq_f32",
        Architecture.NEON,
        _signature(F32X4, ("left", F32X4), ("right", F32X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vmulq_f32",
        0,
        1,
    ),
    _semantic(
        "vsqrtq_f32",
        Architecture.NEON,
        _signature(F32X4, ("value", F32X4)),
        OperationShape.VECTOR_UNARY,
        "SALT.Intrinsics.Neon.vsqrtq_f32",
        0,
    ),
    _semantic(
        "vsubq_f32",
        Architecture.NEON,
        _signature(F32X4, ("left", F32X4), ("right", F32X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vsubq_f32",
        0,
        1,
    ),
    _structural(
        "vmovq_n_s32",
        Architecture.NEON,
        _signature(I32X4, ("value", I32)),
        OperationShape.BROADCAST,
        StructuralOp.BROADCAST,
    ),
    _semantic(
        "vcltq_s32",
        Architecture.NEON,
        _signature(U32X4, ("left", I32X4), ("right", I32X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vcltq_s32",
        0,
        1,
    ),
    _structural(
        "vreinterpretq_s32_f32",
        Architecture.NEON,
        _signature(I32X4, ("value", F32X4)),
        OperationShape.REINTERPRET,
        StructuralOp.BITCAST,
    ),
    _semantic(
        "vbslq_f32",
        Architecture.NEON,
        _signature(
            F32X4,
            ("mask", U32X4),
            ("if_true", F32X4),
            ("if_false", F32X4),
        ),
        OperationShape.VECTOR_TERNARY,
        "SALT.Intrinsics.Neon.vbslq_f32",
        0,
        1,
        2,
    ),
    _structural(
        "vmovq_n_u32",
        Architecture.NEON,
        _signature(U32X4, ("value", U32)),
        OperationShape.BROADCAST,
        StructuralOp.BROADCAST,
    ),
    _structural(
        "vreinterpretq_f32_u32",
        Architecture.NEON,
        _signature(F32X4, ("value", U32X4)),
        OperationShape.REINTERPRET,
        StructuralOp.BITCAST,
    ),
    _structural(
        "vreinterpretq_u32_f32",
        Architecture.NEON,
        _signature(U32X4, ("value", F32X4)),
        OperationShape.REINTERPRET,
        StructuralOp.BITCAST,
    ),
    _semantic(
        "vcaltq_f32",
        Architecture.NEON,
        _signature(U32X4, ("left", F32X4), ("right", F32X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vcaltq_f32",
        0,
        1,
    ),
    _semantic(
        "vorrq_u32",
        Architecture.NEON,
        _signature(U32X4, ("left", U32X4), ("right", U32X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vorrq_u32",
        0,
        1,
    ),
    _semantic(
        "__riscv_vfabs_v_f32m8",
        Architecture.RVV,
        _signature(VF32M8, ("value", VF32M8), ("vl", SIZE_T)),
        OperationShape.VECTOR_UNARY,
        "SALT.Intrinsics.RVV.vfabs_v_f32",
        0,
    ),
    _semantic(
        "__riscv_vfadd_vv_f32m8",
        Architecture.RVV,
        _signature(
            VF32M8, ("left", VF32M8), ("right", VF32M8), ("vl", SIZE_T)
        ),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.RVV.vfadd_vv_f32",
        0,
        1,
    ),
    _semantic(
        "__riscv_vfdiv_vv_f32m8",
        Architecture.RVV,
        _signature(
            VF32M8, ("left", VF32M8), ("right", VF32M8), ("vl", SIZE_T)
        ),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.RVV.vfdiv_vv_f32",
        0,
        1,
    ),
    _semantic(
        "__riscv_vfmul_vf_f32m8",
        Architecture.RVV,
        _signature(VF32M8, ("vector", VF32M8), ("scalar", F32), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vfmul_vf_f32",
        0,
        1,
    ),
    _semantic(
        "__riscv_vfmul_vv_f32m8",
        Architecture.RVV,
        _signature(
            VF32M8, ("left", VF32M8), ("right", VF32M8), ("vl", SIZE_T)
        ),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.RVV.vfmul_vv_f32",
        0,
        1,
    ),
    _semantic(
        "__riscv_vfsqrt_v_f32m8",
        Architecture.RVV,
        _signature(VF32M8, ("value", VF32M8), ("vl", SIZE_T)),
        OperationShape.VECTOR_UNARY,
        "SALT.Intrinsics.RVV.vfsqrt_v_f32",
        0,
    ),
    _semantic(
        "__riscv_vfsub_vv_f32m8",
        Architecture.RVV,
        _signature(
            VF32M8, ("left", VF32M8), ("right", VF32M8), ("vl", SIZE_T)
        ),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.RVV.vfsub_vv_f32",
        0,
        1,
    ),
    _structural(
        "__riscv_vreinterpret_v_f32m8_i32m8",
        Architecture.RVV,
        _signature(VI32M8, ("value", VF32M8)),
        OperationShape.REINTERPRET,
        StructuralOp.BITCAST,
    ),
    _semantic(
        "__riscv_vmslt_vx_i32m8_b4",
        Architecture.RVV,
        _signature(
            VBOOL4, ("vector", VI32M8), ("scalar", I32), ("vl", SIZE_T)
        ),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vmslt_vx_i32",
        0,
        1,
    ),
    _semantic(
        "__riscv_vmerge_vvm_f32m8",
        Architecture.RVV,
        _signature(
            VF32M8,
            ("if_false", VF32M8),
            ("if_true", VF32M8),
            ("mask", VBOOL4),
            ("vl", SIZE_T),
        ),
        OperationShape.VECTOR_TERNARY,
        "SALT.Intrinsics.RVV.vmerge_vvm_f32",
        0,
        1,
        2,
    ),
    _semantic(
        "__riscv_vfadd_vf_f32m8",
        Architecture.RVV,
        _signature(VF32M8, ("vector", VF32M8), ("scalar", F32), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vfadd_vf_f32",
        0,
        1,
    ),
    _semantic(
        "__riscv_vfsub_vf_f32m8",
        Architecture.RVV,
        _signature(VF32M8, ("vector", VF32M8), ("scalar", F32), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vfsub_vf_f32",
        0,
        1,
    ),
    _semantic(
        "__riscv_vmfgt_vf_f32m8_b4",
        Architecture.RVV,
        _signature(VBOOL4, ("vector", VF32M8), ("scalar", F32), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vmfgt_vf_f32",
        0,
        1,
    ),
    _semantic(
        "__riscv_vmfne_vv_f32m8_b4",
        Architecture.RVV,
        _signature(
            VBOOL4, ("left", VF32M8), ("right", VF32M8), ("vl", SIZE_T)
        ),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.RVV.vmfne_vv_f32",
        0,
        1,
    ),
    _semantic(
        "__riscv_vfsgnj_vv_f32m8",
        Architecture.RVV,
        _signature(
            VF32M8, ("magnitude", VF32M8), ("sign", VF32M8), ("vl", SIZE_T)
        ),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.RVV.vfsgnj_vv_f32",
        0,
        1,
    ),
    _semantic(
        "__riscv_vor_vx_u32m8",
        Architecture.RVV,
        _signature(VU32M8, ("vector", VU32M8), ("scalar", U32), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vor_vx_u32",
        0,
        1,
    ),
    _structural(
        "__riscv_vreinterpret_v_f32m8_u32m8",
        Architecture.RVV,
        _signature(VU32M8, ("value", VF32M8)),
        OperationShape.REINTERPRET,
        StructuralOp.BITCAST,
    ),
    _structural(
        "__riscv_vreinterpret_v_u32m8_f32m8",
        Architecture.RVV,
        _signature(VF32M8, ("value", VU32M8)),
        OperationShape.REINTERPRET,
        StructuralOp.BITCAST,
    ),
    _semantic(
        "vaddw_s8",
        Architecture.NEON,
        _signature(I16X8, ("wide", I16X8), ("narrow", I8X8)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vaddw_s8",
        0,
        1,
    ),
    _semantic(
        "vaddw_u8",
        Architecture.NEON,
        _signature(U16X8, ("wide", U16X8), ("narrow", U8X8)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vaddw_u8",
        0,
        1,
    ),
    _semantic(
        "vcvtq_f32_s32",
        Architecture.NEON,
        _signature(F32X4, ("value", I32X4)),
        OperationShape.VECTOR_UNARY,
        "SALT.Intrinsics.Neon.vcvtq_f32_s32",
        0,
    ),
    _semantic(
        "vmull_s16",
        Architecture.NEON,
        _signature(I32X4, ("left", I16X4), ("right", I16X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vmull_s16",
        0,
        1,
    ),
    _semantic(
        "vqmovn_high_s32",
        Architecture.NEON,
        _signature(I16X8, ("low", I16X4), ("high", I32X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vqmovn_high_s32",
        0,
        1,
    ),
    _semantic(
        "vqsubq_s32",
        Architecture.NEON,
        _signature(I32X4, ("left", I32X4), ("right", I32X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vqsubq_s32",
        0,
        1,
    ),
    _structural(
        "vreinterpretq_u16_s16",
        Architecture.NEON,
        _signature(U16X8, ("value", I16X8)),
        OperationShape.REINTERPRET,
        StructuralOp.BITCAST,
    ),
    _semantic(
        "__riscv_vsub_vx_i16m4",
        Architecture.RVV,
        _signature(VI16M4, ("value", VI16M4), ("scalar", I16), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vsub_vx_i16",
        0,
        1,
    ),
    _semantic(
        "__riscv_vadd_vx_u16m4",
        Architecture.RVV,
        _signature(VU16M4, ("value", VU16M4), ("scalar", U16), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vadd_vx_u16",
        0,
        1,
    ),
    _semantic(
        "__riscv_vzext_vf2_u16m4",
        Architecture.RVV,
        _signature(VU16M4, ("value", VU8M2), ("vl", SIZE_T)),
        OperationShape.VECTOR_UNARY,
        "SALT.Intrinsics.RVV.vzext_vf2_u16",
        0,
    ),
    _semantic(
        "__riscv_vfcvt_f_x_v_f32m8",
        Architecture.RVV,
        _signature(VF32M8, ("value", VI32M8), ("vl", SIZE_T)),
        OperationShape.VECTOR_UNARY,
        "SALT.Intrinsics.RVV.vfcvt_f_x_v_f32",
        0,
    ),
    _semantic(
        "__riscv_vfcvt_x_f_v_i32m8",
        Architecture.RVV,
        _signature(VI32M8, ("value", VF32M8), ("vl", SIZE_T)),
        OperationShape.VECTOR_UNARY,
        "SALT.Intrinsics.RVV.vfcvt_x_f_v_i32_rne",
        0,
    ),
    _semantic(
        "__riscv_vadd_vx_i32m8",
        Architecture.RVV,
        _signature(VI32M8, ("value", VI32M8), ("scalar", I32), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vadd_vx_i32",
        0,
        1,
    ),
    _structural(
        "vdupq_n_u16",
        Architecture.NEON,
        _signature(U16X8, ("value", U16)),
        OperationShape.BROADCAST,
        StructuralOp.BROADCAST,
    ),
    _structural(
        "vdupq_n_u32",
        Architecture.NEON,
        _signature(U32X4, ("value", U32)),
        OperationShape.BROADCAST,
        StructuralOp.BROADCAST,
    ),
    _semantic(
        "vaddq_u32",
        Architecture.NEON,
        _signature(U32X4, ("left", U32X4), ("right", U32X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vadd_u32",
        0,
        1,
    ),
    _semantic(
        "vcgtq_u32",
        Architecture.NEON,
        _signature(U32X4, ("left", U32X4), ("right", U32X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vcgt_u32",
        0,
        1,
    ),
    _semantic(
        "vandq_u32",
        Architecture.NEON,
        _signature(U32X4, ("left", U32X4), ("right", U32X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vand_u32",
        0,
        1,
    ),
    _semantic(
        "vmaxq_u32",
        Architecture.NEON,
        _signature(U32X4, ("left", U32X4), ("right", U32X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vmax_u32",
        0,
        1,
    ),
    _semantic(
        "vmovn_u32",
        Architecture.NEON,
        _signature(U16X4, ("value", U32X4)),
        OperationShape.VECTOR_UNARY,
        "SALT.Intrinsics.Neon.vmovn_u32",
        0,
    ),
    _structural(
        "vcombine_u16",
        Architecture.NEON,
        _signature(U16X8, ("low", U16X4), ("high", U16X4)),
        OperationShape.CONCATENATE,
        StructuralOp.CONCATENATE,
    ),
    _semantic(
        "vshrn_n_u32",
        Architecture.NEON,
        _signature(U16X4, ("value", U32X4), ("shift", INT)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.Neon.vshrn_n_u32",
        0,
        LeanArgument(1, OperandTransform.TO_NAT),
        immediate_constraints=(
            ImmediateConstraint(
                1,
                frozenset({13, 16}),
                erased_from_semantics=False,
            ),
        ),
    ),
    _semantic(
        "vandq_u16",
        Architecture.NEON,
        _signature(U16X8, ("left", U16X8), ("right", U16X8)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vand_u16",
        0,
        1,
    ),
    _semantic(
        "vaddq_u16",
        Architecture.NEON,
        _signature(U16X8, ("left", U16X8), ("right", U16X8)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vadd_u16",
        0,
        1,
    ),
    _semantic(
        "vbslq_u16",
        Architecture.NEON,
        _signature(U16X8, ("mask", U16X8), ("if_true", U16X8), ("if_false", U16X8)),
        OperationShape.VECTOR_TERNARY,
        "SALT.Intrinsics.Neon.vbsl_u16",
        0,
        1,
        2,
    ),
    _semantic(
        "vorrq_u16",
        Architecture.NEON,
        _signature(U16X8, ("left", U16X8), ("right", U16X8)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vorr_u16",
        0,
        1,
    ),
    _structural(
        "vst1q_u16",
        Architecture.NEON,
        _signature(VOID, ("base", U16_PTR), ("value", U16X8)),
        OperationShape.STORE,
        StructuralOp.STORE,
    ),
    _structural(
        "vget_low_u16",
        Architecture.NEON,
        _signature(U16X4, ("value", U16X8)),
        OperationShape.EXTRACT,
        StructuralOp.TAKE_LOW,
    ),
    _semantic(
        "vand_u16",
        Architecture.NEON,
        _signature(U16X4, ("left", U16X4), ("right", U16X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vand_u16",
        0,
        1,
    ),
    _semantic(
        "vadd_u16",
        Architecture.NEON,
        _signature(U16X4, ("left", U16X4), ("right", U16X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vadd_u16",
        0,
        1,
    ),
    _semantic(
        "vbsl_u16",
        Architecture.NEON,
        _signature(U16X4, ("mask", U16X4), ("if_true", U16X4), ("if_false", U16X4)),
        OperationShape.VECTOR_TERNARY,
        "SALT.Intrinsics.Neon.vbsl_u16",
        0,
        1,
        2,
    ),
    _semantic(
        "vorr_u16",
        Architecture.NEON,
        _signature(U16X4, ("left", U16X4), ("right", U16X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vorr_u16",
        0,
        1,
    ),
    _structural(
        "vst1_u16",
        Architecture.NEON,
        _signature(VOID, ("base", U16_PTR), ("value", U16X4)),
        OperationShape.STORE,
        StructuralOp.STORE,
    ),
    _structural(
        "vreinterpret_u32_u16",
        Architecture.NEON,
        _signature(U32X2, ("value", U16X4)),
        OperationShape.REINTERPRET,
        StructuralOp.BITCAST,
    ),
    _structural(
        "vext_u16",
        Architecture.NEON,
        _signature(U16X4, ("left", U16X4), ("right", U16X4), ("offset", INT)),
        OperationShape.SLIDE,
        StructuralOp.EXTRACT_FROM_CONCAT,
        ImmediateConstraint(2, frozenset({2})),
    ),
    _structural(
        "vst1_lane_u16",
        Architecture.NEON,
        _signature(VOID, ("base", U16_PTR), ("value", U16X4), ("lane", INT)),
        OperationShape.LANE_STORE,
        StructuralOp.LANE_STORE,
        ImmediateConstraint(2, frozenset({0, 1, 2, 3})),
    ),
    _semantic(
        "__riscv_vadd_vx_u32m8",
        Architecture.RVV,
        _signature(VU32M8, ("value", VU32M8), ("scalar", U32), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vadd_vx_u32",
        0,
        1,
    ),
    _semantic(
        "__riscv_vmsgtu_vx_u32m8_b4",
        Architecture.RVV,
        _signature(VBOOL4, ("value", VU32M8), ("scalar", U32), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vmsgtu_vx_u32",
        0,
        1,
    ),
    _semantic(
        "__riscv_vand_vx_u32m8",
        Architecture.RVV,
        _signature(VU32M8, ("value", VU32M8), ("scalar", U32), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vand_vx_u32",
        0,
        1,
    ),
    _semantic(
        "__riscv_vmaxu_vx_u32m8",
        Architecture.RVV,
        _signature(VU32M8, ("value", VU32M8), ("scalar", U32), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vmaxu_vx_u32",
        0,
        1,
    ),
    _semantic(
        "__riscv_vnsrl_wx_u16m4",
        Architecture.RVV,
        _signature(VU16M4, ("value", VU32M8), ("shift", SIZE_T), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vnsrl_wx_u16",
        0,
        LeanArgument(1, OperandTransform.TO_NAT),
    ),
    _semantic(
        "__riscv_vand_vx_u16m4",
        Architecture.RVV,
        _signature(VU16M4, ("value", VU16M4), ("scalar", U16), ("vl", SIZE_T)),
        OperationShape.VECTOR_SCALAR,
        "SALT.Intrinsics.RVV.vand_vx_u16",
        0,
        1,
    ),
    _semantic(
        "__riscv_vadd_vv_u16m4",
        Architecture.RVV,
        _signature(VU16M4, ("left", VU16M4), ("right", VU16M4), ("vl", SIZE_T)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.RVV.vadd_vv_u16",
        0,
        1,
    ),
    _semantic(
        "__riscv_vmerge_vxm_u16m4",
        Architecture.RVV,
        _signature(VU16M4, ("base", VU16M4), ("replacement", U16), ("mask", VBOOL4), ("vl", SIZE_T)),
        OperationShape.VECTOR_TERNARY,
        "SALT.Intrinsics.RVV.vmerge_vxm_u16",
        0,
        1,
        2,
    ),
    _semantic(
        "__riscv_vor_vv_u16m4",
        Architecture.RVV,
        _signature(VU16M4, ("left", VU16M4), ("right", VU16M4), ("vl", SIZE_T)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.RVV.vor_vv_u16",
        0,
        1,
    ),
    _structural(
        "__riscv_vse16_v_u16m4",
        Architecture.RVV,
        _signature(VOID, ("base", U16_PTR), ("value", VU16M4), ("vl", SIZE_T)),
        OperationShape.STORE,
        StructuralOp.STORE,
    ),
    _semantic(
        "vmaxq_f32",
        Architecture.NEON,
        _signature(F32X4, ("left", F32X4), ("right", F32X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vmaxq_f32",
        0,
        1,
    ),
    _semantic(
        "vminq_f32",
        Architecture.NEON,
        _signature(F32X4, ("left", F32X4), ("right", F32X4)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.Neon.vminq_f32",
        0,
        1,
    ),
    _semantic(
        "__riscv_vfmax_vv_f32m8",
        Architecture.RVV,
        _signature(VF32M8, ("left", VF32M8), ("right", VF32M8), ("vl", SIZE_T)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.RVV.vfmax_vv_f32",
        0,
        1,
    ),
    _semantic(
        "__riscv_vfmin_vv_f32m8",
        Architecture.RVV,
        _signature(VF32M8, ("left", VF32M8), ("right", VF32M8), ("vl", SIZE_T)),
        OperationShape.VECTOR_VECTOR,
        "SALT.Intrinsics.RVV.vfmin_vv_f32",
        0,
        1,
    ),
)


def render_elementwise_shared_facade() -> str:
    """Render the parse-only C declarations directly from the typed library."""

    # Facades are parser inputs, not semantic registries.  The shared facade
    # therefore declares every already-configured reusable spelling as well as
    # the new family descriptors.  Semantic resolution still happens later
    # against the provenance-preserving canonical index.
    from .registry import QS8_VADD_MINMAX_SPECS
    from .scaleup_catalog import SCALEUP_CATALOGS

    facade_specs = list(ELEMENTWISE_SHARED_SPECS) + list(QS8_VADD_MINMAX_SPECS)
    for catalog in SCALEUP_CATALOGS.values():
        facade_specs.extend(catalog.specs)
    declarations: dict[str, IntrinsicSpec] = {}
    for spec in facade_specs:
        previous = declarations.setdefault(spec.spelling, spec)
        if previous.signature != spec.signature:
            raise ValueError(
                f"shared facade cannot declare two C signatures for {spec.spelling}"
            )

    vectors: dict[str, VectorType] = {}
    for spec in declarations.values():
        for value_type in (spec.signature.result, *spec.signature.argument_types):
            if isinstance(value_type, VectorType):
                vectors[value_type.c_spelling] = value_type
    lines = [
        "#ifndef SALT_ELEMENTWISE_SHARED_FACADE_H",
        "#define SALT_ELEMENTWISE_SHARED_FACADE_H",
        "",
        "typedef __SIZE_TYPE__ size_t;",
        "typedef __INT8_TYPE__ int8_t;",
        "typedef __INT16_TYPE__ int16_t;",
        "typedef __INT32_TYPE__ int32_t;",
        "typedef __UINT8_TYPE__ uint8_t;",
        "typedef __UINT16_TYPE__ uint16_t;",
        "typedef __UINT32_TYPE__ uint32_t;",
        "",
        "#define NULL ((void*) 0)",
        "#define assert(condition) ((void) 0)",
        "#define XNN_OOB_READS",
        "#define XNN_LIKELY(condition) (condition)",
        "#define XNN_UNLIKELY(condition) (condition)",
        "#define INT32_C(value) value",
        "#define UINT16_C(value) value",
        "#define UINT32_C(value) value##U",
        "#define __RISCV_VXRM_RDN 2",
        "#if defined(__aarch64__)",
        "#define XNN_ARCH_ARM64 1",
        "#else",
        "#define XNN_ARCH_ARM64 0",
        "#endif",
        "#define XNN_ARCH_ARM 0",
        "",
        "struct xnn_f32_default_params { char opaque; };",
        "struct xnn_f32_lrelu_params { struct { float slope; } scalar; };",
        "struct xnn_qs8_f32_cvt_params { struct { int32_t zero_point; float scale; } scalar; };",
        "struct xnn_qu8_f32_cvt_params { struct { int32_t zero_point; float scale; } scalar; };",
        "union xnn_qs8_mul_minmax_params { struct { int8_t a_zero_point; int8_t b_zero_point; float scale; int16_t output_zero_point; int8_t output_min; int8_t output_max; } scalar; };",
        "",
    ]
    for spelling in sorted(vectors):
        lines.append(f"typedef struct {{ unsigned char opaque[1]; }} {spelling};")
    lines.append("")
    for spec in sorted(
        declarations.values(),
        key=lambda item: (item.architecture.value, item.spelling),
    ):
        parameters = ", ".join(
            f"{render_clang_type(parameter.type)} {parameter.name}"
            for parameter in spec.signature.parameters
        )
        lines.append(
            f"{render_clang_type(spec.signature.result)} {spec.spelling}({parameters});"
        )
    lines.extend(("", "#endif", ""))
    return "\n".join(lines)
