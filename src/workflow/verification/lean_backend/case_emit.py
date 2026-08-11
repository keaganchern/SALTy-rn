"""Generic local-block Lean emission for reviewed scale-up profiles.

The emitter consumes calls from one selected Neon fixed-width loop body and one
RVV strip-mined body.  Calls in tails and other phases remain audited by the
frontend but are deliberately outside the theorem represented by this module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping

from .emit_lean import (
    EmittedPair,
    LeanEmissionError,
    _BlockEmitter,
    _lean_identifier,
    _lean_string_definition,
    _single_dependency,
)
from .frontend import ArgumentFact, ControlFact, DefinitionFact, IntrinsicCall, KernelExtraction
from .model_profiles import ModelProfile
from .schema import (
    Architecture,
    IntrinsicSpec,
    ScheduleIntrinsic,
    SemanticIntrinsic,
    StructuralIntrinsic,
    StructuralOp,
    VectorType,
)


class CaseEmissionError(LeanEmissionError):
    """A reviewed case does not match the generic block adapter."""


@dataclass(frozen=True, slots=True)
class CaseEmission:
    emitted: EmittedPair
    neon_consumed_calls: tuple[str, ...]
    rvv_consumed_calls: tuple[str, ...]


_C_INTEGER_WIDTHS = {
    "signed char": 8,
    "unsigned char": 8,
    "char": 8,
    "short": 16,
    "unsigned short": 16,
    "int": 32,
    "unsigned int": 32,
    "long": 64,
    "unsigned long": 64,
    "int8_t": 8,
    "uint8_t": 8,
    "int16_t": 16,
    "uint16_t": 16,
    "int32_t": 32,
    "uint32_t": 32,
    "int64_t": 64,
    "uint64_t": 64,
}

_REVIEWED_CASTS_BY_DESTINATION = {
    "signed char": frozenset({"int8_t", "signed char"}),
    "unsigned char": frozenset({"uint8_t", "unsigned char"}),
    "short": frozenset({"int16_t", "short"}),
    "unsigned short": frozenset({"uint16_t", "unsigned short"}),
    "int": frozenset({"int32_t", "int"}),
    "unsigned int": frozenset({"uint32_t", "unsigned int"}),
    "long": frozenset({"int64_t", "long"}),
    "unsigned long": frozenset({"uint64_t", "unsigned long"}),
}


def _integer_width(type_spelling: str) -> int:
    normalized = _normalized_integer_type(type_spelling)
    try:
        return _C_INTEGER_WIDTHS[normalized]
    except KeyError as error:
        raise CaseEmissionError(
            f"unsupported scalar conversion type {type_spelling!r}"
        ) from error


def _normalized_integer_type(type_spelling: str) -> str:
    normalized = re.sub(r"\b(const|volatile|restrict)\b", "", type_spelling)
    return " ".join(normalized.split())


def _field_name(dependency: str) -> str:
    prefix = "field:params@0.scalar."
    if not dependency.startswith(prefix):
        raise CaseEmissionError(f"unsupported parameter dependency {dependency!r}")
    field = dependency.removeprefix(prefix)
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", field) is None:
        raise CaseEmissionError(f"malformed parameter field {field!r}")
    return field


def _converted_field(field: str, width: int, *, negated: bool = False) -> str:
    source = f"p.{field}"
    if negated:
        source = f"(-{source})"
    return f"({source}).truncate {width}"


def _reviewed_field_argument(argument: ArgumentFact) -> tuple[str, bool]:
    field = _field_name(_single_dependency(argument))
    expected = f"params->scalar.{field}"
    compact = re.sub(r"\s+", "", argument.source_text)
    if compact == expected:
        negated = False
    elif compact == f"-{expected}":
        negated = True
    else:
        raise CaseEmissionError(
            f"unsupported parameter expression {argument.source_text!r}"
        )
    implicit_cast = f"implicit-cast:IntegralCast:{argument.type_spelling}"
    accepted_operations = (
        {(), (implicit_cast,)}
        if not negated
        else {("unary:-",), ("unary:-", implicit_cast)}
    )
    if argument.semantic_operations not in accepted_operations:
        raise CaseEmissionError(
            f"unsupported parameter conversion chain {argument.semantic_operations!r}"
        )
    # Keep the sign operation separate.  The base emitter uses the Boolean to
    # distinguish a negated broadcast from a plain one and applies the negation
    # exactly once when materializing the vector value.
    return _converted_field(field, _integer_width(argument.type_spelling)), negated


def _reviewed_scalar_definition(definition: DefinitionFact) -> str:
    field = _field_name(definition.dependencies[0])
    if "=" not in definition.expression_text:
        raise CaseEmissionError(
            f"definition {definition.value} has no initializer: "
            f"{definition.expression_text!r}"
        )
    initializer = definition.expression_text.split("=", 1)[1].strip()
    expected = f"params->scalar.{field}"
    match = re.fullmatch(
        rf"(?:\((?P<cast>[A-Za-z_][A-Za-z0-9_ ]*)\)\s*)?"
        rf"(?P<negated>-?)\s*{re.escape(expected)}",
        initializer,
    )
    if match is None:
        raise CaseEmissionError(
            f"definition {definition.value} is not a reviewed parameter conversion: "
            f"{definition.expression_text!r}"
        )
    cast = match.group("cast")
    destination = _normalized_integer_type(definition.type_spelling)
    if cast is not None and cast not in _REVIEWED_CASTS_BY_DESTINATION.get(
        destination, frozenset()
    ):
        raise CaseEmissionError(
            f"definition {definition.value} uses unreviewed cast {cast!r} "
            f"for destination {destination!r}"
        )
    negated = match.group("negated") == "-"
    return _converted_field(
        field,
        _integer_width(definition.type_spelling),
        negated=negated,
    )


def _is_exact_local_argument(
    argument: ArgumentFact,
    *,
    dependency: str,
    source_text: str,
    type_spelling: str,
) -> bool:
    return (
        argument.dependencies == (dependency,)
        and argument.source_text.strip() == source_text
        and not argument.semantic_operations
        and argument.constant_value is None
        and _normalized_integer_type(argument.type_spelling) == type_spelling
    )


class _CaseBlockEmitter(_BlockEmitter):
    def __init__(
        self,
        extraction: KernelExtraction,
        architecture: Architecture,
        registry: Mapping[str, IntrinsicSpec],
        *,
        active_length: str | None = None,
    ) -> None:
        super().__init__(
            extraction,
            architecture,
            registry=registry,
            active_length=active_length,
        )
        for definition in extraction.definitions:
            if (
                definition.value_call is None
                and len(definition.dependencies) == 1
                and definition.dependencies[0].startswith("field:params@0.scalar.")
                and definition.definition_kind != "parameter"
                and definition.parent_control is None
            ):
                self.environment[definition.value] = _reviewed_scalar_definition(definition)

    def _checked_field_source(self, argument: ArgumentFact) -> tuple[str, bool]:
        return _reviewed_field_argument(argument)

    def _resolve(self, argument: ArgumentFact) -> str:
        if (
            argument.constant_value == 0
            and len(argument.semantic_operations) == 1
            and argument.semantic_operations[0].startswith(
                "explicit-cast:IntegralCast:"
            )
        ):
            return "0"
        return super()._resolve(argument)

    def _structural_expression(
        self, call: IntrinsicCall, spec: StructuralIntrinsic
    ) -> str:
        if spec.operation is StructuralOp.BROADCAST:
            result = spec.signature.result
            if not isinstance(result, VectorType):
                raise CaseEmissionError(
                    f"{call.spelling} has a non-vector broadcast result"
                )
            lanes = result.fixed_lanes
            if lanes is None and self.active_length is None:
                raise CaseEmissionError(
                    f"scalable broadcast {call.spelling} has no active-length binding"
                )
            argument = call.arguments[0]
            dependency = _single_dependency(argument)
            if argument.constant_value is not None:
                scalar = self._resolve(argument)
            elif not argument.semantic_operations and dependency in self.environment:
                scalar = self.environment[dependency]
            else:
                scalar, is_negated = self._checked_field_source(argument)
                if is_negated:
                    scalar = f"-{scalar}"
            length = str(lanes) if lanes is not None else self.active_length
            return f"List.replicate {length} ({scalar})"
        return super()._structural_expression(call, spec)


def _selected_neon_loop(extraction: KernelExtraction, profile: ModelProfile):
    matches = [
        control
        for control in extraction.controls
        if control.kind == "ForStmt"
        and control.parent_control is None
        and control.condition_text == profile.neon_loop_condition
        and control.update_text == profile.neon_loop_update
    ]
    if len(matches) != 1:
        raise CaseEmissionError(
            f"{profile.case_id}: expected one reviewed Neon block loop, got {len(matches)}"
        )
    return matches[0]


def _emit_neon_case(
    extraction: KernelExtraction,
    profile: ModelProfile,
    registry: Mapping[str, IntrinsicSpec],
) -> tuple[list[str], str, tuple[str, ...]]:
    loop = _selected_neon_loop(extraction, profile)
    child_controls = [
        control
        for control in extraction.controls
        if control.parent_control == loop.node_id
    ]
    if child_controls:
        raise CaseEmissionError(
            f"{profile.case_id}: nested Neon block control is unsupported"
        )
    emitter = _CaseBlockEmitter(extraction, Architecture.NEON, registry)

    selected_calls = [
        call
        for call in extraction.calls
        if call.parent_control in {None, loop.node_id}
    ]
    for call in selected_calls:
        if call.parent_control is None:
            spec = emitter._lookup_intrinsic(call.spelling)
            if not (
                isinstance(spec, StructuralIntrinsic)
                and spec.operation is StructuralOp.BROADCAST
            ):
                raise CaseEmissionError(
                    f"{profile.case_id}: unsupported top-level Neon call {call.spelling}"
                )
            emitter.emit_registered_call(call)

    load_offsets = {name: 0 for name in profile.inputs}
    load_versions = {name: 0 for name in profile.inputs}
    stored_lanes = 0
    store_version = 0
    input_update_widths = {name: [] for name in profile.inputs}
    output_update_widths: list[int] = []
    stores: list[str] = []
    for call in selected_calls:
        if call.parent_control != loop.node_id:
            continue
        spec = emitter._lookup_intrinsic(call.spelling)
        if isinstance(spec, StructuralIntrinsic) and spec.operation is StructuralOp.LOAD:
            base_argument = call.arguments[0]
            dependency = _single_dependency(base_argument)
            match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)@(\d+)", dependency)
            if match is None or match.group(1) not in load_offsets:
                raise CaseEmissionError(
                    f"{profile.case_id}: unsupported Neon load base {dependency!r}"
                )
            base, version_text = match.groups()
            if base_argument.source_text.strip() != base or base_argument.semantic_operations:
                raise CaseEmissionError(
                    f"{profile.case_id}: unsupported Neon load expression "
                    f"{base_argument.source_text!r}"
                )
            if int(version_text) != load_versions[base]:
                raise CaseEmissionError(
                    f"{profile.case_id}: non-contiguous pointer version for {base}"
                )
            result = spec.signature.result
            if not isinstance(result, VectorType) or result.fixed_lanes is None:
                raise CaseEmissionError(f"{call.spelling} needs a fixed-width result")
            offset = load_offsets[base]
            width = result.fixed_lanes
            expression = (
                f"({base}).take {width}"
                if offset == 0
                else f"(({base}).drop {offset}).take {width}"
            )
            load_offsets[base] += width
            load_versions[base] += 1
            input_update_widths[base].append(width)
            emitter._bind_call(call, expression)
            continue
        if isinstance(spec, StructuralIntrinsic) and spec.operation is StructuralOp.STORE:
            store_base = call.arguments[0]
            if (
                store_base.dependencies != (f"output@{store_version}",)
                or store_base.source_text.strip() != "output"
                or store_base.semantic_operations
            ):
                raise CaseEmissionError(
                    f"{profile.case_id}: Neon store base changed at store {store_version}"
                )
        result = emitter.emit_registered_call(call)
        if isinstance(spec, StructuralIntrinsic) and spec.operation is StructuralOp.STORE:
            if result is None:
                raise CaseEmissionError(f"{call.spelling} produced no stored value")
            vector = spec.signature.parameters[1].type
            if not isinstance(vector, VectorType) or vector.fixed_lanes is None:
                raise CaseEmissionError(f"{call.spelling} needs a fixed-width stored value")
            stored_lanes += vector.fixed_lanes
            output_update_widths.append(vector.fixed_lanes)
            store_version += 1
            stores.append(result)

    expected = {call.node_id for call in selected_calls}
    if emitter.consumed != expected:
        raise CaseEmissionError(
            f"{profile.case_id}: Neon selected-call coverage mismatch: "
            f"missing={sorted(expected - emitter.consumed)!r}, "
            f"extra={sorted(emitter.consumed - expected)!r}"
        )
    expected_loads = {name: profile.neon_block_lanes for name in profile.inputs}
    if load_offsets != expected_loads or stored_lanes != profile.neon_block_lanes:
        raise CaseEmissionError(
            f"{profile.case_id}: Neon block footprint changed: "
            f"loads={load_offsets!r}, stored={stored_lanes}"
        )
    if not stores:
        raise CaseEmissionError(f"{profile.case_id}: Neon block has no store")

    expected_updates: list[tuple[str, str]] = []
    for input_name in profile.inputs:
        expected_updates.extend(
            (f"{input_name}@{index}", f"{input_name} += {width}")
            for index, width in enumerate(input_update_widths[input_name], 1)
        )
    expected_updates.extend(
        (f"output@{index}", f"output += {width}")
        for index, width in enumerate(output_update_widths, 1)
    )
    expected_updates.append(("batch@1", profile.neon_loop_update))
    actual_updates = [
        (definition.value, definition.expression_text.strip())
        for definition in extraction.definitions
        if definition.parent_control == loop.node_id
        and definition.definition_kind.startswith("compound-")
    ]
    if actual_updates != expected_updates:
        raise CaseEmissionError(
            f"{profile.case_id}: Neon pointer/count updates changed: "
            f"{actual_updates!r}"
        )
    untranslated = [
        definition.value
        for definition in extraction.definitions
        if definition.parent_control == loop.node_id
        and definition.value_call is None
        and not definition.definition_kind.startswith("compound-")
    ]
    if untranslated:
        raise CaseEmissionError(
            f"{profile.case_id}: untranslated Neon block definitions {untranslated!r}"
        )
    _validate_external_definitions(extraction, emitter)
    return emitter.lines, " ++ ".join(f"({value})" for value in stores), tuple(sorted(expected))


def _selected_rvv_loop(extraction: KernelExtraction, profile: ModelProfile):
    matches = [
        control
        for control in extraction.controls
        if control.kind == "WhileStmt"
        and control.parent_control is None
        and control.condition_text == "batch > 0"
    ]
    if len(matches) != 1:
        raise CaseEmissionError(
            f"{profile.case_id}: expected one reviewed RVV loop, got {len(matches)}"
        )
    return matches[0]


def _validate_rvv_scalar_types(
    extraction: KernelExtraction, profile: ModelProfile
) -> None:
    actual: dict[str, str] = {}
    for definition in extraction.definitions:
        if (
            definition.parent_control is not None
            or definition.definition_kind == "parameter"
            or definition.value_call is not None
            or len(definition.dependencies) != 1
            or not definition.dependencies[0].startswith(
                "field:params@0.scalar."
            )
        ):
            continue
        field = _field_name(definition.dependencies[0])
        if field in actual:
            raise CaseEmissionError(f"duplicate RVV scalar local for field {field!r}")
        actual[field] = _normalized_integer_type(definition.type_spelling)
    expected = dict(profile.rvv_scalar_types)
    if actual != expected:
        raise CaseEmissionError(
            f"{profile.case_id}: RVV scalar local types changed: {actual!r}"
        )


def _validate_external_definitions(
    extraction: KernelExtraction, emitter: _CaseBlockEmitter
) -> None:
    rejected: list[str] = []
    for definition in extraction.definitions:
        if definition.parent_control is not None or definition.definition_kind == "parameter":
            continue
        if definition.value_call is not None:
            continue
        if definition.value not in emitter.environment:
            rejected.append(definition.value)
    if rejected:
        raise CaseEmissionError(
            f"untranslated definitions outside the selected block: {rejected!r}"
        )


def _reviewed_signed_shift_branch(
    emitter: _CaseBlockEmitter,
    branch: ControlFact,
    calls: list[IntrinsicCall],
) -> None:
    """Emit the exact signed-shift branch in current ``qu8-vadd-minmax``.

    The frontend records syntactic variable versions rather than CFG phi nodes,
    so the else assignment appears to consume the then assignment.  This adapter
    validates the complete two-call branch and constructs the actual join value.
    """

    if (
        branch.kind != "IfStmt"
        or branch.condition_text != "shift >= 0"
        or branch.condition_dependencies != ("shift@0", "constant:0:int")
    ):
        raise CaseEmissionError("unsupported RVV signed-shift branch condition")
    if [call.spelling for call in calls] != [
        "__riscv_vssra_vx_i32m8",
        "__riscv_vsll_vx_i32m8",
    ]:
        raise CaseEmissionError(
            "RVV signed-shift branch must contain exactly vssra then vsll"
        )

    right, left = calls
    right_spec = emitter._lookup_intrinsic(right.spelling)
    left_spec = emitter._lookup_intrinsic(left.spelling)
    if not isinstance(right_spec, SemanticIntrinsic) or not isinstance(
        left_spec, SemanticIntrinsic
    ):
        raise CaseEmissionError("RVV signed-shift branch calls must be semantic")
    emitter._validate_immediates(right, right_spec)
    emitter._validate_immediates(left, left_spec)

    if (
        right.assigned_to is None
        or left.assigned_to is None
        or right.arguments[0].dependencies != ("vacc@1",)
        or left.arguments[0].dependencies != (right.assigned_to,)
        or left.arguments[0].source_text.strip() != "vacc"
        or left.arguments[0].semantic_operations
        or right.arguments[1].dependencies != ("shift@0",)
        or left.arguments[1].dependencies != ("shift@0",)
        or re.sub(r"\s+", "", right.arguments[1].source_text) != "(size_t)shift"
        or re.sub(r"\s+", "", left.arguments[1].source_text) != "(size_t)(-shift)"
        or right.arguments[1].semantic_operations
        != ("explicit-cast:IntegralCast:unsigned long",)
        or left.arguments[1].semantic_operations
        != ("unary:-", "explicit-cast:IntegralCast:unsigned long")
        or right.arguments[2].constant_value != 0
        or not _is_exact_local_argument(
            right.arguments[3],
            dependency="vl@0",
            source_text="vl",
            type_spelling="unsigned long",
        )
        or not _is_exact_local_argument(
            left.arguments[2],
            dependency="vl@0",
            source_text="vl",
            type_spelling="unsigned long",
        )
        or right.control_path != (f"{branch.node_id}:then",)
        or left.control_path != (f"{branch.node_id}:else",)
    ):
        raise CaseEmissionError("RVV signed-shift branch dataflow changed")

    accumulator = emitter._resolve(right.arguments[0])
    try:
        shift = emitter.environment["shift@0"]
    except KeyError as error:
        raise CaseEmissionError("RVV signed-shift branch has no reviewed shift") from error
    mode = emitter._resolve(right.arguments[2])
    right_name = emitter._bind_call(
        right,
        f"{right_spec.lean_name} ({accumulator}) (({shift}).toNat) ({mode})",
    )
    left_name = emitter._bind_call(
        left,
        f"{left_spec.lean_name} ({accumulator}) ((-({shift}).toInt).toNat)",
    )
    join_name = _lean_identifier(f"{left.assigned_to}_join")
    emitter.lines.append(
        f"  let {join_name} := if ({shift}).toInt >= 0 "
        f"then {right_name} else {left_name}"
    )
    emitter.environment[left.assigned_to] = join_name


def _emit_rvv_case(
    extraction: KernelExtraction,
    profile: ModelProfile,
    registry: Mapping[str, IntrinsicSpec],
) -> tuple[list[str], str, tuple[str, ...]]:
    loop = _selected_rvv_loop(extraction, profile)
    _validate_rvv_scalar_types(extraction, profile)
    active_length = f"{profile.inputs[0]}.length"
    emitter = _CaseBlockEmitter(
        extraction,
        Architecture.RVV,
        registry,
        active_length=active_length,
    )
    child_controls = [
        control
        for control in extraction.controls
        if control.parent_control == loop.node_id
    ]
    if child_controls and profile.case_id != "qu8-vadd-minmax":
        raise CaseEmissionError(
            f"{profile.case_id}: nested RVV control needs a reviewed adapter"
        )
    if profile.case_id == "qu8-vadd-minmax":
        if len(child_controls) != 1:
            raise CaseEmissionError(
                "qu8-vadd-minmax: expected one signed-shift child branch"
            )
        allowed_controls = {loop.node_id, child_controls[0].node_id}
    else:
        allowed_controls = {loop.node_id}
    actual_controls = {control.node_id for control in extraction.controls}
    if actual_controls != allowed_controls:
        raise CaseEmissionError(
            f"{profile.case_id}: RVV control shape changed: "
            f"{sorted(actual_controls)!r}"
        )
    selected_calls = [
        call for call in extraction.calls if call.parent_control in allowed_controls
    ]
    if len(selected_calls) != len(extraction.calls):
        nested = [
            call.spelling
            for call in extraction.calls
            if call.parent_control != loop.node_id
        ]
        raise CaseEmissionError(
            f"{profile.case_id}: nested or external RVV calls need a reviewed adapter: {nested!r}"
        )

    saw_schedule = False
    output: str | None = None
    branch_consumed = False
    for call in selected_calls:
        if child_controls and call.parent_control == child_controls[0].node_id:
            if branch_consumed:
                continue
            branch_calls = [
                nested
                for nested in selected_calls
                if nested.parent_control == child_controls[0].node_id
            ]
            _reviewed_signed_shift_branch(emitter, child_controls[0], branch_calls)
            branch_consumed = True
            continue
        spec = emitter._lookup_intrinsic(call.spelling)
        emitter._validate_immediates(call, spec)
        if isinstance(spec, ScheduleIntrinsic):
            if saw_schedule or call.assigned_to is None:
                raise CaseEmissionError(f"{profile.case_id}: malformed vsetvl binding")
            schedule_argument = call.arguments[0]
            if not _is_exact_local_argument(
                schedule_argument,
                dependency="batch@0",
                source_text="batch",
                type_spelling="unsigned long",
            ):
                raise CaseEmissionError(f"{profile.case_id}: vsetvl must consume batch")
            saw_schedule = True
            emitter.environment[f"call:{call.node_id}"] = active_length
            emitter.environment[call.assigned_to] = active_length
            emitter.consumed.add(call.node_id)
            continue
        if not saw_schedule:
            raise CaseEmissionError(f"{profile.case_id}: RVV data operation precedes vsetvl")
        vl_indices = [
            index
            for index, parameter in enumerate(spec.signature.parameters)
            if parameter.name == "vl"
        ]
        for index in vl_indices:
            if not _is_exact_local_argument(
                call.arguments[index],
                dependency="vl@0",
                source_text="vl",
                type_spelling="unsigned long",
            ):
                raise CaseEmissionError(
                    f"{profile.case_id}: {call.spelling} does not consume active vl"
                )
        if isinstance(spec, StructuralIntrinsic) and spec.operation is StructuralOp.LOAD:
            base_argument = call.arguments[0]
            dependency = _single_dependency(base_argument)
            base = dependency.split("@", 1)[0]
            if base not in profile.inputs:
                raise CaseEmissionError(
                    f"{profile.case_id}: unsupported RVV load base {base!r}"
                )
            if dependency != f"{base}@0":
                raise CaseEmissionError(
                    f"{profile.case_id}: RVV load does not use the chunk base"
                )
            if base_argument.source_text.strip() != base or base_argument.semantic_operations:
                raise CaseEmissionError(
                    f"{profile.case_id}: unsupported RVV load expression "
                    f"{base_argument.source_text!r}"
                )
            emitter._bind_call(call, base)
            continue
        if isinstance(spec, StructuralIntrinsic) and spec.operation is StructuralOp.STORE:
            store_base = call.arguments[0]
            if (
                store_base.dependencies != ("output@0",)
                or store_base.source_text.strip() != "output"
                or store_base.semantic_operations
            ):
                raise CaseEmissionError(
                    f"{profile.case_id}: RVV store does not use the chunk output base"
                )
        result = emitter.emit_registered_call(call)
        if isinstance(spec, StructuralIntrinsic) and spec.operation is StructuralOp.STORE:
            if output is not None or result is None:
                raise CaseEmissionError(f"{profile.case_id}: expected one RVV store")
            output = result

    expected = {call.node_id for call in selected_calls}
    if emitter.consumed != expected:
        raise CaseEmissionError(
            f"{profile.case_id}: RVV selected-call coverage mismatch: "
            f"missing={sorted(expected - emitter.consumed)!r}, "
            f"extra={sorted(emitter.consumed - expected)!r}"
        )
    if output is None:
        raise CaseEmissionError(f"{profile.case_id}: RVV block has no store")
    expected_updates = [
        (f"{input_name}@1", f"{input_name} += vl")
        for input_name in profile.inputs
    ]
    expected_updates.extend(
        [
            ("output@1", "output += vl"),
            ("batch@1", "batch -= vl"),
        ]
    )
    actual_updates = [
        (definition.value, definition.expression_text.strip())
        for definition in extraction.definitions
        if definition.parent_control == loop.node_id
        and definition.definition_kind.startswith("compound-")
    ]
    if actual_updates != expected_updates:
        raise CaseEmissionError(
            f"{profile.case_id}: RVV pointer/count updates changed: "
            f"{actual_updates!r}"
        )
    translated_controls = {loop.node_id}
    translated_controls.update(control.node_id for control in child_controls)
    untranslated = [
        definition.value
        for definition in extraction.definitions
        if definition.parent_control in translated_controls
        and definition.value_call is None
        and not definition.definition_kind.startswith("compound-")
    ]
    if untranslated:
        raise CaseEmissionError(
            f"{profile.case_id}: untranslated RVV block definitions {untranslated!r}"
        )
    _validate_external_definitions(extraction, emitter)
    return emitter.lines, output, tuple(sorted(expected))


def _parameter_structure(profile: ModelProfile) -> list[str]:
    lines = [f"structure {profile.parameter_type} where"]
    lines.extend(
        f"  {field.name} : BitVec {field.width}"
        for field in profile.parameter_fields
    )
    lines.append("  deriving Repr, DecidableEq")
    return lines


def _function_header(name: str, profile: ModelProfile) -> list[str]:
    lines = [f"def {name} (p : {profile.parameter_type})"]
    lines.extend(f"    ({input_name} : List (BitVec 8))" for input_name in profile.inputs)
    lines[-1] = f"{lines[-1]} : List (BitVec 8) :="
    return lines


def emit_case_pair(
    neon: KernelExtraction,
    rvv: KernelExtraction,
    *,
    profile: ModelProfile,
    neon_registry: Mapping[str, IntrinsicSpec],
    rvv_registry: Mapping[str, IntrinsicSpec],
    registry_sha256: str,
) -> CaseEmission:
    """Emit independent local block/chunk models for one reviewed pair."""

    if neon.facade_sha256 != rvv.facade_sha256:
        raise CaseEmissionError(f"{profile.case_id}: parse facades differ across sides")
    neon_lines, neon_output, neon_consumed = _emit_neon_case(
        neon, profile, neon_registry
    )
    rvv_lines, rvv_output, rvv_consumed = _emit_rvv_case(rvv, profile, rvv_registry)
    lines = [
        "-- This file is generated. Do not edit the models by hand.",
        "import SALT.Intrinsics.Neon",
        "import SALT.Intrinsics.RVV",
        "",
        f"namespace {profile.lean_namespace}",
        "",
        *_lean_string_definition("neonSourceSha256", neon.source_sha256),
        *_lean_string_definition("rvvSourceSha256", rvv.source_sha256),
        *_lean_string_definition("neonPreprocessedSha256", neon.preprocessed_sha256),
        *_lean_string_definition("rvvPreprocessedSha256", rvv.preprocessed_sha256),
        *_lean_string_definition("parseFacadeSha256", neon.facade_sha256),
        *_lean_string_definition("registrySha256", registry_sha256),
        "",
        *_parameter_structure(profile),
        "",
        *_function_header(profile.neon_function, profile),
        *neon_lines,
        f"  {neon_output}",
        "",
        *_function_header(profile.rvv_function, profile),
        *rvv_lines,
        f"  {rvv_output}",
        "",
        f"end {profile.lean_namespace}",
        "",
    ]
    emitted = EmittedPair(
        "\n".join(lines), profile.neon_function, profile.rvv_function
    )
    return CaseEmission(emitted, neon_consumed, rvv_consumed)
