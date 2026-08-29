"""Pure-Python schema for the restricted C-intrinsic to Lean frontend.

The schema deliberately keeps three kinds of operation separate:

* structural nodes describe vector construction, memory access, and rearrangement;
* semantic nodes denote an existing, reviewed SALT Lean definition; and
* schedule nodes describe control decisions such as RVV ``vsetvl``.

No solver object is stored here.  In particular, this module must remain usable
without cvc5 or any other symbolic execution library installed.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TypeAlias


class SchemaError(ValueError):
    """Base class for fail-closed schema validation errors."""


class SignatureMismatchError(SchemaError):
    """A call does not match the exact registered C signature."""


class ImmediateConstraintError(SchemaError):
    """A required immediate or named mode is absent or unsupported."""


class Architecture(str, Enum):
    NEON = "neon"
    RVV = "rvv"


class NodeKind(str, Enum):
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"
    SCHEDULE = "schedule"


class Signedness(str, Enum):
    SIGNED = "signed"
    UNSIGNED = "unsigned"


class OperationShape(str, Enum):
    """Source-level call shape, independent of the eventual Lean rendering."""

    BROADCAST = "broadcast"
    LOAD = "load"
    STORE = "store"
    LANE_STORE = "lane_store"
    EXTRACT = "extract"
    CONCATENATE = "concatenate"
    REINTERPRET = "reinterpret"
    SLIDE = "slide"
    VECTOR_UNARY = "vector_unary"
    VECTOR_VECTOR = "vector_vector"
    VECTOR_TERNARY = "vector_ternary"
    VECTOR_SCALAR = "vector_scalar"
    VECTOR_SCALAR_VECTOR = "vector_scalar_vector"
    SCHEDULE = "schedule"


class StructuralOp(str, Enum):
    BROADCAST = "broadcast"
    LOAD = "load"
    STORE = "store"
    LANE_STORE = "lane_store"
    TAKE_LOW = "take_low"
    TAKE_HIGH = "take_high"
    CONCATENATE = "concatenate"
    BITCAST = "bitcast"
    EXTRACT_FROM_CONCAT = "extract_from_concat"


class ScheduleOp(str, Enum):
    SET_ACTIVE_LENGTH = "set_active_length"


class OperandTransform(str, Enum):
    """How a source operand is supplied to an existing SALT Lean definition."""

    IDENTITY = "identity"
    UNBROADCAST = "unbroadcast"
    TO_NAT = "to_nat"
    NEGATED_UNBROADCAST_TO_NAT = "negated_unbroadcast_to_nat"


@dataclass(frozen=True, slots=True)
class ScalarType:
    c_spelling: str
    bit_width: int | None
    signedness: Signedness

    def __post_init__(self) -> None:
        if not self.c_spelling:
            raise SchemaError("scalar C spelling must not be empty")
        if self.bit_width is not None and self.bit_width <= 0:
            raise SchemaError("scalar bit width must be positive")


@dataclass(frozen=True, slots=True)
class FloatingType:
    c_spelling: str
    bit_width: int

    def __post_init__(self) -> None:
        if not self.c_spelling:
            raise SchemaError("floating C spelling must not be empty")
        if self.bit_width <= 0:
            raise SchemaError("floating bit width must be positive")


ScalarValueType: TypeAlias = ScalarType | FloatingType


@dataclass(frozen=True, slots=True)
class VectorType:
    c_spelling: str
    element: ScalarValueType
    fixed_lanes: int | None = None
    lmul: str | None = None

    def __post_init__(self) -> None:
        if not self.c_spelling:
            raise SchemaError("vector C spelling must not be empty")
        if (self.fixed_lanes is None) == (self.lmul is None):
            raise SchemaError(
                "a vector type must have exactly one of fixed_lanes or lmul"
            )
        if self.fixed_lanes is not None and self.fixed_lanes <= 0:
            raise SchemaError("fixed vector lane count must be positive")
        if self.lmul is not None and not self.lmul:
            raise SchemaError("RVV LMUL must not be empty")

    @property
    def scalable(self) -> bool:
        return self.lmul is not None


@dataclass(frozen=True, slots=True)
class PointerType:
    pointee: ScalarValueType
    const: bool = False

    @property
    def c_spelling(self) -> str:
        qualifier = "const " if self.const else ""
        return f"{qualifier}{self.pointee.c_spelling}*"


@dataclass(frozen=True, slots=True)
class VoidType:
    c_spelling: str = "void"

    def __post_init__(self) -> None:
        if self.c_spelling != "void":
            raise SchemaError("VoidType has the unique spelling 'void'")


ValueType: TypeAlias = ScalarValueType | VectorType | PointerType | VoidType


def render_clang_type(value_type: ValueType) -> str:
    """Render the spelling Clang uses in a function ``qualType``.

    The parse facade and registry share this renderer so the frontend does not
    carry a second, independently maintained signature table.
    """

    if isinstance(value_type, PointerType):
        qualifier = "const " if value_type.const else ""
        return f"{qualifier}{value_type.pointee.c_spelling} *"
    return value_type.c_spelling


@dataclass(frozen=True, slots=True)
class Parameter:
    name: str
    type: ValueType

    def __post_init__(self) -> None:
        if not self.name:
            raise SchemaError("parameter name must not be empty")


@dataclass(frozen=True, slots=True)
class FunctionSignature:
    parameters: tuple[Parameter, ...]
    result: ValueType

    @property
    def argument_types(self) -> tuple[ValueType, ...]:
        return tuple(parameter.type for parameter in self.parameters)


def render_clang_function_type(signature: FunctionSignature) -> str:
    parameters = ", ".join(
        render_clang_type(parameter.type) for parameter in signature.parameters
    )
    return f"{render_clang_type(signature.result)} ({parameters})"


ImmediateValue: TypeAlias = int | str


@dataclass(frozen=True, slots=True)
class ImmediateConstraint:
    argument_index: int
    allowed_values: frozenset[ImmediateValue]
    erased_from_semantics: bool = True

    def __post_init__(self) -> None:
        if self.argument_index < 0:
            raise SchemaError("immediate argument index must be non-negative")
        if not self.allowed_values:
            raise SchemaError("an immediate constraint needs an allowed value")
        if any(not isinstance(value, (int, str)) for value in self.allowed_values):
            raise SchemaError("immediate values must be integers or exact symbols")


@dataclass(frozen=True, slots=True)
class LeanArgument:
    source_index: int
    transform: OperandTransform = OperandTransform.IDENTITY

    def __post_init__(self) -> None:
        if self.source_index < 0:
            raise SchemaError("Lean argument source index must be non-negative")


def _validate_intrinsic(
    spelling: str,
    signature: FunctionSignature,
    constraints: tuple[ImmediateConstraint, ...],
) -> None:
    if not spelling or spelling.strip() != spelling:
        raise SchemaError("intrinsic spelling must be a non-empty exact token")
    arity = len(signature.parameters)
    seen: set[int] = set()
    for constraint in constraints:
        if constraint.argument_index >= arity:
            raise SchemaError(
                f"immediate index {constraint.argument_index} is outside arity {arity}"
            )
        if constraint.argument_index in seen:
            raise SchemaError("only one constraint is allowed per argument")
        seen.add(constraint.argument_index)


@dataclass(frozen=True, slots=True)
class StructuralIntrinsic:
    spelling: str
    architecture: Architecture
    signature: FunctionSignature
    shape: OperationShape
    operation: StructuralOp
    immediate_constraints: tuple[ImmediateConstraint, ...] = ()

    def __post_init__(self) -> None:
        _validate_intrinsic(self.spelling, self.signature, self.immediate_constraints)
        if self.shape == OperationShape.SCHEDULE:
            raise SchemaError("a structural intrinsic cannot have schedule shape")

    @property
    def kind(self) -> NodeKind:
        return NodeKind.STRUCTURAL

    @property
    def lean_name(self) -> None:
        # Structural operations are rendered by the backend, not by pretending
        # that a matching SALT intrinsic definition already exists.
        return None


@dataclass(frozen=True, slots=True)
class SemanticIntrinsic:
    spelling: str
    architecture: Architecture
    signature: FunctionSignature
    shape: OperationShape
    lean_name: str
    lean_arguments: tuple[LeanArgument, ...]
    immediate_constraints: tuple[ImmediateConstraint, ...] = ()

    def __post_init__(self) -> None:
        _validate_intrinsic(self.spelling, self.signature, self.immediate_constraints)
        if self.shape == OperationShape.SCHEDULE:
            raise SchemaError("a semantic intrinsic cannot have schedule shape")
        if not self.lean_name.startswith("SALT.Intrinsics."):
            raise SchemaError("semantic targets must name a SALT.Intrinsics definition")
        arity = len(self.signature.parameters)
        for argument in self.lean_arguments:
            if argument.source_index >= arity:
                raise SchemaError(
                    f"Lean argument index {argument.source_index} is outside arity {arity}"
                )
        erased = {
            constraint.argument_index
            for constraint in self.immediate_constraints
            if constraint.erased_from_semantics
        }
        expected_sources = tuple(
            index
            for index, parameter in enumerate(self.signature.parameters)
            if index not in erased and parameter.name != "vl"
        )
        actual_sources = tuple(
            argument.source_index for argument in self.lean_arguments
        )
        if actual_sources != expected_sources:
            raise SchemaError(
                f"{self.spelling} Lean arguments must cover semantic C operands "
                f"exactly once in source order: expected {expected_sources!r}, "
                f"got {actual_sources!r}"
            )

    @property
    def kind(self) -> NodeKind:
        return NodeKind.SEMANTIC


@dataclass(frozen=True, slots=True)
class ScheduleIntrinsic:
    spelling: str
    architecture: Architecture
    signature: FunctionSignature
    shape: OperationShape
    operation: ScheduleOp
    immediate_constraints: tuple[ImmediateConstraint, ...] = ()

    def __post_init__(self) -> None:
        _validate_intrinsic(self.spelling, self.signature, self.immediate_constraints)
        if self.shape != OperationShape.SCHEDULE:
            raise SchemaError("a schedule intrinsic must have schedule shape")

    @property
    def kind(self) -> NodeKind:
        return NodeKind.SCHEDULE

    @property
    def lean_name(self) -> None:
        return None


IntrinsicSpec: TypeAlias = StructuralIntrinsic | SemanticIntrinsic | ScheduleIntrinsic


@dataclass(frozen=True, slots=True)
class TypedOperand:
    expression: str
    type: ValueType
    constant: ImmediateValue | None = None

    def __post_init__(self) -> None:
        if not self.expression:
            raise SchemaError("operand expression must not be empty")
        if self.constant is not None and not isinstance(self.constant, (int, str)):
            raise SchemaError("operand constants must be integers or exact symbols")


def validate_call(spec: IntrinsicSpec, operands: tuple[TypedOperand, ...]) -> None:
    expected = spec.signature.argument_types
    actual = tuple(operand.type for operand in operands)
    if len(actual) != len(expected):
        raise SignatureMismatchError(
            f"{spec.spelling} expects {len(expected)} arguments, got {len(actual)}"
        )
    for index, (actual_type, expected_type) in enumerate(zip(actual, expected)):
        if actual_type != expected_type:
            raise SignatureMismatchError(
                f"{spec.spelling} argument {index} expects {expected_type!r}, "
                f"got {actual_type!r}"
            )
    for constraint in spec.immediate_constraints:
        operand = operands[constraint.argument_index]
        if operand.constant not in constraint.allowed_values:
            allowed = sorted(constraint.allowed_values, key=repr)
            raise ImmediateConstraintError(
                f"{spec.spelling} argument {constraint.argument_index} must be "
                f"one of {allowed!r}, got {operand.constant!r}"
            )


@dataclass(frozen=True, slots=True)
class StructuralNode:
    spec: StructuralIntrinsic
    operands: tuple[TypedOperand, ...]

    def __post_init__(self) -> None:
        validate_call(self.spec, self.operands)


@dataclass(frozen=True, slots=True)
class SemanticNode:
    spec: SemanticIntrinsic
    operands: tuple[TypedOperand, ...]

    def __post_init__(self) -> None:
        validate_call(self.spec, self.operands)


@dataclass(frozen=True, slots=True)
class ScheduleNode:
    spec: ScheduleIntrinsic
    operands: tuple[TypedOperand, ...]

    def __post_init__(self) -> None:
        validate_call(self.spec, self.operands)


IntrinsicNode: TypeAlias = StructuralNode | SemanticNode | ScheduleNode


def make_node(
    spec: IntrinsicSpec, operands: tuple[TypedOperand, ...]
) -> IntrinsicNode:
    """Construct the correctly typed node variant after validating its call."""

    if isinstance(spec, StructuralIntrinsic):
        return StructuralNode(spec, operands)
    if isinstance(spec, SemanticIntrinsic):
        return SemanticNode(spec, operands)
    if isinstance(spec, ScheduleIntrinsic):
        return ScheduleNode(spec, operands)
    raise SchemaError(f"unsupported intrinsic spec type: {type(spec)!r}")
