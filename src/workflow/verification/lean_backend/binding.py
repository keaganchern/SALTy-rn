"""Bind restricted Clang extraction facts to the reviewed intrinsic registry.

This module is deliberately a syntax/provenance stage.  It checks that every
extracted call has one exact registry entry, validates the first kernel's
immediates and selected dataflow invariants, and emits a canonical manifest.
It does not assign semantics to C control flow or prove that a registry entry
implements the corresponding C or ISA intrinsic.
"""

from __future__ import annotations

import dataclasses
import hashlib
import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .frontend import ArgumentFact, IntrinsicCall, KernelExtraction, SourceRange
from .registry import QS8_VADD_MINMAX_REGISTRY
from .schema import (
    Architecture,
    IntrinsicSpec,
    OperandTransform,
    Parameter,
    PointerType,
    ScalarType,
    ScheduleIntrinsic,
    SemanticIntrinsic,
    StructuralIntrinsic,
    StructuralOp,
    TypedOperand,
    ValueType,
    VectorType,
    VoidType,
    make_node,
    render_clang_function_type,
)


class BindingError(RuntimeError):
    """Base class for fail-closed registry binding failures."""


class ArtifactFreshnessError(BindingError):
    """A source or facade no longer matches its extraction-time digest."""


class RegistryInventoryError(BindingError):
    """Observed and reviewed exact-spelling inventories are not bidirectional."""


class CallBindingError(BindingError):
    """An extracted call cannot be bound to its exact registry declaration."""


class ControlShapeError(BindingError):
    """The selected kernel no longer has the reviewed control skeleton."""


class ActiveLengthBindingError(BindingError):
    """RVV calls or progress updates are not tied to the unique active length."""


class OperandProvenanceError(BindingError):
    """A Lean operand transform lacks its required source-level provenance."""


_MANIFEST_SCHEMA_VERSION = 2
_EXPECTED_REGISTRY_SIZE = 43
_REGISTRY_SOURCE = Path(__file__).with_name("registry.py")
_CANONICAL_FACADE = Path(__file__).with_name("facade") / "qs8_vadd_minmax.h"


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=True,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("ascii")


def _sha256_bytes(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _workspace_path(path: str | Path, workspace_root: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(workspace_root.resolve()).as_posix()
    except ValueError as error:
        raise BindingError(
            f"artifact path {resolved} is outside workspace {workspace_root.resolve()}"
        ) from error


def _type_record(value_type: ValueType) -> dict[str, Any]:
    if isinstance(value_type, ScalarType):
        return {
            "kind": "scalar",
            "c_spelling": value_type.c_spelling,
            "bit_width": value_type.bit_width,
            "signedness": value_type.signedness.value,
        }
    if isinstance(value_type, VectorType):
        return {
            "kind": "vector",
            "c_spelling": value_type.c_spelling,
            "element": _type_record(value_type.element),
            "fixed_lanes": value_type.fixed_lanes,
            "lmul": value_type.lmul,
        }
    if isinstance(value_type, PointerType):
        return {
            "kind": "pointer",
            "const": value_type.const,
            "pointee": _type_record(value_type.pointee),
        }
    if isinstance(value_type, VoidType):
        return {"kind": "void", "c_spelling": value_type.c_spelling}
    raise BindingError(f"unserializable registry type {type(value_type)!r}")


def _immediate_sort_key(value: int | str) -> tuple[str, str]:
    return type(value).__name__, repr(value)


def _registry_entry(spec: IntrinsicSpec) -> dict[str, Any]:
    record: dict[str, Any] = {
        "spelling": spec.spelling,
        "architecture": spec.architecture.value,
        "kind": spec.kind.value,
        "shape": spec.shape.value,
        "signature": {
            "parameters": [
                {"name": parameter.name, "type": _type_record(parameter.type)}
                for parameter in spec.signature.parameters
            ],
            "result": _type_record(spec.signature.result),
        },
        "immediate_constraints": [
            {
                "argument_index": constraint.argument_index,
                "allowed_values": sorted(
                    constraint.allowed_values, key=_immediate_sort_key
                ),
            }
            for constraint in sorted(
                spec.immediate_constraints, key=lambda constraint: constraint.argument_index
            )
        ],
    }
    if isinstance(spec, StructuralIntrinsic):
        record["structural_operation"] = spec.operation.value
    elif isinstance(spec, ScheduleIntrinsic):
        record["schedule_operation"] = spec.operation.value
    elif isinstance(spec, SemanticIntrinsic):
        record["lean_name"] = spec.lean_name
        record["lean_arguments"] = [
            {
                "source_index": argument.source_index,
                "transform": argument.transform.value,
            }
            for argument in spec.lean_arguments
        ]
    else:
        raise BindingError(f"unsupported registry entry {type(spec)!r}")
    return record


def canonical_registry(
    registry: Mapping[str, IntrinsicSpec] = QS8_VADD_MINMAX_REGISTRY,
) -> dict[str, Any]:
    """Return the exact 43-entry registry inventory and its content digest."""

    if len(registry) != _EXPECTED_REGISTRY_SIZE:
        raise RegistryInventoryError(
            f"qs8-vadd-minmax registry must contain exactly "
            f"{_EXPECTED_REGISTRY_SIZE} entries, got {len(registry)}"
        )
    entries = []
    for spelling, spec in registry.items():
        if spelling != spec.spelling:
            raise RegistryInventoryError(
                f"registry key {spelling!r} does not match entry {spec.spelling!r}"
            )
        entries.append(_registry_entry(spec))
    entries.sort(key=lambda entry: (entry["architecture"], entry["spelling"]))
    payload = {
        "name": "qs8-vadd-minmax-intrinsics",
        "entry_count": len(entries),
        "entries": entries,
    }
    return {**payload, "sha256": _sha256_bytes(payload)}


def _range_record(
    source_range: SourceRange,
    *,
    workspace_root: Path,
    expected_source: Path,
) -> dict[str, Any]:
    if Path(source_range.path).resolve() != expected_source.resolve():
        raise BindingError(
            f"source range belongs to {source_range.path}, not {expected_source}"
        )
    if source_range.begin_offset < 0 or source_range.end_offset < source_range.begin_offset:
        raise BindingError(f"invalid source range {source_range!r}")
    return {
        "path": _workspace_path(source_range.path, workspace_root),
        "begin_offset": source_range.begin_offset,
        "end_offset": source_range.end_offset,
        "begin_line": source_range.begin_line,
        "begin_column": source_range.begin_column,
        "end_line": source_range.end_line,
        "end_column": source_range.end_column,
    }


def _check_freshness(extraction: KernelExtraction) -> tuple[Path, Path]:
    source = Path(extraction.source_path).resolve()
    facade = Path(extraction.facade_path).resolve()
    for label, path, recorded in (
        ("source", source, extraction.source_sha256),
        ("facade", facade, extraction.facade_sha256),
    ):
        if not path.is_file():
            raise ArtifactFreshnessError(f"{label} artifact no longer exists: {path}")
        actual = _sha256_file(path)
        if actual != recorded:
            raise ArtifactFreshnessError(
                f"stale {label} extraction for {path}: recorded {recorded}, actual {actual}"
            )
    canonical_facade_sha256 = _sha256_file(_CANONICAL_FACADE)
    if extraction.facade_sha256 != canonical_facade_sha256:
        raise ArtifactFreshnessError(
            "the qs8-vadd-minmax binding requires the pinned parse facade"
        )
    return source, facade


def _architecture(extraction: KernelExtraction) -> Architecture:
    try:
        return Architecture(extraction.dialect)
    except ValueError as error:
        raise BindingError(f"unsupported extraction dialect {extraction.dialect!r}") from error


def _validate_preprocessing_binding(
    extraction: KernelExtraction, architecture: Architecture
) -> None:
    expected_target = {
        Architecture.NEON: "aarch64-none-elf",
        Architecture.RVV: "riscv64-none-elf",
    }[architecture]
    if extraction.target_triple != expected_target:
        raise BindingError(
            f"{architecture.value} extraction target must be {expected_target!r}, "
            f"got {extraction.target_triple!r}"
        )
    if re.fullmatch(r"[0-9a-f]{64}", extraction.preprocessed_sha256) is None:
        raise BindingError(
            f"invalid preprocessed translation-unit digest "
            f"{extraction.preprocessed_sha256!r}"
        )


def _spec_for_call(
    call: IntrinsicCall,
    architecture: Architecture,
    registry: Mapping[str, IntrinsicSpec],
) -> IntrinsicSpec:
    try:
        spec = registry[call.spelling]
    except KeyError as error:
        raise RegistryInventoryError(
            f"{call.node_id}: no exact registry entry for {call.spelling!r}"
        ) from error
    if spec.architecture is not architecture:
        raise RegistryInventoryError(
            f"{call.node_id}: {call.spelling!r} is {spec.architecture.value}, "
            f"not {architecture.value}"
        )
    return spec


def _normalized_c_type(spelling: str) -> str:
    return re.sub(r"\s+", "", spelling)


_SCALAR_SOURCE_SPELLINGS = {
    "int8_t": frozenset({"int8_t", "signedchar"}),
    "int16_t": frozenset({"int16_t", "short"}),
    "int32_t": frozenset({"int32_t", "int"}),
    "uint16_t": frozenset({"uint16_t", "unsignedshort"}),
    "uint32_t": frozenset({"uint32_t", "unsignedint"}),
    "int": frozenset({"int"}),
    "unsigned int": frozenset({"unsignedint"}),
    # The initial parse facade is pinned to the current LP64 Clang target.
    "size_t": frozenset({"size_t", "unsignedlong"}),
}


def _source_type_matches(source_spelling: str, registry_type: ValueType) -> bool:
    actual = _normalized_c_type(source_spelling)
    if isinstance(registry_type, ScalarType):
        allowed = _SCALAR_SOURCE_SPELLINGS.get(registry_type.c_spelling)
        return allowed is not None and actual in allowed
    if isinstance(registry_type, VectorType):
        return actual == _normalized_c_type(registry_type.c_spelling)
    if isinstance(registry_type, PointerType):
        return actual == _normalized_c_type(registry_type.c_spelling)
    if isinstance(registry_type, VoidType):
        return actual == "void"
    return False


def _unique_dependencies(arguments: Sequence[ArgumentFact]) -> tuple[str, ...]:
    return tuple(
        dict.fromkeys(
            dependency
            for argument in arguments
            for dependency in argument.dependencies
        )
    )


def _validate_extraction_consistency(extraction: KernelExtraction) -> None:
    calls_by_id = {call.node_id: call for call in extraction.calls}
    if len(calls_by_id) != len(extraction.calls):
        raise CallBindingError("call ids are not unique")
    definitions_by_value = {
        definition.value: definition for definition in extraction.definitions
    }
    if len(definitions_by_value) != len(extraction.definitions):
        raise CallBindingError("definition values are not unique")
    value_calls = {
        definition.value_call: definition
        for definition in extraction.definitions
        if definition.value_call is not None
    }
    if len(value_calls) != sum(
        definition.value_call is not None for definition in extraction.definitions
    ):
        raise CallBindingError("multiple definitions claim one call result")
    unknown_value_calls = set(value_calls) - set(calls_by_id)
    if unknown_value_calls:
        raise CallBindingError(
            f"definitions reference unknown calls {sorted(unknown_value_calls)!r}"
        )
    for call in extraction.calls:
        expected_dependencies = _unique_dependencies(call.arguments)
        if call.dependencies != expected_dependencies:
            raise CallBindingError(
                f"{call.node_id}: call dependencies {call.dependencies!r} do not "
                f"match argument dependencies {expected_dependencies!r}"
            )
        definition = value_calls.get(call.node_id)
        if call.assigned_to is None:
            if definition is not None:
                raise CallBindingError(
                    f"{call.node_id}: definition records an unassigned call result"
                )
        elif (
            definition is None
            or definition.value != call.assigned_to
            or definition.dependencies != (f"call:{call.node_id}",)
        ):
            raise CallBindingError(
                f"{call.node_id}: assigned result {call.assigned_to!r} is not "
                "bidirectionally bound to its definition"
            )


def _bind_calls(
    extraction: KernelExtraction,
    architecture: Architecture,
    registry: Mapping[str, IntrinsicSpec],
) -> tuple[dict[str, IntrinsicSpec], dict[str, Any]]:
    call_specs: dict[str, IntrinsicSpec] = {}
    call_records: dict[str, Any] = {}
    seen_ids: set[str] = set()
    for call in extraction.calls:
        if call.node_id in seen_ids:
            raise CallBindingError(f"duplicate call id {call.node_id!r}")
        seen_ids.add(call.node_id)
        spec = _spec_for_call(call, architecture, registry)
        expected_callee_type = render_clang_function_type(spec.signature)
        if call.callee_type != expected_callee_type:
            raise CallBindingError(
                f"{call.node_id}: {call.spelling} expected callee type "
                f"{expected_callee_type!r}, got {call.callee_type!r}"
            )
        if len(call.arguments) != len(spec.signature.parameters):
            raise CallBindingError(
                f"{call.node_id}: {call.spelling} expected "
                f"{len(spec.signature.parameters)} arguments, got {len(call.arguments)}"
            )
        if not _source_type_matches(call.result_type, spec.signature.result):
            raise CallBindingError(
                f"{call.node_id}: {call.spelling} registry result "
                f"{spec.signature.result!r} does not match extracted "
                f"type {call.result_type!r}"
            )
        for index, (argument, parameter) in enumerate(
            zip(call.arguments, spec.signature.parameters)
        ):
            if not _source_type_matches(argument.type_spelling, parameter.type):
                raise CallBindingError(
                    f"{call.node_id}: argument {index} extracted type "
                    f"{argument.type_spelling!r} does not match registry type "
                    f"{parameter.type!r}"
                )
        operands = tuple(
            TypedOperand(
                argument.source_text,
                parameter.type,
                argument.constant_value,
            )
            for argument, parameter in zip(call.arguments, spec.signature.parameters)
        )
        try:
            make_node(spec, operands)
        except ValueError as error:
            raise CallBindingError(f"{call.node_id}: {error}") from error
        call_specs[call.node_id] = spec
        call_records[call.node_id] = {
            "registry_entry_sha256": _sha256_bytes(_registry_entry(spec)),
            "registry_kind": spec.kind.value,
            "registry_shape": spec.shape.value,
        }
    return call_specs, call_records


def _check_bidirectional_inventory(
    extraction: KernelExtraction,
    architecture: Architecture,
    registry: Mapping[str, IntrinsicSpec],
) -> dict[str, Any]:
    registered = {
        spec.spelling for spec in registry.values() if spec.architecture is architecture
    }
    observed = {call.spelling for call in extraction.calls}
    missing = sorted(registered - observed)
    unregistered = sorted(observed - registered)
    if missing or unregistered:
        raise RegistryInventoryError(
            f"{architecture.value} registry/call inventory mismatch: "
            f"missing={missing!r}, unregistered={unregistered!r}"
        )
    counts = {
        spelling: sum(call.spelling == spelling for call in extraction.calls)
        for spelling in sorted(observed)
    }
    return {
        "bidirectional_complete": True,
        "registered_unique_count": len(registered),
        "observed_unique_count": len(observed),
        "observed_call_count": len(extraction.calls),
        "observed_counts": counts,
    }


def _compact_expression(text: str) -> str:
    return re.sub(r"\s+", "", text)


_NEON_CONTROL_SHAPE = (
    ("control_0000", "ForStmt", None, "batch>=16*sizeof(int8_t)", "batch-=16*sizeof(int8_t)"),
    ("control_0001", "IfStmt", None, "batch!=0", ""),
    ("control_0002", "DoStmt", "control_0001", "batch!=0", ""),
    ("control_0003", "IfStmt", "control_0002", "batch>=(8*sizeof(int8_t))", ""),
    ("control_0004", "IfStmt", "control_0003", "batch&(4*sizeof(int8_t))", ""),
    ("control_0005", "IfStmt", "control_0003", "batch&(2*sizeof(int8_t))", ""),
    ("control_0006", "IfStmt", "control_0003", "batch&(1*sizeof(int8_t))", ""),
)

_RVV_CONTROL_SHAPE = (
    ("control_0000", "WhileStmt", None, "batch>0", ""),
)

_NEON_CALL_CONTROL_RANGES = (
    (0, 8, None),
    (8, 58, "control_0000"),
    (58, 85, "control_0002"),
    (85, 86, "control_0003"),
    (86, 89, "control_0004"),
    (89, 92, "control_0005"),
    (92, 93, "control_0006"),
)


def _validate_control_shape(extraction: KernelExtraction, architecture: Architecture) -> None:
    expected = _NEON_CONTROL_SHAPE if architecture is Architecture.NEON else _RVV_CONTROL_SHAPE
    actual = tuple(
        (
            control.node_id,
            control.kind,
            control.parent_control,
            _compact_expression(control.condition_text),
            _compact_expression(control.update_text),
        )
        for control in extraction.controls
    )
    if actual != expected:
        raise ControlShapeError(
            f"{architecture.value} control shape changed: expected {expected!r}, got {actual!r}"
        )

    if architecture is Architecture.NEON:
        if len(extraction.calls) != 93:
            raise ControlShapeError(
                f"Neon reviewed call placement expects 93 calls, got {len(extraction.calls)}"
            )
        for begin, end, parent in _NEON_CALL_CONTROL_RANGES:
            misplaced = [
                call.node_id
                for call in extraction.calls[begin:end]
                if call.parent_control != parent
            ]
            if misplaced:
                raise ControlShapeError(
                    f"Neon calls {misplaced!r} are outside reviewed control {parent!r}"
                )
    else:
        if len(extraction.calls) != 16:
            raise ControlShapeError(
                f"RVV reviewed loop expects 16 calls, got {len(extraction.calls)}"
            )
        misplaced = [
            call.node_id
            for call in extraction.calls
            if call.parent_control != "control_0000"
        ]
        if misplaced:
            raise ControlShapeError(
                f"RVV calls {misplaced!r} are outside the reviewed while loop"
            )


def _producer_maps(
    extraction: KernelExtraction,
) -> tuple[dict[str, IntrinsicCall], dict[str, IntrinsicCall]]:
    calls_by_id = {call.node_id: call for call in extraction.calls}
    if len(calls_by_id) != len(extraction.calls):
        raise CallBindingError("call ids are not unique")
    assigned: dict[str, IntrinsicCall] = {}
    for call in extraction.calls:
        if call.assigned_to is None:
            continue
        if call.assigned_to in assigned:
            raise CallBindingError(f"multiple calls produce {call.assigned_to!r}")
        assigned[call.assigned_to] = call
    return calls_by_id, assigned


def _producer_for_dependency(
    dependency: str,
    calls_by_id: Mapping[str, IntrinsicCall],
    assigned: Mapping[str, IntrinsicCall],
) -> IntrinsicCall | None:
    if dependency.startswith("call:"):
        return calls_by_id.get(dependency.removeprefix("call:"))
    return assigned.get(dependency)


def _broadcast_origin(
    argument: ArgumentFact,
    *,
    calls_by_id: Mapping[str, IntrinsicCall],
    assigned: Mapping[str, IntrinsicCall],
    call_specs: Mapping[str, IntrinsicSpec],
) -> tuple[IntrinsicCall, tuple[str, ...]]:
    if len(argument.dependencies) != 1:
        raise OperandProvenanceError(
            f"expected one producer for unbroadcast, got {argument.dependencies!r}"
        )
    producer = _producer_for_dependency(argument.dependencies[0], calls_by_id, assigned)
    if producer is None:
        raise OperandProvenanceError(
            f"unbroadcast operand has no intrinsic producer: {argument.dependencies[0]!r}"
        )
    path = [producer.node_id]
    spec = call_specs[producer.node_id]
    if isinstance(spec, StructuralIntrinsic) and spec.operation is StructuralOp.BROADCAST:
        return producer, tuple(path)
    if isinstance(spec, StructuralIntrinsic) and spec.operation is StructuralOp.TAKE_LOW:
        if len(producer.arguments) != 1 or len(producer.arguments[0].dependencies) != 1:
            raise OperandProvenanceError(
                f"{producer.node_id}: get-low must have one exact producer"
            )
        inner = _producer_for_dependency(
            producer.arguments[0].dependencies[0], calls_by_id, assigned
        )
        if inner is None:
            raise OperandProvenanceError(
                f"{producer.node_id}: get-low input has no intrinsic producer"
            )
        inner_spec = call_specs[inner.node_id]
        if not (
            isinstance(inner_spec, StructuralIntrinsic)
            and inner_spec.operation is StructuralOp.BROADCAST
        ):
            raise OperandProvenanceError(
                f"{producer.node_id}: get-low input is not a reviewed broadcast"
            )
        path.append(inner.node_id)
        return inner, tuple(path)
    raise OperandProvenanceError(
        f"{producer.node_id}: {producer.spelling} is not broadcast/get-low provenance"
    )


def _is_unary_negated(text: str) -> bool:
    compact = _compact_expression(text)
    while compact.startswith("(") and compact.endswith(")"):
        compact = compact[1:-1]
    return compact.startswith("-") and len(compact) > 1 and not compact.startswith("--")


def _validate_neon_transforms(
    extraction: KernelExtraction,
    call_specs: Mapping[str, IntrinsicSpec],
) -> dict[tuple[str, int], dict[str, Any]]:
    calls_by_id, assigned = _producer_maps(extraction)
    provenance: dict[tuple[str, int], dict[str, Any]] = {}
    for call in extraction.calls:
        spec = call_specs[call.node_id]
        if not isinstance(spec, SemanticIntrinsic):
            continue
        for lean_argument in spec.lean_arguments:
            transform = lean_argument.transform
            if transform not in {
                OperandTransform.UNBROADCAST,
                OperandTransform.NEGATED_UNBROADCAST_TO_NAT,
            }:
                continue
            source_index = lean_argument.source_index
            origin, path = _broadcast_origin(
                call.arguments[source_index],
                calls_by_id=calls_by_id,
                assigned=assigned,
                call_specs=call_specs,
            )
            negated = transform is OperandTransform.NEGATED_UNBROADCAST_TO_NAT
            if negated:
                if len(origin.arguments) != 1 or not _is_unary_negated(
                    origin.arguments[0].source_text
                ):
                    raise OperandProvenanceError(
                        f"{call.node_id} argument {source_index}: negated-unbroadcast "
                        f"origin {origin.node_id} is not syntactically unary-negated"
                    )
            provenance[(call.node_id, source_index)] = {
                "transform": transform.value,
                "producer_path": list(path),
                "broadcast_call": origin.node_id,
                "broadcast_spelling": origin.spelling,
                "unary_negated_input": negated,
            }
    return provenance


def _validate_argument_operations(
    extraction: KernelExtraction,
    call_specs: Mapping[str, IntrinsicSpec],
    transform_provenance: Mapping[tuple[str, int], dict[str, Any]],
) -> None:
    """Reject source operations that the registry lowering would otherwise erase."""

    allowed_negated_broadcasts = {
        str(record["broadcast_call"])
        for record in transform_provenance.values()
        if record.get("transform")
        == OperandTransform.NEGATED_UNBROADCAST_TO_NAT.value
    }
    reviewed_lane_store_pointer_casts = {
        "vst1_lane_u32": (
            "(void*)output",
            ("explicit-cast:BitCast:void *", "implicit-cast:BitCast:uint32_t *"),
        ),
        "vst1_lane_u16": (
            "(void*)output",
            ("explicit-cast:BitCast:void *", "implicit-cast:BitCast:uint16_t *"),
        ),
    }
    for call in extraction.calls:
        spec = call_specs[call.node_id]
        constrained = {
            constraint.argument_index for constraint in spec.immediate_constraints
        }
        for index, argument in enumerate(call.arguments):
            operations = argument.semantic_operations
            if not operations:
                continue
            if index in constrained and argument.constant_value is not None:
                reviewed_conversion = (
                    f"implicit-cast:IntegralCast:{argument.type_spelling}",
                )
                if operations == reviewed_conversion:
                    continue
            if call.node_id in allowed_negated_broadcasts:
                if operations == ("unary:-",):
                    continue
            reviewed_pointer_cast = reviewed_lane_store_pointer_casts.get(call.spelling)
            if (
                index == 0
                and reviewed_pointer_cast is not None
                and _compact_expression(argument.source_text) == reviewed_pointer_cast[0]
                and operations == reviewed_pointer_cast[1]
                and len(argument.dependencies) == 1
                and argument.dependencies[0].startswith("output@")
            ):
                continue
            raise OperandProvenanceError(
                f"{call.node_id} argument {index}: source operations {operations!r} "
                "have no reviewed Lean lowering"
            )


def _validate_rvv_active_length(
    extraction: KernelExtraction,
    call_specs: Mapping[str, IntrinsicSpec],
) -> dict[str, Any]:
    schedule_calls = [
        call
        for call in extraction.calls
        if isinstance(call_specs[call.node_id], ScheduleIntrinsic)
    ]
    if len(schedule_calls) != 1:
        raise ActiveLengthBindingError(
            f"expected one RVV vsetvl result, got {len(schedule_calls)}"
        )
    setvl = schedule_calls[0]
    if setvl.assigned_to is None:
        raise ActiveLengthBindingError("the unique vsetvl result is not assigned")
    vl = setvl.assigned_to
    if len(setvl.arguments) != 1 or setvl.arguments[0].dependencies != ("batch@0",):
        raise ActiveLengthBindingError(
            f"{setvl.node_id}: vsetvl must consume the reviewed loop batch@0"
        )
    for call in extraction.calls:
        if call is setvl:
            continue
        spec = call_specs[call.node_id]
        if not spec.signature.parameters or spec.signature.parameters[-1].name != "vl":
            raise ActiveLengthBindingError(
                f"{call.node_id}: non-vsetvl RVV entry has no final vl parameter"
            )
        dependencies = call.arguments[-1].dependencies
        if dependencies != (vl,):
            raise ActiveLengthBindingError(
                f"{call.node_id}: final vl must depend exactly on {vl!r}, "
                f"got {dependencies!r}"
            )

    updates: dict[str, str] = {}
    for variable, expected_kind in (
        ("input_a", "compound-+="),
        ("input_b", "compound-+="),
        ("output", "compound-+="),
        ("batch", "compound--="),
    ):
        candidates = [
            definition
            for definition in extraction.definitions
            if definition.variable == variable
            and definition.definition_kind.startswith("compound-")
        ]
        if len(candidates) != 1:
            raise ActiveLengthBindingError(
                f"expected one RVV progress update for {variable}, got {len(candidates)}"
            )
        update = candidates[0]
        if update.definition_kind != expected_kind:
            raise ActiveLengthBindingError(
                f"{update.node_id}: {variable} uses {update.definition_kind}, "
                f"expected {expected_kind}"
            )
        if (
            len(update.dependencies) != 2
            or update.dependencies[1] != vl
            or not update.dependencies[0].startswith(f"{variable}@")
        ):
            raise ActiveLengthBindingError(
                f"{update.node_id}: {variable} update must use its prior value and {vl}"
            )
        if update.parent_control != "control_0000":
            raise ActiveLengthBindingError(
                f"{update.node_id}: {variable} update is outside the RVV while loop"
            )
        expected_expression = f"{variable}{'+=' if variable != 'batch' else '-='}vl"
        if _compact_expression(update.expression_text) != expected_expression:
            raise ActiveLengthBindingError(
                f"{update.node_id}: expected exact progress expression "
                f"{expected_expression!r}, got {update.expression_text!r}"
            )
        updates[variable] = update.node_id
    return {
        "unique_vsetvl_call": setvl.node_id,
        "active_length_value": vl,
        "all_vector_calls_use_active_length": True,
        "progress_updates": updates,
    }


def _argument_record(
    argument: ArgumentFact,
    parameter: Parameter,
    *,
    workspace_root: Path,
    source: Path,
    provenance: dict[str, Any] | None,
) -> dict[str, Any]:
    return {
        "source_type": argument.type_spelling,
        "registry_parameter": parameter.name,
        "registry_type": _type_record(parameter.type),
        "dependencies": list(argument.dependencies),
        "constant_value": argument.constant_value,
        "source_text": argument.source_text,
        "source": _range_record(
            argument.source, workspace_root=workspace_root, expected_source=source
        ),
        "transform_provenance": provenance,
    }


def bind_kernel(
    extraction: KernelExtraction,
    *,
    workspace_root: str | Path,
    registry: Mapping[str, IntrinsicSpec] = QS8_VADD_MINMAX_REGISTRY,
) -> dict[str, Any]:
    """Validate and serialize one extraction as registry-bound syntax facts."""

    root = Path(workspace_root).resolve()
    source, facade = _check_freshness(extraction)
    architecture = _architecture(extraction)
    _validate_preprocessing_binding(extraction, architecture)
    canonical_registry(registry)
    _validate_extraction_consistency(extraction)
    call_specs, binding_records = _bind_calls(extraction, architecture, registry)
    inventory = _check_bidirectional_inventory(extraction, architecture, registry)
    _validate_control_shape(extraction, architecture)
    transform_provenance: dict[tuple[str, int], dict[str, Any]] = {}
    schedule_binding: dict[str, Any]
    if architecture is Architecture.NEON:
        transform_provenance = _validate_neon_transforms(extraction, call_specs)
        schedule_binding = {
            "reviewed_fixed_width_and_tail_control_shape": True,
            "cfg_semantics_established": False,
        }
    else:
        schedule_binding = _validate_rvv_active_length(extraction, call_specs)
        schedule_binding["cfg_semantics_established"] = False
    _validate_argument_operations(extraction, call_specs, transform_provenance)

    calls = []
    for call in extraction.calls:
        spec = call_specs[call.node_id]
        calls.append(
            {
                "node_id": call.node_id,
                "spelling": call.spelling,
                "callee_type": call.callee_type,
                "result_type": call.result_type,
                "assigned_to": call.assigned_to,
                "parent_control": call.parent_control,
                "dependencies": list(call.dependencies),
                "binding": binding_records[call.node_id],
                "arguments": [
                    _argument_record(
                        argument,
                        parameter,
                        workspace_root=root,
                        source=source,
                        provenance=transform_provenance.get((call.node_id, index)),
                    )
                    for index, (argument, parameter) in enumerate(
                        zip(call.arguments, spec.signature.parameters)
                    )
                ],
                "source": _range_record(
                    call.source, workspace_root=root, expected_source=source
                ),
            }
        )

    return {
        "architecture": architecture.value,
        "function": {
            "name": extraction.function_name,
            "type": extraction.function_type,
        },
        "source": {
            "path": _workspace_path(source, root),
            "sha256": extraction.source_sha256,
            "preprocessed_sha256": extraction.preprocessed_sha256,
        },
        "facade": {
            "path": _workspace_path(facade, root),
            "sha256": extraction.facade_sha256,
        },
        "frontend": {
            "schema_version": extraction.schema_version,
            "producer": "clang-ast-dump-json",
            "clang_version": extraction.clang_version,
            "target_triple": extraction.target_triple,
            "reachable_ast_nodes": extraction.reachable_ast_nodes,
        },
        "inventory": inventory,
        "schedule_binding": schedule_binding,
        "parameters": [
            {
                "name": parameter.name,
                "type": parameter.type_spelling,
                "source": _range_record(
                    parameter.source, workspace_root=root, expected_source=source
                ),
            }
            for parameter in extraction.parameters
        ],
        "calls": calls,
        "definitions": [
            {
                **{
                    field.name: getattr(definition, field.name)
                    for field in dataclasses.fields(definition)
                    if field.name != "source"
                },
                "dependencies": list(definition.dependencies),
                "source": _range_record(
                    definition.source, workspace_root=root, expected_source=source
                ),
            }
            for definition in extraction.definitions
        ],
        "controls": [
            {
                **{
                    field.name: getattr(control, field.name)
                    for field in dataclasses.fields(control)
                    if field.name != "source"
                },
                "condition_dependencies": list(control.condition_dependencies),
                "source": _range_record(
                    control.source, workspace_root=root, expected_source=source
                ),
            }
            for control in extraction.controls
        ],
    }


def build_manifest(
    neon: KernelExtraction,
    rvv: KernelExtraction,
    *,
    workspace_root: str | Path,
    registry: Mapping[str, IntrinsicSpec] = QS8_VADD_MINMAX_REGISTRY,
) -> dict[str, Any]:
    """Build the deterministic two-sided registry-bound syntax manifest."""

    registry_record = canonical_registry(registry)
    registry_record["source"] = {
        "path": _workspace_path(_REGISTRY_SOURCE, Path(workspace_root).resolve()),
        "sha256": _sha256_file(_REGISTRY_SOURCE),
    }
    neon_record = bind_kernel(neon, workspace_root=workspace_root, registry=registry)
    rvv_record = bind_kernel(rvv, workspace_root=workspace_root, registry=registry)
    if neon_record["architecture"] != Architecture.NEON.value:
        raise BindingError("first extraction must be Neon")
    if rvv_record["architecture"] != Architecture.RVV.value:
        raise BindingError("second extraction must be RVV")
    if neon_record["facade"] != rvv_record["facade"]:
        raise BindingError("Neon and RVV extractions must use the same facade artifact")

    payload = {
        "schema_version": _MANIFEST_SCHEMA_VERSION,
        "artifact_kind": "saltyrn.registry_bound_intrinsic_syntax",
        "stage": {
            "name": "registry-bound-syntax",
            "establishes": [
                "fresh source and parse-facade hashes",
                "exact typed intrinsic-registry binding",
                "immediate-constraint checks",
                "reviewed syntactic control and operand-provenance checks",
            ],
            "does_not_establish": [
                "C abstract-machine or CFG semantics",
                "intrinsic value or state semantics",
                "Arm or RISC-V ISA correspondence",
                "Neon/RVV kernel equivalence",
            ],
        },
        "registry": registry_record,
        "kernels": {
            "neon": neon_record,
            "rvv": rvv_record,
        },
    }
    return {**payload, "manifest_sha256": _sha256_bytes(payload)}


def canonical_json(manifest: Mapping[str, Any], *, pretty: bool = True) -> str:
    """Serialize a manifest deterministically, with one trailing newline."""

    if pretty:
        return json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    return _canonical_bytes(manifest).decode("ascii") + "\n"
