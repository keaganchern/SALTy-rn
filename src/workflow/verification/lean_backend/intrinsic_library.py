"""Program-independent exact intrinsic descriptors for the elementwise compiler.

Unlike the historical kernel catalogs, this library is organized by reusable
typed operation families.  Adding an entry here makes one exact C signature
available to every structurally compatible program; it does not register a
program or select a proof target.
"""

from __future__ import annotations

from .registry import INT, SIZE_T, VOID
from .schema import (
    Architecture,
    FloatingType,
    FunctionSignature,
    ImmediateConstraint,
    IntrinsicSpec,
    OperationShape,
    Parameter,
    PointerType,
    ScheduleIntrinsic,
    ScheduleOp,
    StructuralIntrinsic,
    StructuralOp,
    ValueType,
    VectorType,
    render_clang_type,
)


F32 = FloatingType("float", 32)
CONST_F32_PTR = PointerType(F32, const=True)
F32_PTR = PointerType(F32)
F32X2 = VectorType("float32x2_t", F32, fixed_lanes=2)
F32X4 = VectorType("float32x4_t", F32, fixed_lanes=4)
VF32M8 = VectorType("vfloat32m8_t", F32, lmul="m8")


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
)


def render_elementwise_shared_facade() -> str:
    """Render the parse-only C declarations directly from the typed library."""

    vectors: dict[str, VectorType] = {}
    for spec in ELEMENTWISE_SHARED_SPECS:
        for value_type in (spec.signature.result, *spec.signature.argument_types):
            if isinstance(value_type, VectorType):
                vectors[value_type.c_spelling] = value_type
    lines = [
        "#ifndef SALT_ELEMENTWISE_SHARED_FACADE_H",
        "#define SALT_ELEMENTWISE_SHARED_FACADE_H",
        "",
        "typedef __SIZE_TYPE__ size_t;",
        "",
        "#define NULL ((void*) 0)",
        "#define assert(condition) ((void) 0)",
        "",
    ]
    for spelling in sorted(vectors):
        lines.append(f"typedef struct {{ unsigned char opaque[1]; }} {spelling};")
    lines.append("")
    for spec in sorted(
        ELEMENTWISE_SHARED_SPECS,
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
