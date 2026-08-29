"""Content-addressed reusable capabilities for the elementwise compiler."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Mapping, Sequence

from .schema import (
    SCHEMA_VERSION,
    Architecture,
    CapabilityRef,
    ElementwiseSchemaError,
    canonical_sha256,
)


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ElementwiseSchemaError(f"{field} must be a trimmed non-empty string")
    return value


def _digest(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ElementwiseSchemaError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ElementwiseSchemaError(f"{field} must be a string-keyed JSON object")
    return value


def _sequence(value: object, field: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ElementwiseSchemaError(f"{field} must be a JSON array")
    return value


def _exact(data: Mapping[str, Any], expected: set[str], subject: str) -> None:
    if set(data) != expected:
        raise ElementwiseSchemaError(
            f"invalid {subject} fields: missing={sorted(expected - set(data))!r}, "
            f"extra={sorted(set(data) - expected)!r}"
        )


class IntrinsicRole(str, Enum):
    STRUCTURAL = "structural"
    SEMANTIC = "semantic"
    SCHEDULE = "schedule"


@dataclass(frozen=True, slots=True)
class IntrinsicCapability:
    """One program-independent exact typed intrinsic lowering capability."""

    architecture: Architecture
    spelling: str
    function_type: str
    argument_count: int
    role: IntrinsicRole
    descriptor_sha256: str
    implementation_sha256: str
    semantic_symbol: str | None
    review_evidence_sha256: str | None = None
    version: int = 1
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        _text(self.spelling, "intrinsic spelling")
        _text(self.function_type, "intrinsic function type")
        if type(self.argument_count) is not int or self.argument_count < 0:
            raise ElementwiseSchemaError("intrinsic argument count must be non-negative")
        _digest(self.descriptor_sha256, "intrinsic descriptor digest")
        _digest(self.implementation_sha256, "intrinsic implementation digest")
        if self.role is IntrinsicRole.SEMANTIC:
            _text(self.semantic_symbol, "intrinsic semantic symbol")
        elif self.semantic_symbol is not None:
            raise ElementwiseSchemaError("non-semantic capability cannot name a semantic symbol")
        if self.review_evidence_sha256 is not None:
            _digest(self.review_evidence_sha256, "intrinsic review evidence digest")
        if type(self.version) is not int or self.version <= 0:
            raise ElementwiseSchemaError("intrinsic capability version must be positive")
        if self.schema_version != SCHEMA_VERSION:
            raise ElementwiseSchemaError("unsupported intrinsic capability schema version")

    @property
    def capability_id(self) -> str:
        source_key = canonical_sha256(
            {
                "architecture": self.architecture.value,
                "spelling": self.spelling,
                "function_type": self.function_type,
                "argument_count": self.argument_count,
            }
        )[:16]
        return f"intrinsic:{self.architecture.value}:{self.spelling}:{source_key}"

    def unsigned_record(self) -> dict[str, Any]:
        return {
            "artifact_kind": "intrinsic-capability",
            "schema_version": self.schema_version,
            "capability_id": self.capability_id,
            "version": self.version,
            "architecture": self.architecture.value,
            "spelling": self.spelling,
            "function_type": self.function_type,
            "argument_count": self.argument_count,
            "role": self.role.value,
            "descriptor_sha256": self.descriptor_sha256,
            "implementation_sha256": self.implementation_sha256,
            "semantic_symbol": self.semantic_symbol,
            "review_evidence_sha256": self.review_evidence_sha256,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.unsigned_record())

    @property
    def ref(self) -> CapabilityRef:
        return CapabilityRef(self.capability_id, self.version, self.sha256)

    def to_record(self) -> dict[str, Any]:
        return {**self.unsigned_record(), "capability_sha256": self.sha256}

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "IntrinsicCapability":
        expected = {
            "artifact_kind", "schema_version", "capability_id", "version",
            "architecture", "spelling", "function_type", "argument_count", "role",
            "descriptor_sha256", "implementation_sha256", "semantic_symbol",
            "review_evidence_sha256", "capability_sha256",
        }
        _exact(data, expected, "intrinsic capability")
        if data["artifact_kind"] != "intrinsic-capability":
            raise ElementwiseSchemaError("invalid intrinsic capability artifact kind")
        try:
            architecture = Architecture(data["architecture"])
            role = IntrinsicRole(data["role"])
        except (TypeError, ValueError) as error:
            raise ElementwiseSchemaError("invalid intrinsic capability enum") from error
        argument_count = data["argument_count"]
        version = data["version"]
        schema_version = data["schema_version"]
        if type(argument_count) is not int or type(version) is not int or type(schema_version) is not int:
            raise ElementwiseSchemaError("intrinsic capability integer fields are malformed")
        semantic_symbol = data["semantic_symbol"]
        if semantic_symbol is not None and not isinstance(semantic_symbol, str):
            raise ElementwiseSchemaError("semantic symbol must be a string or null")
        review = data["review_evidence_sha256"]
        if review is not None:
            review = _digest(review, "intrinsic review evidence digest")
        result = cls(
            architecture=architecture,
            spelling=_text(data["spelling"], "intrinsic spelling"),
            function_type=_text(data["function_type"], "intrinsic function type"),
            argument_count=argument_count,
            role=role,
            descriptor_sha256=_digest(data["descriptor_sha256"], "descriptor digest"),
            implementation_sha256=_digest(data["implementation_sha256"], "implementation digest"),
            semantic_symbol=semantic_symbol,
            review_evidence_sha256=review,
            version=version,
            schema_version=schema_version,
        )
        if data["capability_id"] != result.capability_id:
            raise ElementwiseSchemaError("intrinsic capability id disagrees with source key")
        if _digest(data["capability_sha256"], "capability digest") != result.sha256:
            raise ElementwiseSchemaError("intrinsic capability digest disagrees with contents")
        return result


class LayoutKind(str, Enum):
    SCALAR_LANE = "scalar-lane"


@dataclass(frozen=True, slots=True)
class LayoutViewCapability:
    kind: LayoutKind
    recognizer_sha256: str
    theorem_symbol: str
    theorem_sha256: str
    version: int = 1

    def __post_init__(self) -> None:
        _digest(self.recognizer_sha256, "layout recognizer digest")
        _text(self.theorem_symbol, "layout theorem symbol")
        _digest(self.theorem_sha256, "layout theorem digest")
        if type(self.version) is not int or self.version <= 0:
            raise ElementwiseSchemaError("layout capability version must be positive")

    @property
    def capability_id(self) -> str:
        return f"layout:{self.kind.value}"

    def unsigned_record(self) -> dict[str, Any]:
        return {
            "artifact_kind": "layout-view-capability",
            "schema_version": SCHEMA_VERSION,
            "capability_id": self.capability_id,
            "version": self.version,
            "kind": self.kind.value,
            "logical_index_rule": "stream[i]",
            "recognizer_sha256": self.recognizer_sha256,
            "theorem_symbol": self.theorem_symbol,
            "theorem_sha256": self.theorem_sha256,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.unsigned_record())

    @property
    def ref(self) -> CapabilityRef:
        return CapabilityRef(self.capability_id, self.version, self.sha256)

    def to_record(self) -> dict[str, Any]:
        return {**self.unsigned_record(), "capability_sha256": self.sha256}

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "LayoutViewCapability":
        expected = {
            "artifact_kind", "schema_version", "capability_id", "version", "kind",
            "logical_index_rule", "recognizer_sha256", "theorem_symbol", "theorem_sha256",
            "capability_sha256",
        }
        _exact(data, expected, "layout-view capability")
        if data["artifact_kind"] != "layout-view-capability" or data["schema_version"] != SCHEMA_VERSION:
            raise ElementwiseSchemaError("invalid layout-view capability header")
        if data["logical_index_rule"] != "stream[i]":
            raise ElementwiseSchemaError("unsupported scalar-lane logical index rule")
        try:
            kind = LayoutKind(data["kind"])
        except (TypeError, ValueError) as error:
            raise ElementwiseSchemaError("invalid layout kind") from error
        version = data["version"]
        if type(version) is not int:
            raise ElementwiseSchemaError("layout version must be an integer")
        result = cls(
            kind,
            _digest(data["recognizer_sha256"], "layout recognizer digest"),
            _text(data["theorem_symbol"], "layout theorem symbol"),
            _digest(data["theorem_sha256"], "layout theorem digest"),
            version,
        )
        if data["capability_id"] != result.capability_id or data["capability_sha256"] != result.sha256:
            raise ElementwiseSchemaError("layout capability identity disagrees with contents")
        return result


class ScheduleKind(str, Enum):
    FIXED_NO_TAIL = "fixed-no-tail"
    FIXED_TAIL = "fixed-tail"
    MULTI_PHASE = "multi-phase"
    RVV_STRIP_MINE = "rvv-strip-mine"


@dataclass(frozen=True, slots=True)
class ScheduleFamilyCapability:
    architecture: Architecture
    kind: ScheduleKind
    recognizer_sha256: str
    theorem_symbols: tuple[str, ...]
    theorem_sha256: str
    version: int = 1

    def __post_init__(self) -> None:
        _digest(self.recognizer_sha256, "schedule recognizer digest")
        if not self.theorem_symbols or tuple(sorted(set(self.theorem_symbols))) != self.theorem_symbols:
            raise ElementwiseSchemaError("schedule theorem symbols must be sorted and unique")
        for symbol in self.theorem_symbols:
            _text(symbol, "schedule theorem symbol")
        _digest(self.theorem_sha256, "schedule theorem digest")
        if type(self.version) is not int or self.version <= 0:
            raise ElementwiseSchemaError("schedule capability version must be positive")

    @property
    def capability_id(self) -> str:
        return f"schedule:{self.architecture.value}:{self.kind.value}"

    def unsigned_record(self) -> dict[str, Any]:
        return {
            "artifact_kind": "schedule-family-capability",
            "schema_version": SCHEMA_VERSION,
            "capability_id": self.capability_id,
            "version": self.version,
            "architecture": self.architecture.value,
            "kind": self.kind.value,
            "recognizer_sha256": self.recognizer_sha256,
            "theorem_symbols": list(self.theorem_symbols),
            "theorem_sha256": self.theorem_sha256,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.unsigned_record())

    @property
    def ref(self) -> CapabilityRef:
        return CapabilityRef(self.capability_id, self.version, self.sha256)

    def to_record(self) -> dict[str, Any]:
        return {**self.unsigned_record(), "capability_sha256": self.sha256}

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "ScheduleFamilyCapability":
        expected = {
            "artifact_kind", "schema_version", "capability_id", "version", "architecture",
            "kind", "recognizer_sha256", "theorem_symbols", "theorem_sha256",
            "capability_sha256",
        }
        _exact(data, expected, "schedule-family capability")
        if data["artifact_kind"] != "schedule-family-capability" or data["schema_version"] != SCHEMA_VERSION:
            raise ElementwiseSchemaError("invalid schedule-family capability header")
        try:
            architecture = Architecture(data["architecture"])
            kind = ScheduleKind(data["kind"])
        except (TypeError, ValueError) as error:
            raise ElementwiseSchemaError("invalid schedule capability enum") from error
        version = data["version"]
        if type(version) is not int:
            raise ElementwiseSchemaError("schedule version must be an integer")
        result = cls(
            architecture,
            kind,
            _digest(data["recognizer_sha256"], "schedule recognizer digest"),
            tuple(_text(item, "schedule theorem symbol") for item in _sequence(data["theorem_symbols"], "schedule theorem symbols")),
            _digest(data["theorem_sha256"], "schedule theorem digest"),
            version,
        )
        if data["capability_id"] != result.capability_id or data["capability_sha256"] != result.sha256:
            raise ElementwiseSchemaError("schedule capability identity disagrees with contents")
        return result

