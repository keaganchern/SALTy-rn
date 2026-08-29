"""Lean emission for reviewed scale-up profiles.

The generic path consumes one selected Neon fixed-width loop body and one RVV
strip-mined body. Reviewed schedule adapters may extend that boundary only after
validating the complete source shape. The initial adapters cover the complete
S8 64/8/4/2/1 schedule and a unary fixed-block plus prefix-tail grammar.
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
from .frontend import (
    ArgumentFact,
    ControlFact,
    DefinitionFact,
    IntrinsicCall,
    KernelExtraction,
)
from .model_profiles import ModelProfile
from .schema import (
    Architecture,
    IntrinsicSpec,
    PointerType,
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
                self.environment[definition.value] = _reviewed_scalar_definition(
                    definition
                )

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


def _normalized_control_shape(
    controls: tuple[ControlFact, ...],
) -> tuple[tuple[str, int | None, str, tuple[str, ...], str], ...]:
    positions = {control.node_id: index for index, control in enumerate(controls)}
    return tuple(
        (
            control.kind,
            (
                None
                if control.parent_control is None
                else positions.get(control.parent_control, -1)
            ),
            control.condition_text,
            control.condition_dependencies,
            control.update_text,
        )
        for control in controls
    )


_S8_VCLAMP_NEON_CONTROL_SHAPE = (
    ("ForStmt", None, "batch >= 64", ("batch@0", "constant:64:int"), "batch -= 64"),
    ("ForStmt", None, "batch >= 8", ("batch@1", "constant:8:int"), "batch -= 8"),
    ("IfStmt", None, "batch != 0", ("batch@2", "constant:0:int"), ""),
    ("IfStmt", 2, "batch & 4", ("batch@2", "constant:4:int"), ""),
    ("IfStmt", 2, "batch & 2", ("batch@2", "constant:2:int"), ""),
    ("IfStmt", 2, "batch & 1", ("batch@2", "constant:1:int"), ""),
)


def _byte_tail_control_shape(
    loop: ControlFact, element_type: str
) -> tuple[tuple[str, int | None, str, tuple[str, ...], str], ...]:
    return (
        (
            loop.kind,
            None,
            loop.condition_text,
            loop.condition_dependencies,
            loop.update_text,
        ),
        ("IfStmt", None, "batch != 0", ("batch@1", "constant:0:int"), ""),
        (
            "IfStmt",
            1,
            f"batch & (4 * sizeof({element_type}))",
            ("batch@1", "constant:4:int", f"sizeof:{element_type}"),
            "",
        ),
        (
            "IfStmt",
            1,
            f"batch & (2 * sizeof({element_type}))",
            ("batch@1", "constant:2:int", f"sizeof:{element_type}"),
            "",
        ),
        (
            "IfStmt",
            1,
            f"batch & (1 * sizeof({element_type}))",
            ("batch@1", "constant:1:int", f"sizeof:{element_type}"),
            "",
        ),
    )


def _validate_neon_control_shape(
    extraction: KernelExtraction, profile: ModelProfile, loop: ControlFact
) -> None:
    if profile.multiphase_widths:
        if profile.multiphase_widths != (64, 8):
            raise CaseEmissionError(
                f"unsupported multi-phase widths {profile.multiphase_widths!r}"
            )
        expected = _S8_VCLAMP_NEON_CONTROL_SHAPE
    elif profile.prefix_tail is not None:
        expected = _byte_tail_control_shape(loop, profile.prefix_tail.element_c_type)
    else:
        expected = (
            (
                loop.kind,
                None,
                loop.condition_text,
                loop.condition_dependencies,
                loop.update_text,
            ),
        )
    actual = _normalized_control_shape(extraction.controls)
    if actual != expected:
        raise CaseEmissionError(
            f"{profile.case_id}: Neon control shape changed: {actual!r}"
        )


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
    _validate_neon_control_shape(extraction, profile, loop)
    emitter = _CaseBlockEmitter(extraction, Architecture.NEON, registry)

    selected_calls = [
        call for call in extraction.calls if call.parent_control in {None, loop.node_id}
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
        if (
            isinstance(spec, StructuralIntrinsic)
            and spec.operation is StructuralOp.LOAD
        ):
            base_argument = call.arguments[0]
            dependency = _single_dependency(base_argument)
            match = re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)@(\d+)", dependency)
            if match is None or match.group(1) not in load_offsets:
                raise CaseEmissionError(
                    f"{profile.case_id}: unsupported Neon load base {dependency!r}"
                )
            base, version_text = match.groups()
            if (
                base_argument.source_text.strip() != base
                or base_argument.semantic_operations
            ):
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
        if (
            isinstance(spec, StructuralIntrinsic)
            and spec.operation is StructuralOp.STORE
        ):
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
        if (
            isinstance(spec, StructuralIntrinsic)
            and spec.operation is StructuralOp.STORE
        ):
            if result is None:
                raise CaseEmissionError(f"{call.spelling} produced no stored value")
            vector = spec.signature.parameters[1].type
            if not isinstance(vector, VectorType) or vector.fixed_lanes is None:
                raise CaseEmissionError(
                    f"{call.spelling} needs a fixed-width stored value"
                )
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
    return (
        emitter.lines,
        " ++ ".join(f"({value})" for value in stores),
        tuple(sorted(expected)),
    )


def _compact_source(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _s8_tail_call_shape(call: IntrinsicCall) -> tuple[object, ...]:
    return (
        call.node_id,
        call.spelling,
        call.assigned_to,
        call.parent_control,
        call.control_path,
        tuple(
            (
                _compact_source(argument.source_text),
                argument.dependencies,
                argument.semantic_operations,
                argument.constant_value,
            )
            for argument in call.arguments
        ),
    )


_S8_TAIL_CONTROL_SHAPES = (
    (
        "control_0000",
        "ForStmt",
        None,
        "batch>=64",
        ("batch@0", "constant:64:int"),
        "batch-=64",
    ),
    (
        "control_0001",
        "ForStmt",
        None,
        "batch>=8",
        ("batch@1", "constant:8:int"),
        "batch-=8",
    ),
    (
        "control_0002",
        "IfStmt",
        None,
        "batch!=0",
        ("batch@2", "constant:0:int"),
        "",
    ),
    (
        "control_0003",
        "IfStmt",
        "control_0002",
        "batch&4",
        ("batch@2", "constant:4:int"),
        "",
    ),
    (
        "control_0004",
        "IfStmt",
        "control_0002",
        "batch&2",
        ("batch@2", "constant:2:int"),
        "",
    ),
    (
        "control_0005",
        "IfStmt",
        "control_0002",
        "batch&1",
        ("batch@2", "constant:1:int"),
        "",
    ),
)


_S8_TAIL_CALL_SHAPES = (
    (
        "call_0018",
        "vld1_s8",
        "vacc@0",
        "control_0001",
        (),
        (("input", ("input@4",), (), None),),
    ),
    (
        "call_0019",
        "vget_low_s8",
        None,
        "control_0001",
        (),
        (("voutput_max", ("voutput_max@0",), (), None),),
    ),
    (
        "call_0020",
        "vmin_s8",
        "vacc@1",
        "control_0001",
        (),
        (
            ("vacc", ("vacc@0",), (), None),
            ("vget_low_s8(voutput_max)", ("call:call_0019",), (), None),
        ),
    ),
    (
        "call_0021",
        "vget_low_s8",
        None,
        "control_0001",
        (),
        (("voutput_min", ("voutput_min@0",), (), None),),
    ),
    (
        "call_0022",
        "vmax_s8",
        "vacc@2",
        "control_0001",
        (),
        (
            ("vacc", ("vacc@1",), (), None),
            ("vget_low_s8(voutput_min)", ("call:call_0021",), (), None),
        ),
    ),
    (
        "call_0023",
        "vst1_s8",
        None,
        "control_0001",
        (),
        (
            ("output", ("output@4",), (), None),
            ("vacc", ("vacc@2",), (), None),
        ),
    ),
    (
        "call_0024",
        "vld1_s8",
        "vacc@3",
        "control_0002",
        ("control_0002:then",),
        (("input", ("input@5",), (), None),),
    ),
    (
        "call_0025",
        "vget_low_s8",
        None,
        "control_0002",
        ("control_0002:then",),
        (("voutput_max", ("voutput_max@0",), (), None),),
    ),
    (
        "call_0026",
        "vmin_s8",
        "vacc@4",
        "control_0002",
        ("control_0002:then",),
        (
            ("vacc", ("vacc@3",), (), None),
            ("vget_low_s8(voutput_max)", ("call:call_0025",), (), None),
        ),
    ),
    (
        "call_0027",
        "vget_low_s8",
        None,
        "control_0002",
        ("control_0002:then",),
        (("voutput_min", ("voutput_min@0",), (), None),),
    ),
    (
        "call_0028",
        "vmax_s8",
        "vacc@5",
        "control_0002",
        ("control_0002:then",),
        (
            ("vacc", ("vacc@4",), (), None),
            ("vget_low_s8(voutput_min)", ("call:call_0027",), (), None),
        ),
    ),
    (
        "call_0029",
        "vreinterpret_u32_s8",
        None,
        "control_0003",
        ("control_0002:then", "control_0003:then"),
        (("vacc", ("vacc@5",), (), None),),
    ),
    (
        "call_0030",
        "vst1_lane_u32",
        None,
        "control_0003",
        ("control_0002:then", "control_0003:then"),
        (
            (
                "(void*)output",
                ("output@5",),
                (
                    "explicit-cast:BitCast:void *",
                    "implicit-cast:BitCast:uint32_t *",
                ),
                None,
            ),
            ("vreinterpret_u32_s8(vacc)", ("call:call_0029",), (), None),
            ("0", ("constant:0:int",), (), 0),
        ),
    ),
    (
        "call_0031",
        "vext_s8",
        "vacc@6",
        "control_0003",
        ("control_0002:then", "control_0003:then"),
        (
            ("vacc", ("vacc@5",), (), None),
            ("vacc", ("vacc@5",), (), None),
            ("4", ("constant:4:int",), (), 4),
        ),
    ),
    (
        "call_0032",
        "vreinterpret_u16_s8",
        None,
        "control_0004",
        ("control_0002:then", "control_0004:then"),
        (("vacc", ("vacc@6",), (), None),),
    ),
    (
        "call_0033",
        "vst1_lane_u16",
        None,
        "control_0004",
        ("control_0002:then", "control_0004:then"),
        (
            (
                "(void*)output",
                ("output@6",),
                (
                    "explicit-cast:BitCast:void *",
                    "implicit-cast:BitCast:uint16_t *",
                ),
                None,
            ),
            ("vreinterpret_u16_s8(vacc)", ("call:call_0032",), (), None),
            ("0", ("constant:0:int",), (), 0),
        ),
    ),
    (
        "call_0034",
        "vext_s8",
        "vacc@7",
        "control_0004",
        ("control_0002:then", "control_0004:then"),
        (
            ("vacc", ("vacc@6",), (), None),
            ("vacc", ("vacc@6",), (), None),
            ("2", ("constant:2:int",), (), 2),
        ),
    ),
    (
        "call_0035",
        "vst1_lane_s8",
        None,
        "control_0005",
        ("control_0002:then", "control_0005:then"),
        (
            ("output", ("output@7",), (), None),
            ("vacc", ("vacc@7",), (), None),
            ("0", ("constant:0:int",), (), 0),
        ),
    ),
)


_S8_TAIL_UPDATE_SHAPES = (
    (
        "input@5",
        "control_0001",
        (),
        "input+=8",
        ("input@4", "constant:8:int"),
    ),
    (
        "output@5",
        "control_0001",
        (),
        "output+=8",
        ("output@4", "constant:8:int"),
    ),
    (
        "batch@2",
        "control_0001",
        (),
        "batch-=8",
        ("batch@1", "constant:8:int"),
    ),
    (
        "input@6",
        "control_0002",
        ("control_0002:then",),
        "input+=8",
        ("input@5", "constant:8:int"),
    ),
    (
        "output@6",
        "control_0003",
        ("control_0002:then", "control_0003:then"),
        "output+=4",
        ("output@5", "constant:4:int"),
    ),
    (
        "output@7",
        "control_0004",
        ("control_0002:then", "control_0004:then"),
        "output+=2",
        ("output@6", "constant:2:int"),
    ),
)


def _validate_s8_tail_source_shape(
    extraction: KernelExtraction,
) -> tuple[IntrinsicCall, ...]:
    actual_controls = tuple(
        (
            control.node_id,
            control.kind,
            control.parent_control,
            _compact_source(control.condition_text),
            control.condition_dependencies,
            _compact_source(control.update_text),
        )
        for control in extraction.controls
    )
    if actual_controls != _S8_TAIL_CONTROL_SHAPES:
        raise CaseEmissionError(
            "s8-vclamp: complete Neon control shape changed: "
            f"expected={_S8_TAIL_CONTROL_SHAPES!r}, actual={actual_controls!r}"
        )

    tail_calls = tuple(extraction.calls[18:])
    actual_calls = tuple(_s8_tail_call_shape(call) for call in tail_calls)
    if actual_calls != _S8_TAIL_CALL_SHAPES:
        raise CaseEmissionError(
            "s8-vclamp: Neon 8-lane/tail call or operand shape changed: "
            f"expected={_S8_TAIL_CALL_SHAPES!r}, actual={actual_calls!r}"
        )

    tail_control_ids = {"control_0001", "control_0002", "control_0003", "control_0004"}
    tail_control_ids.add("control_0005")
    actual_updates = tuple(
        (
            definition.value,
            definition.parent_control,
            definition.control_path,
            _compact_source(definition.expression_text),
            definition.dependencies,
        )
        for definition in extraction.definitions
        if definition.parent_control in tail_control_ids
        and definition.definition_kind.startswith("compound-")
    )
    if actual_updates != _S8_TAIL_UPDATE_SHAPES:
        raise CaseEmissionError(
            "s8-vclamp: Neon 8-lane/tail pointer or count updates changed: "
            f"expected={_S8_TAIL_UPDATE_SHAPES!r}, actual={actual_updates!r}"
        )

    untranslated = [
        definition.value
        for definition in extraction.definitions
        if definition.parent_control in tail_control_ids
        and definition.value_call is None
        and not definition.definition_kind.startswith("compound-")
    ]
    if untranslated:
        raise CaseEmissionError(
            "s8-vclamp: untranslated Neon 8-lane/tail definitions " f"{untranslated!r}"
        )
    return tail_calls


def _new_s8_tail_emitter(
    extraction: KernelExtraction, registry: Mapping[str, IntrinsicSpec]
) -> _CaseBlockEmitter:
    emitter = _CaseBlockEmitter(extraction, Architecture.NEON, registry)
    emitter.environment.update(
        {
            "voutput_max@0": "List.replicate 16 ((p.max).truncate 8)",
            "voutput_min@0": "List.replicate 16 ((p.min).truncate 8)",
        }
    )
    return emitter


def _consume_little_endian_lane_store(
    emitter: _CaseBlockEmitter,
    call: IntrinsicCall,
    *,
    width: int,
    bit: int,
    name: str,
) -> str:
    spec = emitter._lookup_intrinsic(call.spelling)
    if not (
        isinstance(spec, StructuralIntrinsic)
        and spec.operation is StructuralOp.LANE_STORE
    ):
        raise CaseEmissionError(f"{call.spelling}: expected a reviewed lane store")
    emitter._validate_immediates(call, spec)
    value = emitter._resolve(call.arguments[1])
    emitter.consumed.add(call.node_id)
    emitter.lines.append(
        f"  let {name} := if live.testBit {bit} then ({value}).take {width} else []"
    )
    return name


def _emit_multiphase_64_8_tail_value_models(
    extraction: KernelExtraction, registry: Mapping[str, IntrinsicSpec]
) -> tuple[list[str], tuple[str, ...]]:
    """Emit the exact S8 8-lane and live-prefix value adapters.

    Lane stores are interpreted as little-endian byte prefixes only inside this
    adapter. This is not a generic C-memory or endian correspondence rule.
    """

    calls = _validate_s8_tail_source_shape(extraction)
    by_id = {call.node_id: call for call in calls}

    block = _new_s8_tail_emitter(extraction, registry)
    block._bind_call(by_id["call_0018"], "(input).take 8")
    for call_id in ("call_0019", "call_0020", "call_0021", "call_0022"):
        block.emit_registered_call(by_id[call_id])
    block_output = block.emit_registered_call(by_id["call_0023"])
    if block_output is None:
        raise CaseEmissionError("s8-vclamp: 8-lane store produced no value")

    partial = _new_s8_tail_emitter(extraction, registry)
    partial._bind_call(by_id["call_0024"], "(loaded).take 8")
    for call_id in ("call_0025", "call_0026", "call_0027", "call_0028", "call_0029"):
        partial.emit_registered_call(by_id[call_id])

    stored4 = _consume_little_endian_lane_store(
        partial, by_id["call_0030"], width=4, bit=2, name="stored4"
    )
    shifted4 = partial.emit_registered_call(by_id["call_0031"])
    if shifted4 is None:
        raise CaseEmissionError("s8-vclamp: 4-lane slide produced no value")
    partial.lines.append(
        f"  let after4 := if live.testBit 2 then {shifted4} else vacc_5"
    )
    partial.environment["vacc@6"] = "after4"

    partial.emit_registered_call(by_id["call_0032"])
    stored2 = _consume_little_endian_lane_store(
        partial, by_id["call_0033"], width=2, bit=1, name="stored2"
    )
    shifted2 = partial.emit_registered_call(by_id["call_0034"])
    if shifted2 is None:
        raise CaseEmissionError("s8-vclamp: 2-lane slide produced no value")
    partial.lines.append(
        f"  let after2 := if live.testBit 1 then {shifted2} else after4"
    )
    partial.environment["vacc@7"] = "after2"
    stored1 = _consume_little_endian_lane_store(
        partial, by_id["call_0035"], width=1, bit=0, name="stored1"
    )

    expected = {call.node_id for call in calls}
    consumed = block.consumed | partial.consumed
    if consumed != expected:
        raise CaseEmissionError(
            "s8-vclamp: Neon 8-lane/tail call coverage mismatch: "
            f"missing={sorted(expected - consumed)!r}, extra={sorted(consumed - expected)!r}"
        )

    lines = [
        "",
        "/-- Generated value model of the source's reversed-order 8-lane block. -/",
        "def neonBlock8FromIntrinsics (p : S8ClampParams)",
        "    (input : List (BitVec 8)) : List (BitVec 8) :=",
        *block.lines,
        f"  {block_output}",
        "",
        "/-- Generated little-endian live-prefix value abstraction for the 4/2/1 stores.",
        "",
        "This definition does not establish C memory, alignment, aliasing, or endian adequacy.",
        "-/",
        "def neonPartialTailLivePrefixFromIntrinsics (p : S8ClampParams)",
        "    (loaded : List (BitVec 8)) (live : Nat) : List (BitVec 8) :=",
        *partial.lines,
        f"  ({stored4}) ++ ({stored2}) ++ ({stored1})",
        "",
        "/-- Generated value-only lifting of the validated 64/8/4/2/1 control shape.",
        "",
        "`overread` supplies the bytes physically loaded beyond a nonempty short tail.",
        "This definition does not establish that those bytes are legally readable.",
        "-/",
        "def neonValueLoopWithOverreadFromIntrinsics (p : S8ClampParams)",
        "    (input overread : List (BitVec 8)) : List (BitVec 8) :=",
        "  SALT.Kernel.Schedule.runFixedChunkTail 64 (by decide)",
        "    (neonBlock64FromIntrinsics p)",
        "    (SALT.Kernel.Schedule.runFixedChunkTail 8 (by decide)",
        "      (neonBlock8FromIntrinsics p)",
        "      (fun tail =>",
        "        let loaded := (tail ++ overread).take 8",
        "        neonPartialTailLivePrefixFromIntrinsics p loaded tail.length))",
        "    input",
        "",
        "/-- Zero-filled compatibility specialization of the arbitrary-overread model. -/",
        "def neonValueLoopFromIntrinsics (p : S8ClampParams)",
        "    (input : List (BitVec 8)) : List (BitVec 8) :=",
        "  neonValueLoopWithOverreadFromIntrinsics p input",
        "    (List.replicate 7 (0 : BitVec 8))",
    ]
    return lines, tuple(sorted(expected))


def _tail_control_path(
    root: ControlFact, child: ControlFact | None = None
) -> tuple[str, ...]:
    path = (f"{root.node_id}:then",)
    if child is not None:
        path += (f"{child.node_id}:then",)
    return path


def _role_argument_names(prefix: str, inputs: tuple[str, ...]) -> tuple[str, ...]:
    if len(inputs) == 1:
        return (prefix,)
    names: list[str] = []
    for input_name in inputs:
        role = input_name.removeprefix("input_")
        parts = role.split("_")
        if not role or any(
            re.fullmatch(r"[A-Za-z][A-Za-z0-9]*", part) is None for part in parts
        ):
            raise CaseEmissionError(
                f"cannot derive a Lean tail role from input {input_name!r}"
            )
        suffix = "".join(part[0].upper() + part[1:] for part in parts)
        names.append(f"{prefix}{suffix}")
    if len(set(names)) != len(names):
        raise CaseEmissionError(f"duplicate generated tail arguments {names!r}")
    return tuple(names)


def _loaded_argument_names(inputs: tuple[str, ...]) -> tuple[str, ...]:
    return _role_argument_names("loaded", inputs)


def _overread_argument_names(inputs: tuple[str, ...]) -> tuple[str, ...]:
    return _role_argument_names("overread", inputs)


def _emit_prefix_tail_value_models(
    extraction: KernelExtraction,
    profile: ModelProfile,
    registry: Mapping[str, IntrinsicSpec],
    already_consumed: tuple[str, ...],
) -> tuple[list[str], tuple[str, ...]]:
    """Emit one reviewed fixed-block plus little-endian prefix-tail schedule."""

    config = profile.prefix_tail
    if config is None:
        raise CaseEmissionError(f"{profile.case_id}: no prefix-tail profile")
    if len(profile.inputs) not in {1, 2}:
        raise CaseEmissionError(
            f"{profile.case_id}: prefix-tail value loops support one or two inputs"
        )
    input_names = profile.inputs
    main = _selected_neon_loop(extraction, profile)
    roots = [
        control
        for control in extraction.controls
        if control.kind == "IfStmt"
        and control.parent_control is None
        and control.condition_text == "batch != 0"
    ]
    if len(roots) != 1:
        raise CaseEmissionError(
            f"{profile.case_id}: expected one nonempty prefix-tail guard"
        )
    root = roots[0]
    children = [
        control
        for control in extraction.controls
        if control.parent_control == root.node_id
    ]
    expected_conditions = [
        f"batch & ({width} * sizeof({config.element_c_type}))"
        for width in config.store_widths
    ]
    if [control.condition_text for control in children] != expected_conditions:
        raise CaseEmissionError(
            f"{profile.case_id}: prefix-tail branch order or widths changed"
        )

    consumed_before = set(already_consumed)
    tail_controls = {root.node_id, *(control.node_id for control in children)}
    tail_calls = [
        call for call in extraction.calls if call.node_id not in consumed_before
    ]
    if not tail_calls or any(
        call.parent_control not in tail_controls for call in tail_calls
    ):
        raise CaseEmissionError(
            f"{profile.case_id}: calls outside the reviewed prefix-tail remain"
        )

    emitter = _CaseBlockEmitter(extraction, Architecture.NEON, registry)
    prologue_calls = [call for call in extraction.calls if call.parent_control is None]
    for call in prologue_calls:
        spec = emitter._lookup_intrinsic(call.spelling)
        if not (
            isinstance(spec, StructuralIntrinsic)
            and spec.operation is StructuralOp.BROADCAST
        ):
            raise CaseEmissionError(
                f"{profile.case_id}: prefix-tail prologue must contain broadcasts only"
            )
        emitter.emit_registered_call(call)

    root_calls = [call for call in tail_calls if call.parent_control == root.node_id]
    if not root_calls:
        raise CaseEmissionError(f"{profile.case_id}: prefix tail has no value pipeline")
    if any(call.control_path != _tail_control_path(root) for call in root_calls):
        raise CaseEmissionError(f"{profile.case_id}: prefix-tail root path changed")
    if len(root_calls) <= len(input_names):
        raise CaseEmissionError(f"{profile.case_id}: prefix-tail pipeline is empty")
    loaded_names = _loaded_argument_names(input_names)
    for load, input_name, loaded_name in zip(
        root_calls[: len(input_names)], input_names, loaded_names
    ):
        load_spec = emitter._lookup_intrinsic(load.spelling)
        if not (
            isinstance(load_spec, StructuralIntrinsic)
            and load_spec.operation is StructuralOp.LOAD
            and isinstance(load_spec.signature.result, VectorType)
            and load_spec.signature.result.fixed_lanes == config.load_lanes
        ):
            raise CaseEmissionError(
                f"{profile.case_id}: prefix tail must begin with one "
                f"{config.load_lanes}-lane load per input"
            )
        load_base = load.arguments[0]
        if (
            load_base.dependencies != (f"{input_name}@1",)
            or load_base.source_text.strip() != input_name
            or load_base.semantic_operations
        ):
            raise CaseEmissionError(
                f"{profile.case_id}: prefix-tail load base changed for {input_name}"
            )
        emitter._bind_call(load, f"({loaded_name}).take {config.load_lanes}")

    tail_value: str | None = None
    tail_dependency: str | None = None
    value_calls = root_calls[len(input_names) :]
    for index, call in enumerate(value_calls):
        spec = emitter._lookup_intrinsic(call.spelling)
        if isinstance(spec, StructuralIntrinsic) and spec.operation in {
            StructuralOp.LOAD,
            StructuralOp.STORE,
            StructuralOp.LANE_STORE,
        }:
            raise CaseEmissionError(
                f"{profile.case_id}: load or store appeared inside the tail value pipeline"
            )
        emitted_value = emitter.emit_registered_call(call)
        if emitted_value is None:
            raise CaseEmissionError(
                f"{profile.case_id}: tail value pipeline call produced no value"
            )
        if call.assigned_to is None:
            dependency = f"call:{call.node_id}"
            if not any(
                dependency in later.dependencies for later in value_calls[index + 1 :]
            ):
                raise CaseEmissionError(
                    f"{profile.case_id}: expression-only tail call {call.spelling} "
                    "is not consumed by a later call"
                )
            continue
        tail_value = emitted_value
        tail_dependency = call.assigned_to
    if tail_value is None or tail_dependency is None:
        raise CaseEmissionError(f"{profile.case_id}: prefix-tail pipeline is empty")

    main_store_count = sum(
        1
        for call in extraction.calls
        if call.parent_control == main.node_id
        and isinstance(emitter._lookup_intrinsic(call.spelling), StructuralIntrinsic)
        and emitter._lookup_intrinsic(call.spelling).operation is StructuralOp.STORE
    )
    output_version = main_store_count
    stored_values: list[str] = []
    expected_updates: list[tuple[str, str, tuple[str, ...], str, tuple[str, ...]]] = []

    for index, (child, width) in enumerate(zip(children, config.store_widths)):
        branch_calls = [
            call for call in tail_calls if call.parent_control == child.node_id
        ]
        if any(
            call.control_path != _tail_control_path(root, child)
            for call in branch_calls
        ):
            raise CaseEmissionError(
                f"{profile.case_id}: prefix-tail branch path changed for width {width}"
            )
        expected_count = 1 if index == len(children) - 1 else 3
        if len(branch_calls) != expected_count:
            raise CaseEmissionError(
                f"{profile.case_id}: width-{width} branch has {len(branch_calls)} calls; "
                f"expected {expected_count}"
            )

        lane_store_index = 0
        stored_dependency = tail_dependency
        if len(branch_calls) == 3:
            bitcast = branch_calls[0]
            bitcast_spec = emitter._lookup_intrinsic(bitcast.spelling)
            if not (
                isinstance(bitcast_spec, StructuralIntrinsic)
                and bitcast_spec.operation is StructuralOp.BITCAST
                and bitcast.arguments[0].dependencies == (tail_dependency,)
            ):
                raise CaseEmissionError(
                    f"{profile.case_id}: width-{width} branch needs a current-value bitcast"
                )
            emitter.emit_registered_call(bitcast)
            stored_dependency = f"call:{bitcast.node_id}"
            lane_store_index = 1

        lane_store = branch_calls[lane_store_index]
        lane_spec = emitter._lookup_intrinsic(lane_store.spelling)
        pointer_type = lane_spec.signature.parameters[0].type
        pointer_argument = lane_store.arguments[0]
        value_argument = lane_store.arguments[1]
        expected_pointer_source = "output" if width == 1 else "(void*)output"
        expected_pointer_operations = (
            ()
            if width == 1
            else (
                "explicit-cast:BitCast:void *",
                f"implicit-cast:BitCast:uint{width * 8}_t *",
            )
        )
        if not (
            isinstance(lane_spec, StructuralIntrinsic)
            and lane_spec.operation is StructuralOp.LANE_STORE
            and isinstance(pointer_type, PointerType)
            and pointer_type.pointee.bit_width == width * 8
            and pointer_argument.dependencies == (f"output@{output_version}",)
            and _compact_source(pointer_argument.source_text) == expected_pointer_source
            and pointer_argument.semantic_operations == expected_pointer_operations
            and value_argument.dependencies == (stored_dependency,)
            and not value_argument.semantic_operations
        ):
            raise CaseEmissionError(
                f"{profile.case_id}: width-{width} lane-store shape changed"
            )
        stored_values.append(
            _consume_little_endian_lane_store(
                emitter,
                lane_store,
                width=width,
                bit=width.bit_length() - 1,
                name=f"stored{width}",
            )
        )

        if index == len(children) - 1:
            continue
        slide = branch_calls[-1]
        slide_spec = emitter._lookup_intrinsic(slide.spelling)
        slide_definition = (
            None
            if slide.assigned_to is None
            else emitter.definitions.get(slide.assigned_to)
        )
        if not (
            isinstance(slide_spec, StructuralIntrinsic)
            and slide_spec.operation is StructuralOp.EXTRACT_FROM_CONCAT
            and slide.assigned_to is not None
            and slide_definition is not None
            and slide_definition.definition_kind == "assignment"
            and slide_definition.value_call == slide.node_id
            and slide.arguments[0].dependencies == (tail_dependency,)
            and slide.arguments[1].dependencies == (tail_dependency,)
            and slide.arguments[2].constant_value == width
        ):
            raise CaseEmissionError(
                f"{profile.case_id}: width-{width} conditional slide changed"
            )
        shifted = emitter.emit_registered_call(slide)
        if shifted is None:
            raise CaseEmissionError(
                f"{profile.case_id}: width-{width} slide produced no value"
            )
        joined = f"after{width}"
        emitter.lines.append(
            f"  let {joined} := if live.testBit {width.bit_length() - 1} "
            f"then {shifted} else {tail_value}"
        )
        emitter.environment[slide.assigned_to] = joined
        tail_dependency = slide.assigned_to
        tail_value = joined

        next_version = output_version + 1
        expected_updates.append(
            (
                f"output@{next_version}",
                child.node_id,
                _tail_control_path(root, child),
                f"output+={width}",
                (f"output@{output_version}", f"constant:{width}:int"),
            )
        )
        output_version = next_version

    if config.input_advances_after_load:
        expected_updates[0:0] = [
            (
                f"{input_name}@2",
                root.node_id,
                _tail_control_path(root),
                f"{input_name}+={config.load_lanes}",
                (f"{input_name}@1", f"constant:{config.load_lanes}:int"),
            )
            for input_name in input_names
        ]
    actual_updates = [
        (
            definition.value,
            definition.parent_control,
            definition.control_path,
            _compact_source(definition.expression_text),
            definition.dependencies,
        )
        for definition in extraction.definitions
        if definition.parent_control in tail_controls
        and definition.definition_kind.startswith("compound-")
    ]
    if actual_updates != expected_updates:
        raise CaseEmissionError(
            f"{profile.case_id}: prefix-tail pointer updates changed: "
            f"{actual_updates!r}"
        )
    untranslated = [
        definition.value
        for definition in extraction.definitions
        if definition.parent_control in tail_controls
        and definition.value_call is None
        and not definition.definition_kind.startswith("compound-")
    ]
    if untranslated:
        raise CaseEmissionError(
            f"{profile.case_id}: untranslated prefix-tail definitions {untranslated!r}"
        )

    expected_tail = {call.node_id for call in tail_calls}
    consumed_tail = emitter.consumed - {call.node_id for call in prologue_calls}
    if consumed_tail != expected_tail:
        raise CaseEmissionError(
            f"{profile.case_id}: prefix-tail call coverage mismatch: "
            f"missing={sorted(expected_tail - consumed_tail)!r}, "
            f"extra={sorted(consumed_tail - expected_tail)!r}"
        )

    width = profile.neon_block_lanes
    padding = config.load_lanes - 1
    loaded_parameters = " ".join(loaded_names)
    partial_application = " ".join(loaded_names)
    overread_description = (
        "`overread` supplies the bytes physically loaded beyond a nonempty short tail."
        if len(input_names) == 1
        else "`overreadA` and `overreadB` supply the bytes physically loaded beyond "
        "a nonempty short tail."
    )
    if len(input_names) == 1:
        input_name = input_names[0]
        value_loop_parameters = [
            f"    ({input_name} overread : List (BitVec 8)) : List (BitVec 8) :=",
        ]
        tail_loader_lines = [
            f"      let {loaded_names[0]} := (tail ++ overread).take {config.load_lanes}",
            f"      neonPartialTailLivePrefixFromIntrinsics p {partial_application} tail.length)",
        ]
        schedule_lines = [
            f"  SALT.Kernel.Schedule.runFixedChunkTail {width} (by decide)",
            f"    ({profile.neon_function} p)",
            "    (fun tail =>",
            *tail_loader_lines,
            f"    {input_name}",
        ]
        compatibility_parameters = [
            f"    ({input_name} : List (BitVec 8)) : List (BitVec 8) :=",
        ]
        compatibility_arguments = [
            f"  neonValueLoopWithOverreadFromIntrinsics p {input_name}",
            f"    (List.replicate {padding} (0 : BitVec 8))",
        ]
    else:
        input_a, input_b = input_names
        overread_names = _overread_argument_names(input_names)
        overread_a, overread_b = overread_names
        loaded_a, loaded_b = loaded_names
        value_loop_parameters = [
            f"    ({input_a} {input_b} {overread_a} {overread_b} : List (BitVec 8))",
            f"    (sameLength : {input_a}.length = {input_b}.length) : List (BitVec 8) :=",
        ]
        schedule_lines = [
            f"  SALT.Kernel.Schedule.runFixedChunkTail2 {width} (by decide)",
            f"    ({profile.neon_function} p)",
            "    (fun tailA tailB =>",
            f"      let {loaded_a} := (tailA ++ {overread_a}).take {config.load_lanes}",
            f"      let {loaded_b} := (tailB ++ {overread_b}).take {config.load_lanes}",
            f"      neonPartialTailLivePrefixFromIntrinsics p {partial_application} tailA.length)",
            f"    {input_a} {input_b} sameLength",
        ]
        compatibility_parameters = [
            f"    ({input_a} {input_b} : List (BitVec 8))",
            f"    (sameLength : {input_a}.length = {input_b}.length) : List (BitVec 8) :=",
        ]
        compatibility_arguments = [
            f"  neonValueLoopWithOverreadFromIntrinsics p {input_a} {input_b}",
            f"    (List.replicate {padding} (0 : BitVec 8))",
            f"    (List.replicate {padding} (0 : BitVec 8)) sameLength",
        ]

    lines = [
        "",
        "/-- Generated little-endian live-prefix value abstraction for the reviewed tail stores.",
        "",
        "This definition does not establish C memory, alignment, aliasing, or endian adequacy.",
        "-/",
        f"def neonPartialTailLivePrefixFromIntrinsics (p : {profile.parameter_type})",
        f"    ({loaded_parameters} : List (BitVec 8)) (live : Nat) : List (BitVec 8) :=",
        *emitter.lines,
        "  " + " ++ ".join(f"({value})" for value in stored_values),
        "",
        f"/-- Generated value-only lifting of the validated {width}/{'/'.join(map(str, config.store_widths))} control shape.",
        "",
        overread_description,
        "This definition does not establish that those bytes are legally readable.",
        "-/",
        f"def neonValueLoopWithOverreadFromIntrinsics (p : {profile.parameter_type})",
        *value_loop_parameters,
        *schedule_lines,
        "",
        "/-- Zero-filled compatibility specialization of the explicit-overread model. -/",
        f"def neonValueLoopFromIntrinsics (p : {profile.parameter_type})",
        *compatibility_parameters,
        *compatibility_arguments,
    ]
    return lines, tuple(sorted(expected_tail))


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
            or not definition.dependencies[0].startswith("field:params@0.scalar.")
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
        if (
            definition.parent_control is not None
            or definition.definition_kind == "parameter"
        ):
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

    accumulator_dependencies = right.arguments[0].dependencies
    accumulator_dependency = (
        accumulator_dependencies[0] if len(accumulator_dependencies) == 1 else ""
    )
    accumulator_match = re.fullmatch(
        r"([A-Za-z_][A-Za-z0-9_]*)@(\d+)", accumulator_dependency
    )
    right_match = (
        None
        if right.assigned_to is None
        else re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)@(\d+)", right.assigned_to)
    )
    left_match = (
        None
        if left.assigned_to is None
        else re.fullmatch(r"([A-Za-z_][A-Za-z0-9_]*)@(\d+)", left.assigned_to)
    )
    right_definition = (
        None
        if right.assigned_to is None
        else emitter.definitions.get(right.assigned_to)
    )
    left_definition = (
        None if left.assigned_to is None else emitter.definitions.get(left.assigned_to)
    )
    call_positions = {
        call.node_id: index for index, call in enumerate(emitter.extraction.calls)
    }
    left_position = call_positions[left.node_id]
    later_calls = emitter.extraction.calls[left_position + 1 :]
    first_consumer = later_calls[0] if later_calls else None

    if (
        right.assigned_to is None
        or left.assigned_to is None
        or accumulator_match is None
        or right_match is None
        or left_match is None
        or accumulator_match.group(1) != right_match.group(1)
        or right_match.group(1) != left_match.group(1)
        or int(right_match.group(2)) != int(accumulator_match.group(2)) + 1
        or int(left_match.group(2)) != int(right_match.group(2)) + 1
        or right_definition is None
        or left_definition is None
        or right_definition.definition_kind != "assignment"
        or left_definition.definition_kind != "assignment"
        or right_definition.value_call != right.node_id
        or left_definition.value_call != left.node_id
        or first_consumer is None
        or not first_consumer.arguments
        or first_consumer.arguments[0].dependencies != (left.assigned_to,)
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
        raise CaseEmissionError(
            "RVV signed-shift branch has no reviewed shift"
        ) from error
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
    if child_controls and not profile.rvv_signed_shift_branch:
        raise CaseEmissionError(
            f"{profile.case_id}: nested RVV control needs a reviewed adapter"
        )
    if profile.rvv_signed_shift_branch:
        if len(child_controls) != 1:
            raise CaseEmissionError(
                f"{profile.case_id}: expected one signed-shift child branch"
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
    loaded_inputs: list[str] = []
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
            raise CaseEmissionError(
                f"{profile.case_id}: RVV data operation precedes vsetvl"
            )
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
        if (
            isinstance(spec, StructuralIntrinsic)
            and spec.operation is StructuralOp.LOAD
        ):
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
            if (
                base_argument.source_text.strip() != base
                or base_argument.semantic_operations
            ):
                raise CaseEmissionError(
                    f"{profile.case_id}: unsupported RVV load expression "
                    f"{base_argument.source_text!r}"
                )
            loaded_inputs.append(base)
            emitter._bind_call(call, base)
            continue
        if (
            isinstance(spec, StructuralIntrinsic)
            and spec.operation is StructuralOp.STORE
        ):
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
        if (
            isinstance(spec, StructuralIntrinsic)
            and spec.operation is StructuralOp.STORE
        ):
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
    if loaded_inputs != list(profile.inputs):
        raise CaseEmissionError(
            f"{profile.case_id}: RVV load footprint/order changed: {loaded_inputs!r}"
        )
    expected_updates = [
        (f"{input_name}@1", f"{input_name} += vl") for input_name in profile.inputs
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
        f"  {field.name} : BitVec {field.width}" for field in profile.parameter_fields
    )
    lines.append("  deriving Repr, DecidableEq")
    return lines


def _function_header(name: str, profile: ModelProfile) -> list[str]:
    lines = [f"def {name} (p : {profile.parameter_type})"]
    lines.extend(
        f"    ({input_name} : List (BitVec 8))" for input_name in profile.inputs
    )
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
    """Emit reviewed models for one pair, including any validated case adapter."""

    if neon.facade_sha256 != rvv.facade_sha256:
        raise CaseEmissionError(f"{profile.case_id}: parse facades differ across sides")
    neon_lines, neon_output, neon_consumed = _emit_neon_case(
        neon, profile, neon_registry
    )
    neon_extra_lines: list[str] = []
    if profile.multiphase_widths:
        neon_extra_lines, tail_consumed = _emit_multiphase_64_8_tail_value_models(
            neon, neon_registry
        )
        overlap = set(neon_consumed) & set(tail_consumed)
        if overlap:
            raise CaseEmissionError(
                f"multi-phase: duplicate Neon call consumption {sorted(overlap)!r}"
            )
        combined = set(neon_consumed) | set(tail_consumed)
        all_calls = {call.node_id for call in neon.calls}
        if combined != all_calls:
            raise CaseEmissionError(
                "multi-phase: complete Neon value-call coverage mismatch: "
                f"missing={sorted(all_calls - combined)!r}, "
                f"extra={sorted(combined - all_calls)!r}"
            )
        neon_consumed = tuple(sorted(combined))
    elif profile.prefix_tail is not None:
        neon_extra_lines, tail_consumed = _emit_prefix_tail_value_models(
            neon, profile, neon_registry, neon_consumed
        )
        overlap = set(neon_consumed) & set(tail_consumed)
        if overlap:
            raise CaseEmissionError(
                f"{profile.case_id}: duplicate Neon call consumption {sorted(overlap)!r}"
            )
        combined = set(neon_consumed) | set(tail_consumed)
        all_calls = {call.node_id for call in neon.calls}
        if combined != all_calls:
            raise CaseEmissionError(
                f"{profile.case_id}: complete Neon value-call coverage mismatch: "
                f"missing={sorted(all_calls - combined)!r}, "
                f"extra={sorted(combined - all_calls)!r}"
            )
        neon_consumed = tuple(sorted(combined))
    rvv_lines, rvv_output, rvv_consumed = _emit_rvv_case(rvv, profile, rvv_registry)
    rvv_extra_lines: list[str] = []
    if profile.prefix_tail is not None:
        if len(profile.inputs) not in {1, 2}:
            raise CaseEmissionError(
                f"{profile.case_id}: RVV value loops support one or two inputs"
            )
        rvv_extra_lines = [
            "",
            "/-- Generated value-only lifting of the validated RVV strip-mined loop.",
            "",
            "A positive partition abstracts active lengths; ISA `vsetvl` legality is separate.",
            "-/",
            f"def rvvValueLoopFromIntrinsics (p : {profile.parameter_type})",
        ]
        if len(profile.inputs) == 1:
            input_name = profile.inputs[0]
            rvv_extra_lines.extend(
                [
                    f"    ({input_name} : List (BitVec 8))",
                    "    (schedule : SALT.Kernel.Schedule.PositivePartition "
                    f"{input_name}.length) :",
                    "    List (BitVec 8) :=",
                    "  SALT.Kernel.Schedule.processBlocks "
                    f"(rvvChunkFromIntrinsics p) {input_name} schedule",
                ]
            )
        else:
            input_a, input_b = profile.inputs
            rvv_extra_lines.extend(
                [
                    f"    ({input_a} {input_b} : List (BitVec 8))",
                    f"    (sameLength : {input_a}.length = {input_b}.length)",
                    "    (schedule : SALT.Kernel.Schedule.PositivePartition "
                    f"{input_a}.length) :",
                    "    List (BitVec 8) :=",
                    "  SALT.Kernel.Schedule.processBlocks2 "
                    f"(rvvChunkFromIntrinsics p) {input_a} {input_b} "
                    "sameLength schedule",
                ]
            )
    schedule_import = (
        ["import SALT.Kernel.Schedule"]
        if profile.multiphase_widths or profile.prefix_tail is not None
        else []
    )
    lines = [
        "-- This file is generated. Do not edit the models by hand.",
        "import SALT.Intrinsics.Neon",
        "import SALT.Intrinsics.RVV",
        *schedule_import,
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
        *neon_extra_lines,
        "",
        *_function_header(profile.rvv_function, profile),
        *rvv_lines,
        f"  {rvv_output}",
        *rvv_extra_lines,
        "",
        f"end {profile.lean_namespace}",
        "",
    ]
    emitted = EmittedPair("\n".join(lines), profile.neon_function, profile.rvv_function)
    return CaseEmission(emitted, neon_consumed, rvv_consumed)
