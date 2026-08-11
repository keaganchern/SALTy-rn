"""Emit executable Lean block models from registry-bound intrinsic call DAGs.

This first emitter intentionally handles only the 16-lane Neon main body and
the RVV strip-mined body of ``qs8-vadd-minmax``.  It consumes every call in the
selected body, checks normalization provenance (for example, a vector operand
lowered to a Lean scalar must come from a broadcast), and rejects structural
operations whose semantics are not implemented here.

The emitted functions are block models.  They are not yet a refinement proof
for the complete C loops, tail stores, or an ISA execution.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path

from .frontend import _FACADE, ArgumentFact, IntrinsicCall, KernelExtraction
from .registry import lookup_intrinsic
from .schema import (
    Architecture,
    ImmediateConstraintError,
    OperandTransform,
    ScheduleIntrinsic,
    SemanticIntrinsic,
    StructuralIntrinsic,
    StructuralOp,
    VectorType,
)


class LeanEmissionError(ValueError):
    """The extracted call graph is outside the reviewed emission subset."""


@dataclass(frozen=True)
class EmittedPair:
    module_text: str
    neon_function: str
    rvv_function: str


def _file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _lean_identifier(value: str) -> str:
    identifier = re.sub(r"[^A-Za-z0-9_]", "_", value)
    if not identifier or identifier[0].isdigit():
        identifier = f"value_{identifier}"
    return identifier


def _lean_string_definition(name: str, value: str) -> list[str]:
    return [f"def {name} : String :=", f'  "{value}"']


def _single_dependency(argument: ArgumentFact) -> str:
    if len(argument.dependencies) != 1:
        raise LeanEmissionError(
            f"expected one dependency for {argument.source_text!r}, "
            f"got {argument.dependencies!r}"
        )
    return argument.dependencies[0]


def _field_expression(dependency: str) -> str:
    prefix = "field:params@0.scalar."
    if not dependency.startswith(prefix):
        raise LeanEmissionError(f"unsupported scalar source {dependency!r}")
    field = dependency.removeprefix(prefix)
    if not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", field):
        raise LeanEmissionError(f"malformed parameter field {field!r}")
    return f"p.{field}"


def _checked_field_source(argument: ArgumentFact) -> tuple[str, bool]:
    dependency = _single_dependency(argument)
    scalar = _field_expression(dependency)
    expected = f"params->scalar.{scalar.removeprefix('p.')}"
    source = argument.source_text.strip()
    if source == expected and not argument.semantic_operations:
        return scalar, False
    if source == f"-{expected}" and argument.semantic_operations == ("unary:-",):
        return scalar, True
    raise LeanEmissionError(
        f"unsupported cast or expression around parameter field: {source!r}"
    )


class _BlockEmitter:
    def __init__(self, extraction: KernelExtraction, architecture: Architecture) -> None:
        if extraction.dialect != architecture.value:
            raise LeanEmissionError(
                f"expected {architecture.value} extraction, got {extraction.dialect!r}"
            )
        self.extraction = extraction
        self.architecture = architecture
        self.calls_by_id = {call.node_id: call for call in extraction.calls}
        self.calls_by_value = {
            call.assigned_to: call
            for call in extraction.calls
            if call.assigned_to is not None
        }
        self.definitions = {definition.value: definition for definition in extraction.definitions}
        self.environment: dict[str, str] = {}
        self.lines: list[str] = []
        self.consumed: set[str] = set()

        for definition in extraction.definitions:
            if (
                definition.value_call is None
                and len(definition.dependencies) == 1
                and definition.dependencies[0].startswith("field:params@0.scalar.")
            ):
                self.environment[definition.value] = _field_expression(
                    definition.dependencies[0]
                )

    def _call_for_dependency(self, dependency: str) -> IntrinsicCall:
        if dependency.startswith("call:"):
            call_id = dependency.removeprefix("call:")
            try:
                return self.calls_by_id[call_id]
            except KeyError as error:
                raise LeanEmissionError(f"unknown call dependency {dependency!r}") from error
        try:
            return self.calls_by_value[dependency]
        except KeyError as error:
            raise LeanEmissionError(
                f"{dependency!r} is not produced by a registered intrinsic"
            ) from error

    def _resolve(self, argument: ArgumentFact) -> str:
        if argument.semantic_operations:
            raise LeanEmissionError(
                f"source operations {argument.semantic_operations!r} around "
                f"{argument.source_text!r} have no reviewed Lean lowering"
            )
        dependency = _single_dependency(argument)
        if dependency.startswith("field:params@0.scalar."):
            return _field_expression(dependency)
        try:
            return self.environment[dependency]
        except KeyError as error:
            raise LeanEmissionError(
                f"no emitted value for {dependency!r} used by {argument.source_text!r}"
            ) from error

    def _broadcast_scalar(self, argument: ArgumentFact, *, require_negated: bool) -> str:
        dependency = _single_dependency(argument)
        producer = self._call_for_dependency(dependency)
        producer_spec = lookup_intrinsic(producer.spelling, self.architecture)

        while (
            isinstance(producer_spec, StructuralIntrinsic)
            and producer_spec.operation in {StructuralOp.TAKE_LOW, StructuralOp.TAKE_HIGH}
        ):
            dependency = _single_dependency(producer.arguments[0])
            producer = self._call_for_dependency(dependency)
            producer_spec = lookup_intrinsic(producer.spelling, self.architecture)

        if not (
            isinstance(producer_spec, StructuralIntrinsic)
            and producer_spec.operation is StructuralOp.BROADCAST
            and len(producer.arguments) == 1
        ):
            raise LeanEmissionError(
                f"{argument.source_text!r} is normalized to a scalar but is not "
                "derived from a reviewed broadcast"
            )

        scalar_argument = producer.arguments[0]
        scalar, is_negated = _checked_field_source(scalar_argument)
        if is_negated != require_negated:
            expectation = "negated broadcast" if require_negated else "plain broadcast"
            raise LeanEmissionError(
                f"{producer.spelling} operand must be a {expectation}: "
                f"{scalar_argument.source_text!r}"
            )
        return scalar

    def _validate_immediates(
        self, call: IntrinsicCall, spec: StructuralIntrinsic | SemanticIntrinsic | ScheduleIntrinsic
    ) -> None:
        for constraint in spec.immediate_constraints:
            value = call.arguments[constraint.argument_index].constant_value
            if value not in constraint.allowed_values:
                allowed = sorted(constraint.allowed_values, key=repr)
                raise ImmediateConstraintError(
                    f"{call.spelling} argument {constraint.argument_index} must be "
                    f"one of {allowed!r}, got {value!r}"
                )

    def _semantic_expression(self, call: IntrinsicCall, spec: SemanticIntrinsic) -> str:
        arguments: list[str] = []
        for lean_argument in spec.lean_arguments:
            source = call.arguments[lean_argument.source_index]
            if lean_argument.transform is OperandTransform.IDENTITY:
                expression = self._resolve(source)
            elif lean_argument.transform is OperandTransform.UNBROADCAST:
                expression = self._broadcast_scalar(source, require_negated=False)
            elif lean_argument.transform is OperandTransform.TO_NAT:
                expression = f"({self._resolve(source)}).toNat"
            elif lean_argument.transform is OperandTransform.NEGATED_UNBROADCAST_TO_NAT:
                expression = f"({self._broadcast_scalar(source, require_negated=True)}).toNat"
            else:
                raise LeanEmissionError(
                    f"unsupported operand transform {lean_argument.transform.value!r}"
                )
            arguments.append(f"({expression})")
        return f"{spec.lean_name} {' '.join(arguments)}"

    def _bind_call(self, call: IntrinsicCall, expression: str) -> str:
        name = _lean_identifier(call.assigned_to or call.node_id)
        self.lines.append(f"  let {name} := {expression}")
        self.environment[f"call:{call.node_id}"] = name
        if call.assigned_to is not None:
            self.environment[call.assigned_to] = name
        self.consumed.add(call.node_id)
        return name

    def _structural_expression(self, call: IntrinsicCall, spec: StructuralIntrinsic) -> str:
        operation = spec.operation
        if operation is StructuralOp.BROADCAST:
            if not isinstance(spec.signature.result, VectorType):
                raise LeanEmissionError(f"{call.spelling} has a non-vector broadcast result")
            lanes = spec.signature.result.fixed_lanes
            if lanes is None:
                raise LeanEmissionError(f"scalable broadcast {call.spelling} is unsupported")
            scalar, is_negated = _checked_field_source(call.arguments[0])
            if is_negated:
                scalar = f"-{scalar}"
            return f"List.replicate {lanes} ({scalar})"
        if operation in {StructuralOp.TAKE_LOW, StructuralOp.TAKE_HIGH}:
            result = spec.signature.result
            if not isinstance(result, VectorType) or result.fixed_lanes is None:
                raise LeanEmissionError(f"{call.spelling} needs a fixed-width vector result")
            vector = self._resolve(call.arguments[0])
            method = "take" if operation is StructuralOp.TAKE_LOW else "drop"
            return f"({vector}).{method} {result.fixed_lanes}"
        if operation is StructuralOp.CONCATENATE:
            return f"{self._resolve(call.arguments[0])} ++ {self._resolve(call.arguments[1])}"
        if operation is StructuralOp.BITCAST:
            return self._resolve(call.arguments[0])
        if operation is StructuralOp.EXTRACT_FROM_CONCAT:
            result = spec.signature.result
            if not isinstance(result, VectorType) or result.fixed_lanes is None:
                raise LeanEmissionError(f"{call.spelling} needs a fixed-width vector result")
            offset = call.arguments[2].constant_value
            if not isinstance(offset, int):
                raise LeanEmissionError(f"{call.spelling} needs an integer offset")
            left = self._resolve(call.arguments[0])
            right = self._resolve(call.arguments[1])
            return f"(({left} ++ {right}).drop {offset}).take {result.fixed_lanes}"
        raise LeanEmissionError(
            f"structural operation {operation.value!r} needs context-specific lowering"
        )

    def emit_registered_call(self, call: IntrinsicCall) -> str | None:
        spec = lookup_intrinsic(call.spelling, self.architecture)
        self._validate_immediates(call, spec)
        if isinstance(spec, SemanticIntrinsic):
            return self._bind_call(call, self._semantic_expression(call, spec))
        if isinstance(spec, StructuralIntrinsic):
            if spec.operation in {StructuralOp.STORE, StructuralOp.LANE_STORE}:
                self.consumed.add(call.node_id)
                if spec.operation is StructuralOp.LANE_STORE:
                    raise LeanEmissionError("lane-store lowering requires an endian contract")
                return self._resolve(call.arguments[1])
            return self._bind_call(call, self._structural_expression(call, spec))
        raise LeanEmissionError(f"schedule call {call.spelling} needs loop context")


def _emit_neon_block(extraction: KernelExtraction) -> tuple[list[str], str]:
    emitter = _BlockEmitter(extraction, Architecture.NEON)
    controls = [control for control in extraction.controls if control.kind == "ForStmt"]
    if len(controls) != 1:
        raise LeanEmissionError(f"expected one Neon main loop, got {len(controls)}")
    main = controls[0]
    if (
        main.parent_control is not None
        or main.condition_text != "batch >= 16 * sizeof(int8_t)"
        or main.update_text != "batch -= 16 * sizeof(int8_t)"
    ):
        raise LeanEmissionError("unsupported Neon main-loop schedule")

    expected_updates = {
        ("input_a@1", "input_a += 8"),
        ("input_a@2", "input_a += 8"),
        ("input_b@1", "input_b += 8"),
        ("input_b@2", "input_b += 8"),
        ("output@1", "output += 16"),
        ("batch@1", "batch -= 16 * sizeof(int8_t)"),
    }
    actual_updates = {
        (definition.value, definition.expression_text.strip())
        for definition in extraction.definitions
        if definition.parent_control == main.node_id
        and definition.definition_kind.startswith("compound-")
    }
    if actual_updates != expected_updates:
        raise LeanEmissionError(
            f"unsupported Neon pointer/count updates: {sorted(actual_updates)!r}"
        )
    untranslated_main_definitions = [
        definition.value
        for definition in extraction.definitions
        if definition.parent_control == main.node_id
        and definition.value_call is None
        and not definition.definition_kind.startswith("compound-")
    ]
    if untranslated_main_definitions:
        raise LeanEmissionError(
            f"untranslated Neon main-body definitions: {untranslated_main_definitions!r}"
        )

    external_call_values = {
        call.assigned_to
        for call in extraction.calls
        if call.parent_control is None and call.assigned_to is not None
    }
    unexpected_external_definitions = [
        definition.value
        for definition in extraction.definitions
        if definition.parent_control is None
        and definition.definition_kind != "parameter"
        and definition.value not in external_call_values
    ]
    if unexpected_external_definitions:
        raise LeanEmissionError(
            "untranslated Neon statements outside the main loop: "
            f"{unexpected_external_definitions!r}"
        )

    identity_dependencies = {
        dependency
        for call in extraction.calls
        if call.parent_control == main.node_id
        for spec in (lookup_intrinsic(call.spelling, Architecture.NEON),)
        if isinstance(spec, SemanticIntrinsic)
        for lean_argument in spec.lean_arguments
        if lean_argument.transform is OperandTransform.IDENTITY
        for dependency in call.arguments[lean_argument.source_index].dependencies
    }
    for call in extraction.calls:
        spec = lookup_intrinsic(call.spelling, Architecture.NEON)
        if call.parent_control is None:
            if not (
                isinstance(spec, StructuralIntrinsic)
                and spec.operation is StructuralOp.BROADCAST
            ):
                raise LeanEmissionError(
                    f"unexpected call outside the Neon loop: {call.spelling}"
                )
            emitter._validate_immediates(call, spec)
            _checked_field_source(call.arguments[0])
            if (
                call.assigned_to in identity_dependencies
                or f"call:{call.node_id}" in identity_dependencies
            ):
                emitter.emit_registered_call(call)
            else:
                # Scalar-normalized uses are checked when their semantic call is
                # emitted; no dead Lean vector binding is needed.
                emitter.consumed.add(call.node_id)

    load_offsets = {"input_a": 0, "input_b": 0}
    output: str | None = None
    for call in extraction.calls:
        if call.parent_control != main.node_id:
            continue
        spec = lookup_intrinsic(call.spelling, Architecture.NEON)
        if isinstance(spec, StructuralIntrinsic) and spec.operation is StructuralOp.LOAD:
            dependency = _single_dependency(call.arguments[0])
            match = re.fullmatch(r"(input_[ab])@(\d+)", dependency)
            if match is None:
                raise LeanEmissionError(f"unsupported Neon load base {dependency!r}")
            base, version_text = match.groups()
            version = int(version_text)
            if version != load_offsets[base]:
                raise LeanEmissionError(
                    f"non-contiguous {base} load version {version}; "
                    f"expected {load_offsets[base]}"
                )
            load_offsets[base] += 1
            result = spec.signature.result
            if not isinstance(result, VectorType) or result.fixed_lanes is None:
                raise LeanEmissionError(f"{call.spelling} needs fixed load width")
            offset = version * result.fixed_lanes
            chunk = "chunk_a" if base == "input_a" else "chunk_b"
            expression = (
                f"({chunk}).take {result.fixed_lanes}"
                if offset == 0
                else f"(({chunk}).drop {offset}).take {result.fixed_lanes}"
            )
            emitter._bind_call(call, expression)
            continue
        result = emitter.emit_registered_call(call)
        if isinstance(spec, StructuralIntrinsic) and spec.operation is StructuralOp.STORE:
            if output is not None:
                raise LeanEmissionError("multiple stores in the selected Neon block")
            if call.arguments[0].dependencies != ("output@0",):
                raise LeanEmissionError("Neon main store must use the current output pointer")
            output = result

    expected = {
        call.node_id
        for call in extraction.calls
        if call.parent_control in {None, main.node_id}
    }
    if emitter.consumed != expected:
        missing = sorted(expected - emitter.consumed)
        extra = sorted(emitter.consumed - expected)
        raise LeanEmissionError(f"Neon call coverage mismatch: missing={missing}, extra={extra}")
    if load_offsets != {"input_a": 2, "input_b": 2} or output is None:
        raise LeanEmissionError("Neon main block must load 16 bytes from each input and store once")
    return emitter.lines, output


def _emit_rvv_block(extraction: KernelExtraction) -> tuple[list[str], str]:
    emitter = _BlockEmitter(extraction, Architecture.RVV)
    controls = [control for control in extraction.controls if control.kind == "WhileStmt"]
    if len(controls) != 1 or controls[0].condition_text != "batch > 0":
        raise LeanEmissionError("unsupported RVV strip-mined loop")
    loop = controls[0]
    if loop.parent_control is not None:
        raise LeanEmissionError("nested RVV strip-mined loop is unsupported")

    expected_initializers = {
        "a_zero_point@0": (
            "const signed char",
            "const int8_t a_zero_point = params->scalar.a_zero_point",
            ("field:params@0.scalar.a_zero_point",),
        ),
        "b_zero_point@0": (
            "const signed char",
            "const int8_t b_zero_point = params->scalar.b_zero_point",
            ("field:params@0.scalar.b_zero_point",),
        ),
        "a_multiplier@0": (
            "const int",
            "const int32_t a_multiplier = params->scalar.a_multiplier",
            ("field:params@0.scalar.a_multiplier",),
        ),
        "b_multiplier@0": (
            "const int",
            "const int32_t b_multiplier = params->scalar.b_multiplier",
            ("field:params@0.scalar.b_multiplier",),
        ),
        "shift@0": (
            "const unsigned long",
            "const size_t shift = (size_t)params->scalar.shift",
            ("field:params@0.scalar.shift",),
        ),
        "output_zero_point@0": (
            "const short",
            "const int16_t output_zero_point = params->scalar.output_zero_point",
            ("field:params@0.scalar.output_zero_point",),
        ),
        "output_min@0": (
            "const signed char",
            "const int8_t output_min = params->scalar.output_min",
            ("field:params@0.scalar.output_min",),
        ),
        "output_max@0": (
            "const signed char",
            "const int8_t output_max = params->scalar.output_max",
            ("field:params@0.scalar.output_max",),
        ),
    }
    actual_initializers = {
        definition.value: (
            definition.type_spelling,
            definition.expression_text.strip(),
            definition.dependencies,
        )
        for definition in extraction.definitions
        if definition.parent_control is None
        and definition.definition_kind != "parameter"
    }
    if actual_initializers != expected_initializers:
        raise LeanEmissionError(
            f"unsupported RVV scalar initializers: {actual_initializers!r}"
        )

    expected_updates = {
        "input_a": ("compound-+=", "input_a += vl", ("input_a@0", "vl@0")),
        "input_b": ("compound-+=", "input_b += vl", ("input_b@0", "vl@0")),
        "output": ("compound-+=", "output += vl", ("output@0", "vl@0")),
        "batch": ("compound--=", "batch -= vl", ("batch@0", "vl@0")),
    }
    actual_updates = {
        definition.variable: (
            definition.definition_kind,
            definition.expression_text.strip(),
            definition.dependencies,
        )
        for definition in extraction.definitions
        if definition.parent_control == loop.node_id
        and definition.definition_kind.startswith("compound-")
    }
    if actual_updates != expected_updates:
        raise LeanEmissionError(
            f"RVV pointer/count updates must all use active vl: {actual_updates!r}"
        )
    untranslated_loop_definitions = [
        definition.value
        for definition in extraction.definitions
        if definition.parent_control == loop.node_id
        and definition.value_call is None
        and not definition.definition_kind.startswith("compound-")
    ]
    if untranslated_loop_definitions:
        raise LeanEmissionError(
            f"untranslated RVV loop definitions: {untranslated_loop_definitions!r}"
        )

    output: str | None = None
    saw_schedule = False
    for call in extraction.calls:
        if call.parent_control != loop.node_id:
            raise LeanEmissionError(f"RVV call outside strip-mined body: {call.spelling}")
        spec = lookup_intrinsic(call.spelling, Architecture.RVV)
        emitter._validate_immediates(call, spec)
        constrained = {
            constraint.argument_index for constraint in spec.immediate_constraints
        }
        for index, argument in enumerate(call.arguments):
            reviewed_immediate_conversion = (
                f"implicit-cast:IntegralCast:{argument.type_spelling}",
            )
            if (
                argument.semantic_operations
                and not (
                    index in constrained
                    and argument.constant_value is not None
                    and argument.semantic_operations == reviewed_immediate_conversion
                )
            ):
                raise LeanEmissionError(
                    f"{call.node_id} argument {index} has unlowered source operations "
                    f"{argument.semantic_operations!r}"
                )
        if isinstance(spec, ScheduleIntrinsic):
            if saw_schedule or call.assigned_to is None:
                raise LeanEmissionError("expected one assigned RVV vsetvl call")
            if call.arguments[0].dependencies != ("batch@0",):
                raise LeanEmissionError("RVV vsetvl must consume the remaining batch")
            saw_schedule = True
            emitter.environment[f"call:{call.node_id}"] = "chunk_a.length"
            emitter.environment[call.assigned_to] = "chunk_a.length"
            emitter.consumed.add(call.node_id)
            continue
        if not saw_schedule:
            raise LeanEmissionError("RVV data operation occurs before vsetvl")
        if call.arguments[-1].dependencies != ("vl@0",):
            raise LeanEmissionError(f"{call.spelling} does not use the active vl")
        if isinstance(spec, StructuralIntrinsic) and spec.operation is StructuralOp.LOAD:
            base = _single_dependency(call.arguments[0])
            if base == "input_a@0":
                expression = "chunk_a"
            elif base == "input_b@0":
                expression = "chunk_b"
            else:
                raise LeanEmissionError(f"unsupported RVV load base {base!r}")
            emitter._bind_call(call, expression)
            continue
        result = emitter.emit_registered_call(call)
        if isinstance(spec, StructuralIntrinsic) and spec.operation is StructuralOp.STORE:
            if output is not None or call.arguments[0].dependencies != ("output@0",):
                raise LeanEmissionError("unsupported RVV store pattern")
            output = result

    if not saw_schedule or output is None:
        raise LeanEmissionError("RVV block must select vl and store once")
    if emitter.consumed != {call.node_id for call in extraction.calls}:
        raise LeanEmissionError("RVV emitter did not consume every extracted call")
    return emitter.lines, output


def emit_qs8_vadd_minmax_pair(
    neon: KernelExtraction,
    rvv: KernelExtraction,
) -> EmittedPair:
    """Emit independent block definitions from the selected C pair."""

    if neon.facade_sha256 != rvv.facade_sha256:
        raise LeanEmissionError("Neon and RVV models must share one parse facade")
    canonical_facade_sha256 = _file_sha256(_FACADE)
    if neon.facade_sha256 != canonical_facade_sha256:
        raise LeanEmissionError(
            "the qs8-vadd-minmax emitter requires the pinned parse facade"
        )
    if neon.target_triple != "aarch64-none-elf":
        raise LeanEmissionError(f"unexpected Neon target {neon.target_triple!r}")
    if rvv.target_triple != "riscv64-none-elf":
        raise LeanEmissionError(f"unexpected RVV target {rvv.target_triple!r}")

    neon_lines, neon_output = _emit_neon_block(neon)
    rvv_lines, rvv_output = _emit_rvv_block(rvv)
    neon_function = "neonBlock16FromIntrinsics"
    rvv_function = "rvvBlockFromIntrinsics"
    lines = [
        "-- This file is generated. Do not edit the models by hand.",
        "import SALT.Intrinsics.Neon",
        "import SALT.Intrinsics.RVV",
        "import SALT.Kernel.QS8.Params",
        "",
        "namespace SALT.Generated.QS8VAddMinmax",
        "",
        "open SALT.Kernel.QS8",
        "",
        *_lean_string_definition("neonSourceSha256", neon.source_sha256),
        *_lean_string_definition("rvvSourceSha256", rvv.source_sha256),
        *_lean_string_definition("neonPreprocessedSha256", neon.preprocessed_sha256),
        *_lean_string_definition("rvvPreprocessedSha256", rvv.preprocessed_sha256),
        *_lean_string_definition("parseFacadeSha256", canonical_facade_sha256),
        *_lean_string_definition(
            "registrySourceSha256",
            _file_sha256(Path(__file__).with_name("registry.py")),
        ),
        "",
        f"def {neon_function} (p : QS8AddMinmaxParams)",
        "    (chunk_a chunk_b : List (BitVec 8)) : List (BitVec 8) :=",
        *neon_lines,
        f"  {neon_output}",
        "",
        f"def {rvv_function} (p : QS8AddMinmaxParams)",
        "    (chunk_a chunk_b : List (BitVec 8)) : List (BitVec 8) :=",
        *rvv_lines,
        f"  {rvv_output}",
        "",
        "end SALT.Generated.QS8VAddMinmax",
        "",
    ]
    return EmittedPair("\n".join(lines), neon_function, rvv_function)
