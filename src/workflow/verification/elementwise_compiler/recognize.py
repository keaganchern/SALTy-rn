"""Fail-closed scalar-layout and execution-family recognition."""

from __future__ import annotations

import dataclasses
import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from workflow.verification.lean_backend.frontend import KernelExtraction

from .capabilities import (
    LayoutKind,
    LayoutViewCapability,
    ScheduleFamilyCapability,
    ScheduleKind,
)
from .contracts import ParsedAssertion, translate_assertions
from .schema import (
    Architecture,
    ContractBinding,
    ElementwiseSchemaError,
    LayoutInstance,
    LocalAssertionFact,
    ScheduleInstance,
    canonical_sha256,
)


class RecognitionError(ElementwiseSchemaError):
    def __init__(self, status: str, detail: str) -> None:
        super().__init__(detail)
        self.status = status
        self.detail = detail


@dataclass(frozen=True, slots=True)
class FixedSchedule:
    kind: ScheduleKind
    count_variable: str
    lanes: int
    element_c_type: str
    store_widths: tuple[int, ...]
    loop_control: str
    tail_control: str | None


@dataclass(frozen=True, slots=True)
class RvvSchedule:
    count_variable: str
    loop_control: str
    nested_controls: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PairRecognition:
    contracts: ContractBinding
    layout_capability: LayoutViewCapability
    schedule_capabilities: tuple[ScheduleFamilyCapability, ScheduleFamilyCapability]
    layout: LayoutInstance
    schedules: tuple[ScheduleInstance, ScheduleInstance]
    local_assertions: tuple[LocalAssertionFact, ...]
    consumed_effects_sha256: str
    inputs: tuple[str, ...]
    output: str
    element_c_type: str
    element_width: int
    neon: FixedSchedule
    rvv: RvvSchedule


_FIXED_CONDITION = re.compile(
    r"^(?P<count>[A-Za-z_][A-Za-z0-9_]*)\s*>=\s*(?P<lanes>[0-9]+)"
    r"(?:\s*\*\s*sizeof\((?P<element>[A-Za-z_][A-Za-z0-9_ ]*)\))?$"
)
_FIXED_UPDATE = re.compile(
    r"^(?P<count>[A-Za-z_][A-Za-z0-9_]*)\s*-=\s*(?P<lanes>[0-9]+)"
    r"(?:\s*\*\s*sizeof\((?P<element>[A-Za-z_][A-Za-z0-9_ ]*)\))?$"
)
_TAIL_BIT = re.compile(
    r"^(?P<count>[A-Za-z_][A-Za-z0-9_]*)\s*&\s*\(?(?P<width>[0-9]+)"
    r"\s*\*\s*sizeof\((?P<element>[A-Za-z_][A-Za-z0-9_ ]*)\)\)?$"
)
_WIDTHS = {
    "signed char": 8,
    "unsigned char": 8,
    "char": 8,
    "int8_t": 8,
    "uint8_t": 8,
    "short": 16,
    "unsigned short": 16,
    "int16_t": 16,
    "uint16_t": 16,
    "int": 32,
    "unsigned int": 32,
    "float": 32,
    "int32_t": 32,
    "uint32_t": 32,
}
_ELEMENT_CANONICAL = {
    "signed char": "i8",
    "char": "i8",
    "int8_t": "i8",
    "unsigned char": "u8",
    "uint8_t": "u8",
    "float": "f32",
}


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _compact(text: str) -> str:
    return re.sub(r"\s+", "", text)


def _normalized_type(type_spelling: str) -> str:
    value = re.sub(r"\b(const|volatile|restrict|__restrict|__restrict__)\b", "", type_spelling)
    return " ".join(value.replace("*", " * ").split())


def _pointer_element(type_spelling: str) -> tuple[str, bool] | None:
    if "*" not in type_spelling or "struct " in type_spelling:
        return None
    is_const = bool(re.search(r"\bconst\b", type_spelling.split("*", 1)[0]))
    element = _normalized_type(type_spelling).split("*", 1)[0].strip()
    return element, is_const


def _layout_streams(extraction: KernelExtraction) -> tuple[tuple[str, ...], str, str, int]:
    inputs: list[str] = []
    outputs: list[str] = []
    elements: set[str] = set()
    for parameter in extraction.parameters:
        pointer = _pointer_element(parameter.type_spelling)
        if pointer is None:
            continue
        element, is_const = pointer
        elements.add(element)
        (inputs if is_const else outputs).append(parameter.name)
    if not inputs or len(outputs) != 1:
        raise RecognitionError(
            "layout-unrecognized",
            f"scalar-lane layout needs input streams and one output; got inputs={inputs!r}, outputs={outputs!r}",
        )
    if len(elements) != 1:
        raise RecognitionError(
            "layout-unrecognized", f"scalar-lane streams use different element types {sorted(elements)!r}"
        )
    element = next(iter(elements))
    width = _WIDTHS.get(element)
    if width is None:
        raise RecognitionError("layout-unrecognized", f"unsupported scalar element type {element!r}")
    return tuple(inputs), outputs[0], element, width


def _capabilities(repository_root: Path) -> tuple[
    LayoutViewCapability,
    dict[tuple[Architecture, ScheduleKind], ScheduleFamilyCapability],
]:
    recognizer = _sha256(Path(__file__).resolve())
    schedule_path = repository_root / "src/verification_bw/lean/SALT/Kernel/Schedule.lean"
    family_path = repository_root / "src/verification_bw/lean/SALT/Kernel/ElementwiseFamily.lean"
    layout_path = repository_root / "src/verification_bw/lean/SALT/Kernel/ElementwiseLayout.lean"
    if any(not path.is_file() for path in (schedule_path, family_path, layout_path)):
        raise RecognitionError("family-unrecognized", "SALT elementwise theorem module is absent")
    schedule_sha = _sha256(schedule_path)
    family_sha = _sha256(family_path)
    layout_sha = _sha256(layout_path)
    layout = LayoutViewCapability(
        LayoutKind.SCALAR_LANE,
        recognizer,
        "SALT.Kernel.ElementwiseLayout.scalarLaneView_eq_self",
        layout_sha,
    )
    result: dict[tuple[Architecture, ScheduleKind], ScheduleFamilyCapability] = {}
    symbols = {
        ScheduleKind.FIXED_NO_TAIL: ("SALT.Kernel.ElementwiseFamily.runFixedNoTail_eq_map",),
        ScheduleKind.FIXED_TAIL: ("SALT.Kernel.Schedule.runFixedChunkTail_eq_map",),
        ScheduleKind.MULTI_PHASE: ("SALT.Kernel.Schedule.runFixedChunkTail_eq_map",),
        ScheduleKind.RVV_STRIP_MINE: ("SALT.Kernel.Schedule.processBlocks_eq_map",),
    }
    for architecture, kinds in (
        (Architecture.NEON, (ScheduleKind.FIXED_NO_TAIL, ScheduleKind.FIXED_TAIL, ScheduleKind.MULTI_PHASE)),
        (Architecture.RVV, (ScheduleKind.RVV_STRIP_MINE,)),
    ):
        for kind in kinds:
            result[(architecture, kind)] = ScheduleFamilyCapability(
                architecture,
                kind,
                recognizer,
                tuple(sorted(symbols[kind])),
                family_sha if kind is ScheduleKind.FIXED_NO_TAIL else schedule_sha,
            )
    return layout, result


def _top_controls(extraction: KernelExtraction) -> tuple[object, ...]:
    return tuple(control for control in extraction.controls if control.parent_control is None)


def _recognize_fixed(extraction: KernelExtraction) -> FixedSchedule:
    top = _top_controls(extraction)
    loops = tuple(control for control in top if control.kind == "ForStmt")
    if len(loops) != 1:
        if len(loops) > 1 or any(control.kind == "DoStmt" for control in top):
            raise RecognitionError("family-unrecognized", "Neon control is multi-phase")
        raise RecognitionError("family-unrecognized", "Neon needs one top-level fixed loop")
    loop = loops[0]
    condition = _FIXED_CONDITION.fullmatch(loop.condition_text.strip())
    update = _FIXED_UPDATE.fullmatch(loop.update_text.strip())
    if condition is None or update is None:
        raise RecognitionError(
            "family-unrecognized",
            f"unsupported fixed loop condition/update {loop.condition_text!r}/{loop.update_text!r}",
        )
    condition_element = condition.group("element") or "signed char"
    update_element = update.group("element") or condition_element
    if (
        condition.group("count") != update.group("count")
        or condition.group("lanes") != update.group("lanes")
        or condition_element != update_element
    ):
        raise RecognitionError("family-unrecognized", "fixed loop guard and update disagree")
    lanes = int(condition.group("lanes"))
    nonloops = tuple(control for control in top if control.node_id != loop.node_id)
    if not nonloops:
        return FixedSchedule(
            ScheduleKind.FIXED_NO_TAIL,
            condition.group("count"),
            lanes,
            condition_element,
            (),
            loop.node_id,
            None,
        )
    if len(nonloops) != 1 or nonloops[0].kind != "IfStmt":
        raise RecognitionError("family-unrecognized", "fixed loop has unsupported trailing control")
    tail = nonloops[0]
    if _compact(tail.condition_text) != f"{condition.group('count')}!=0":
        raise RecognitionError("family-unrecognized", "tail branch is not the nonzero remainder")
    children = tuple(
        control
        for control in extraction.controls
        if control.parent_control == tail.node_id and control.kind == "IfStmt"
    )
    widths: list[int] = []
    for child in children:
        match = _TAIL_BIT.fullmatch(child.condition_text.strip())
        if (
            match is None
            or match.group("count") != condition.group("count")
            or match.group("element") != condition_element
        ):
            raise RecognitionError(
                "family-unrecognized", f"unsupported tail store condition {child.condition_text!r}"
            )
        widths.append(int(match.group("width")))
    expected = tuple(1 << bit for bit in reversed(range((lanes - 1).bit_length())))
    expected = tuple(width for width in expected if width < lanes)
    if tuple(widths) != expected or sum(widths) != lanes - 1:
        raise RecognitionError(
            "family-unrecognized", f"tail widths {tuple(widths)!r} do not encode 1..{lanes - 1}"
        )
    return FixedSchedule(
        ScheduleKind.FIXED_TAIL,
        condition.group("count"),
        lanes,
        condition_element,
        tuple(widths),
        loop.node_id,
        tail.node_id,
    )


def _recognize_rvv(extraction: KernelExtraction) -> RvvSchedule:
    top = _top_controls(extraction)
    loops = tuple(control for control in top if control.kind == "WhileStmt")
    if len(loops) != 1 or len(top) != 1:
        raise RecognitionError("family-unrecognized", "RVV needs one top-level strip-mined while loop")
    loop = loops[0]
    match = re.fullmatch(
        r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*>\s*0\s*", loop.condition_text
    )
    if match is None:
        raise RecognitionError("family-unrecognized", "RVV loop guard is not positive remaining length")
    nested = tuple(
        control.node_id
        for control in extraction.controls
        if control.parent_control == loop.node_id
    )
    if any(
        control.kind != "IfStmt"
        for control in extraction.controls
        if control.parent_control == loop.node_id
    ):
        raise RecognitionError("family-unrecognized", "RVV has unsupported nested control")
    return RvvSchedule(match.group(1), loop.node_id, nested)


def _assertion_digest(source_text: str) -> str:
    return hashlib.sha256(source_text.encode("utf-8")).hexdigest()


def _derive_local_assertions(
    local: tuple[ParsedAssertion, ...],
    schedule: FixedSchedule,
) -> tuple[LocalAssertionFact, ...]:
    if not local:
        return ()
    if schedule.kind is not ScheduleKind.FIXED_TAIL or schedule.tail_control is None:
        raise RecognitionError("family-unrecognized", "local assertion has no recognized tail path")
    count = schedule.count_variable
    element = schedule.element_c_type
    allowed = {
        f"assert({count}>=1*sizeof({element}));",
        f"assert({count}<={schedule.lanes - 1}*sizeof({element}));",
        f"assert({count}%sizeof({element})==0);",
    }
    result: list[LocalAssertionFact] = []
    for assertion in local:
        compact = _compact(assertion.source_text)
        if assertion.parent_control != schedule.tail_control or compact not in allowed:
            raise RecognitionError(
                "family-unrecognized",
                f"local assertion is not a fixed-tail remainder fact: {assertion.source_text!r}",
            )
        result.append(
            LocalAssertionFact(
                Architecture.NEON,
                assertion.parent_control,
                assertion.expression,
                "fixed-tail-remainder",
                _assertion_digest(assertion.source_text),
            )
        )
    return tuple(sorted(result, key=lambda item: canonical_sha256(item.to_record())))


def _stable_source_range(value: dict[str, Any]) -> dict[str, Any]:
    result = dict(value)
    result.pop("path", None)
    return result


def _effect_record(extraction: KernelExtraction) -> dict[str, Any]:
    calls = []
    for call in extraction.calls:
        calls.append(
            {
                "node_id": call.node_id,
                "spelling": call.spelling,
                "callee_type": call.callee_type,
                "result_type": call.result_type,
                "arguments": [
                    {
                        "type": argument.type_spelling,
                        "dependencies": list(argument.dependencies),
                        "source_text": argument.source_text,
                        "constant": argument.constant_value,
                        "semantic_operations": list(argument.semantic_operations),
                        "source": _stable_source_range(dataclasses.asdict(argument.source)),
                    }
                    for argument in call.arguments
                ],
                "dependencies": list(call.dependencies),
                "assigned_to": call.assigned_to,
                "parent_control": call.parent_control,
                "control_path": list(call.control_path),
                "source": _stable_source_range(dataclasses.asdict(call.source)),
            }
        )
    definitions = []
    for definition in extraction.definitions:
        value = dataclasses.asdict(definition)
        value["source"] = _stable_source_range(value["source"])
        definitions.append(value)
    controls = []
    for control in extraction.controls:
        value = dataclasses.asdict(control)
        value["source"] = _stable_source_range(value["source"])
        controls.append(value)
    return {
        "dialect": extraction.dialect,
        "function_type": extraction.function_type,
        "parameters": [
            {"name": item.name, "type": item.type_spelling}
            for item in extraction.parameters
        ],
        "calls": calls,
        "definitions": definitions,
        "controls": controls,
        "assertions": [dataclasses.asdict(item) for item in extraction.assertions],
    }


def recognize_pair(
    neon: KernelExtraction,
    rvv: KernelExtraction,
    *,
    repository_root: str | Path,
) -> PairRecognition:
    """Recognize the first scalar-lane fixed-loop/RVV family without case ids."""

    neon_inputs, neon_output, neon_element, neon_width = _layout_streams(neon)
    rvv_inputs, rvv_output, rvv_element, rvv_width = _layout_streams(rvv)
    if (
        neon_inputs != rvv_inputs
        or neon_output != rvv_output
        or neon_element != rvv_element
        or neon_width != rvv_width
    ):
        raise RecognitionError("layout-unrecognized", "Neon/RVV scalar stream layouts differ")
    neon_entry, neon_local = translate_assertions(
        neon.assertions, parameters=neon.parameters
    )
    rvv_entry, rvv_local = translate_assertions(rvv.assertions, parameters=rvv.parameters)
    if rvv_local:
        raise RecognitionError("family-unrecognized", "RVV local assertions are unsupported")
    try:
        contracts = ContractBinding(neon_entry, rvv_entry)
    except ElementwiseSchemaError as error:
        raise RecognitionError("entry-contract-mismatch", str(error)) from error
    fixed = _recognize_fixed(neon)
    stripmine = _recognize_rvv(rvv)
    if _ELEMENT_CANONICAL.get(fixed.element_c_type, fixed.element_c_type) != (
        _ELEMENT_CANONICAL.get(neon_element, neon_element)
    ):
        raise RecognitionError(
            "family-unrecognized",
            f"loop element {fixed.element_c_type!r} disagrees with stream element {neon_element!r}",
        )
    local_facts = _derive_local_assertions(neon_local, fixed)
    root = Path(repository_root).resolve()
    layout_capability, schedule_capabilities = _capabilities(root)
    control_neon = canonical_sha256(_effect_record(neon)["controls"])
    control_rvv = canonical_sha256(_effect_record(rvv)["controls"])
    layout = LayoutInstance(
        layout_capability.ref,
        neon_element,
        tuple(sorted(neon_inputs)),
        (neon_output,),
    )
    schedules = (
        ScheduleInstance(
            Architecture.NEON,
            schedule_capabilities[(Architecture.NEON, fixed.kind)].ref,
            tuple(
                sorted(
                    {
                        "count_variable": fixed.count_variable,
                        "element_c_type": fixed.element_c_type,
                        "lanes": fixed.lanes,
                        "store_widths": ",".join(str(width) for width in fixed.store_widths) or "none",
                    }.items()
                )
            ),
            control_neon,
        ),
        ScheduleInstance(
            Architecture.RVV,
            schedule_capabilities[(Architecture.RVV, ScheduleKind.RVV_STRIP_MINE)].ref,
            tuple(
                sorted(
                    {
                        "count_variable": stripmine.count_variable,
                        "nested_controls": len(stripmine.nested_controls),
                    }.items()
                )
            ),
            control_rvv,
        ),
    )
    consumed = canonical_sha256(
        {"neon": _effect_record(neon), "rvv": _effect_record(rvv)}
    )
    return PairRecognition(
        contracts,
        layout_capability,
        (
            schedule_capabilities[(Architecture.NEON, fixed.kind)],
            schedule_capabilities[(Architecture.RVV, ScheduleKind.RVV_STRIP_MINE)],
        ),
        layout,
        schedules,
        local_facts,
        consumed,
        neon_inputs,
        neon_output,
        neon_element,
        neon_width,
        fixed,
        stripmine,
    )
