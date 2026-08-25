"""Stable serialization for complete configured intrinsic descriptors."""

from __future__ import annotations

import hashlib
import json
from typing import Any

from .schema import (
    IntrinsicSpec,
    PointerType,
    ScalarType,
    ScheduleIntrinsic,
    SemanticIntrinsic,
    StructuralIntrinsic,
    VectorType,
    VoidType,
)


_SPEC_TYPES = (StructuralIntrinsic, SemanticIntrinsic, ScheduleIntrinsic)


class DescriptorSerializationError(ValueError):
    """A value is not part of the configured intrinsic descriptor schema."""


def canonical_type_record(value_type: object) -> dict[str, Any]:
    """Serialize one registry value type without relying on C pretty-printing."""

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
            "element": canonical_type_record(value_type.element),
            "fixed_lanes": value_type.fixed_lanes,
            "lmul": value_type.lmul,
        }
    if isinstance(value_type, PointerType):
        return {
            "kind": "pointer",
            "pointee": canonical_type_record(value_type.pointee),
            "const": value_type.const,
        }
    if isinstance(value_type, VoidType):
        return {"kind": "void", "c_spelling": value_type.c_spelling}
    raise DescriptorSerializationError(
        f"unsupported intrinsic value type: {type(value_type)!r}"
    )


def canonical_spec_record(spec: IntrinsicSpec) -> dict[str, Any]:
    """Serialize every semantic field of one configured intrinsic descriptor."""

    if not isinstance(spec, _SPEC_TYPES):
        raise DescriptorSerializationError(
            f"unsupported intrinsic descriptor: {type(spec)!r}"
        )
    record: dict[str, Any] = {
        "spelling": spec.spelling,
        "architecture": spec.architecture.value,
        "kind": spec.kind.value,
        "shape": spec.shape.value,
        "signature": {
            "parameters": [
                {
                    "name": parameter.name,
                    "type": canonical_type_record(parameter.type),
                }
                for parameter in spec.signature.parameters
            ],
            "result": canonical_type_record(spec.signature.result),
        },
        "immediate_constraints": [
            {
                "argument_index": constraint.argument_index,
                "allowed_values": sorted(
                    constraint.allowed_values,
                    key=lambda value: (type(value).__name__, repr(value)),
                ),
                "erased_from_semantics": constraint.erased_from_semantics,
            }
            for constraint in sorted(
                spec.immediate_constraints,
                key=lambda constraint: constraint.argument_index,
            )
        ],
    }
    if isinstance(spec, SemanticIntrinsic):
        record["lean_name"] = spec.lean_name
        record["lean_arguments"] = [
            {
                "source_index": argument.source_index,
                "transform": argument.transform.value,
            }
            for argument in spec.lean_arguments
        ]
    elif isinstance(spec, StructuralIntrinsic):
        record["structural_operation"] = spec.operation.value
    elif isinstance(spec, ScheduleIntrinsic):
        record["schedule_operation"] = spec.operation.value
    else:  # pragma: no cover - closed IntrinsicSpec union
        raise DescriptorSerializationError(
            f"unsupported intrinsic descriptor: {type(spec)!r}"
        )
    return record


def canonical_spec_json(spec: IntrinsicSpec) -> str:
    """Return a deterministic ASCII JSON encoding of a complete descriptor."""

    return json.dumps(
        canonical_spec_record(spec),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
    )


def canonical_spec_digest(spec: IntrinsicSpec) -> str:
    """Hash a complete descriptor without provenance or review status."""

    return hashlib.sha256(canonical_spec_json(spec).encode("ascii")).hexdigest()
