"""Canonical schemas for the reusable elementwise compiler.

The records in this module are deliberately independent of kernel names.  They
describe exact source artifacts, reusable capabilities, generated parents, and
terminal checker results.  Every persisted record is strict and content-addressed.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from enum import Enum
from pathlib import PurePosixPath
from typing import Any, Mapping, Sequence


SCHEMA_VERSION = 1
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_.']*$")


class ElementwiseSchemaError(ValueError):
    """A compiler artifact is malformed or internally inconsistent."""


def canonical_json(value: object, *, pretty: bool = False) -> str:
    """Serialize a JSON value deterministically using ASCII."""

    return json.dumps(
        value,
        ensure_ascii=True,
        indent=2 if pretty else None,
        separators=None if pretty else (",", ":"),
        sort_keys=True,
    ) + ("\n" if pretty else "")


def canonical_sha256(value: object) -> str:
    """Hash the compact canonical JSON representation of ``value``."""

    return hashlib.sha256(canonical_json(value).encode("ascii")).hexdigest()


def _exact_keys(data: Mapping[str, Any], expected: set[str], subject: str) -> None:
    actual = set(data)
    if actual != expected:
        raise ElementwiseSchemaError(
            f"invalid {subject} fields: missing={sorted(expected - actual)!r}, "
            f"extra={sorted(actual - expected)!r}"
        )


def _text(value: object, field: str) -> str:
    if not isinstance(value, str) or not value or value.strip() != value:
        raise ElementwiseSchemaError(f"{field} must be a trimmed non-empty string")
    return value


def _digest(value: object, field: str) -> str:
    if not isinstance(value, str) or _SHA256_RE.fullmatch(value) is None:
        raise ElementwiseSchemaError(f"{field} must be a lowercase SHA-256 digest")
    return value


def _optional_digest(value: object, field: str) -> str | None:
    return None if value is None else _digest(value, field)


def _relative_path(value: object, field: str) -> str:
    path = PurePosixPath(_text(value, field))
    if path.is_absolute() or ".." in path.parts:
        raise ElementwiseSchemaError(f"{field} must be a repository-relative path")
    return path.as_posix()


def _sequence(value: object, field: str) -> Sequence[object]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes)):
        raise ElementwiseSchemaError(f"{field} must be a JSON array")
    return value


def _mapping(value: object, field: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ElementwiseSchemaError(f"{field} must be a JSON object")
    if any(not isinstance(key, str) for key in value):
        raise ElementwiseSchemaError(f"{field} keys must be strings")
    return value


def _enum(enum_type: type[Enum], value: object, field: str) -> Any:
    try:
        return enum_type(value)
    except (TypeError, ValueError) as error:
        raise ElementwiseSchemaError(f"invalid {field}: {value!r}") from error


class Architecture(str, Enum):
    NEON = "neon"
    RVV = "rvv"


class ContractTypeKind(str, Enum):
    BOOL = "bool"
    INTEGER = "integer"
    POINTER = "pointer"


@dataclass(frozen=True, slots=True)
class ContractType:
    kind: ContractTypeKind
    c_spelling: str
    bit_width: int | None = None
    signed: bool | None = None

    def __post_init__(self) -> None:
        _text(self.c_spelling, "contract type C spelling")
        if self.kind is ContractTypeKind.BOOL:
            if self.bit_width is not None or self.signed is not None:
                raise ElementwiseSchemaError("boolean contract type has no width/sign")
        elif self.kind is ContractTypeKind.INTEGER:
            if self.bit_width is None or self.bit_width <= 0 or self.signed is None:
                raise ElementwiseSchemaError("integer contract type needs width and sign")
        elif self.kind is ContractTypeKind.POINTER:
            if self.bit_width is None or self.bit_width <= 0 or self.signed is not None:
                raise ElementwiseSchemaError("pointer contract type needs width and no sign")

    def to_record(self) -> dict[str, Any]:
        return {
            "kind": self.kind.value,
            "c_spelling": self.c_spelling,
            "bit_width": self.bit_width,
            "signed": self.signed,
        }

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "ContractType":
        _exact_keys(data, {"kind", "c_spelling", "bit_width", "signed"}, "contract type")
        width = data["bit_width"]
        if width is not None and (type(width) is not int or width <= 0):
            raise ElementwiseSchemaError("contract type bit_width must be positive or null")
        signed = data["signed"]
        if signed is not None and type(signed) is not bool:
            raise ElementwiseSchemaError("contract type signed must be boolean or null")
        return cls(
            kind=_enum(ContractTypeKind, data["kind"], "contract type kind"),
            c_spelling=_text(data["c_spelling"], "contract type C spelling"),
            bit_width=width,
            signed=signed,
        )


BOOL = ContractType(ContractTypeKind.BOOL, "_Bool")
SIZE_T = ContractType(ContractTypeKind.INTEGER, "size_t", 64, False)


class ContractOp(str, Enum):
    VARIABLE = "variable"
    INTEGER = "integer"
    NULL = "null"
    SIZEOF = "sizeof"
    NOT = "not"
    AND = "and"
    OR = "or"
    EQ = "eq"
    NE = "ne"
    LT = "lt"
    LE = "le"
    GT = "gt"
    GE = "ge"
    ADD = "add"
    SUB = "sub"
    MUL = "mul"
    MOD = "mod"


_LEAF_OPS = {ContractOp.VARIABLE, ContractOp.INTEGER, ContractOp.NULL, ContractOp.SIZEOF}
_UNARY_OPS = {ContractOp.NOT}
_BOOL_NARY_OPS = {ContractOp.AND, ContractOp.OR}
_COMPARE_OPS = {ContractOp.EQ, ContractOp.NE, ContractOp.LT, ContractOp.LE, ContractOp.GT, ContractOp.GE}
_ARITHMETIC_OPS = {ContractOp.ADD, ContractOp.SUB, ContractOp.MUL, ContractOp.MOD}
_COMMUTATIVE_OPS = {ContractOp.AND, ContractOp.OR, ContractOp.EQ, ContractOp.NE, ContractOp.ADD, ContractOp.MUL}


@dataclass(frozen=True, slots=True)
class ContractExpr:
    op: ContractOp
    type: ContractType
    args: tuple["ContractExpr", ...] = ()
    value: str | int | None = None

    def __post_init__(self) -> None:
        if self.op in _LEAF_OPS:
            if self.args:
                raise ElementwiseSchemaError(f"{self.op.value} contract leaf cannot have arguments")
            if self.value is None:
                raise ElementwiseSchemaError(f"{self.op.value} contract leaf needs a value")
        else:
            if self.value is not None:
                raise ElementwiseSchemaError(f"{self.op.value} contract node cannot have a leaf value")
        if self.op is ContractOp.VARIABLE:
            _text(self.value, "contract variable")
        elif self.op is ContractOp.INTEGER:
            if type(self.value) is not int or self.type.kind is not ContractTypeKind.INTEGER:
                raise ElementwiseSchemaError("integer literal needs an integer type/value")
        elif self.op is ContractOp.NULL:
            if self.value != "NULL" or self.type.kind is not ContractTypeKind.POINTER:
                raise ElementwiseSchemaError("null literal needs pointer type and NULL value")
        elif self.op is ContractOp.SIZEOF:
            _text(self.value, "sizeof operand")
            if self.type != SIZE_T:
                raise ElementwiseSchemaError("sizeof result must have size_t type")
        elif self.op in _UNARY_OPS:
            if len(self.args) != 1 or self.args[0].type != BOOL or self.type != BOOL:
                raise ElementwiseSchemaError("logical not needs one boolean argument/result")
        elif self.op in _BOOL_NARY_OPS:
            if len(self.args) < 2 or self.type != BOOL or any(arg.type != BOOL for arg in self.args):
                raise ElementwiseSchemaError("logical conjunction/disjunction needs boolean arguments")
        elif self.op in _COMPARE_OPS:
            if len(self.args) != 2 or self.type != BOOL or self.args[0].type != self.args[1].type:
                raise ElementwiseSchemaError("comparison needs two equal typed arguments and bool result")
            if self.op in {ContractOp.LT, ContractOp.LE, ContractOp.GT, ContractOp.GE} and (
                self.args[0].type.kind is not ContractTypeKind.INTEGER
            ):
                raise ElementwiseSchemaError("ordered comparison needs integer arguments")
        elif self.op in _ARITHMETIC_OPS:
            if (
                len(self.args) != 2
                or self.type.kind is not ContractTypeKind.INTEGER
                or any(arg.type != self.type for arg in self.args)
            ):
                raise ElementwiseSchemaError("arithmetic needs two equal integer arguments/results")
        elif self.op not in _LEAF_OPS:
            raise ElementwiseSchemaError(f"unsupported contract operator {self.op!r}")
        if self.op in _COMMUTATIVE_OPS:
            records = [canonical_json(argument.to_record()) for argument in self.args]
            if records != sorted(records):
                raise ElementwiseSchemaError(
                    f"{self.op.value} contract arguments must be canonically sorted"
                )
        if self.op in {ContractOp.AND, ContractOp.OR} and any(
            argument.op is self.op for argument in self.args
        ):
            raise ElementwiseSchemaError(
                f"nested {self.op.value} contract nodes must be flattened"
            )

    @classmethod
    def variable(cls, name: str, value_type: ContractType) -> "ContractExpr":
        return cls(ContractOp.VARIABLE, value_type, value=name)

    @classmethod
    def integer(cls, value: int, value_type: ContractType = SIZE_T) -> "ContractExpr":
        return cls(ContractOp.INTEGER, value_type, value=value)

    @classmethod
    def sizeof(cls, c_spelling: str) -> "ContractExpr":
        return cls(ContractOp.SIZEOF, SIZE_T, value=c_spelling)

    @classmethod
    def make(
        cls,
        op: ContractOp,
        *args: "ContractExpr",
        result_type: ContractType | None = None,
    ) -> "ContractExpr":
        if op in _COMPARE_OPS or op in _BOOL_NARY_OPS or op is ContractOp.NOT:
            result_type = BOOL
        elif result_type is None:
            if not args:
                raise ElementwiseSchemaError("non-leaf expression needs an argument type")
            result_type = args[0].type
        normalized = tuple(args)
        if op in {ContractOp.AND, ContractOp.OR}:
            flattened = []
            for argument in normalized:
                flattened.extend(argument.args if argument.op is op else (argument,))
            normalized = tuple(flattened)
        if op in _COMMUTATIVE_OPS:
            normalized = tuple(sorted(normalized, key=lambda item: canonical_json(item.to_record())))
        return cls(op=op, type=result_type, args=normalized)

    def to_record(self) -> dict[str, Any]:
        return {
            "op": self.op.value,
            "type": self.type.to_record(),
            "args": [argument.to_record() for argument in self.args],
            "value": self.value,
        }

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "ContractExpr":
        _exact_keys(data, {"op", "type", "args", "value"}, "contract expression")
        return cls(
            op=_enum(ContractOp, data["op"], "contract operator"),
            type=ContractType.from_record(_mapping(data["type"], "contract expression type")),
            args=tuple(
                cls.from_record(_mapping(item, "contract argument"))
                for item in _sequence(data["args"], "contract arguments")
            ),
            value=data["value"],
        )


@dataclass(frozen=True, slots=True)
class EntryContract:
    clauses: tuple[ContractExpr, ...]

    def __post_init__(self) -> None:
        if any(clause.type != BOOL for clause in self.clauses):
            raise ElementwiseSchemaError("entry contract clauses must be boolean")
        records = [canonical_json(clause.to_record()) for clause in self.clauses]
        if records != sorted(set(records)):
            raise ElementwiseSchemaError("entry contract clauses must be sorted and unique")

    @classmethod
    def normalized(cls, clauses: Sequence[ContractExpr]) -> "EntryContract":
        unique = {canonical_json(clause.to_record()): clause for clause in clauses}
        return cls(tuple(unique[key] for key in sorted(unique)))

    def to_record(self) -> dict[str, Any]:
        return {"clauses": [clause.to_record() for clause in self.clauses]}

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "EntryContract":
        _exact_keys(data, {"clauses"}, "entry contract")
        return cls(
            tuple(
                ContractExpr.from_record(_mapping(item, "entry contract clause"))
                for item in _sequence(data["clauses"], "entry contract clauses")
            )
        )

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.to_record())


@dataclass(frozen=True, slots=True)
class ContractBinding:
    neon: EntryContract
    rvv: EntryContract

    def __post_init__(self) -> None:
        if self.neon.to_record() != self.rvv.to_record():
            raise ElementwiseSchemaError("normalized Neon/RVV entry contracts differ")

    @property
    def shared(self) -> EntryContract:
        return self.neon

    def to_record(self) -> dict[str, Any]:
        return {
            "neon": self.neon.to_record(),
            "rvv": self.rvv.to_record(),
            "shared_sha256": self.shared.sha256,
        }

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "ContractBinding":
        _exact_keys(data, {"neon", "rvv", "shared_sha256"}, "contract binding")
        result = cls(
            EntryContract.from_record(_mapping(data["neon"], "Neon contract")),
            EntryContract.from_record(_mapping(data["rvv"], "RVV contract")),
        )
        if _digest(data["shared_sha256"], "shared contract digest") != result.shared.sha256:
            raise ElementwiseSchemaError("shared contract digest disagrees with clauses")
        return result


@dataclass(frozen=True, slots=True)
class SourceArtifact:
    architecture: Architecture
    path: str
    function: str
    source_sha256: str
    facade_path: str
    facade_sha256: str
    preprocessed_sha256: str

    def __post_init__(self) -> None:
        _relative_path(self.path, "source path")
        _text(self.function, "source function")
        _digest(self.source_sha256, "source digest")
        _relative_path(self.facade_path, "facade path")
        _digest(self.facade_sha256, "facade digest")
        _digest(self.preprocessed_sha256, "preprocessed digest")

    def to_record(self) -> dict[str, Any]:
        return {
            "architecture": self.architecture.value,
            "path": self.path,
            "function": self.function,
            "source_sha256": self.source_sha256,
            "facade_path": self.facade_path,
            "facade_sha256": self.facade_sha256,
            "preprocessed_sha256": self.preprocessed_sha256,
        }

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "SourceArtifact":
        expected = {
            "architecture", "path", "function", "source_sha256", "facade_path",
            "facade_sha256", "preprocessed_sha256",
        }
        _exact_keys(data, expected, "source artifact")
        return cls(
            architecture=_enum(Architecture, data["architecture"], "source architecture"),
            path=_relative_path(data["path"], "source path"),
            function=_text(data["function"], "source function"),
            source_sha256=_digest(data["source_sha256"], "source digest"),
            facade_path=_relative_path(data["facade_path"], "facade path"),
            facade_sha256=_digest(data["facade_sha256"], "facade digest"),
            preprocessed_sha256=_digest(data["preprocessed_sha256"], "preprocessed digest"),
        )


@dataclass(frozen=True, slots=True)
class CapabilityRef:
    capability_id: str
    version: int
    sha256: str

    def __post_init__(self) -> None:
        _text(self.capability_id, "capability id")
        if type(self.version) is not int or self.version <= 0:
            raise ElementwiseSchemaError("capability version must be positive")
        _digest(self.sha256, "capability digest")

    def to_record(self) -> dict[str, Any]:
        return {"capability_id": self.capability_id, "version": self.version, "sha256": self.sha256}

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "CapabilityRef":
        _exact_keys(data, {"capability_id", "version", "sha256"}, "capability reference")
        version = data["version"]
        if type(version) is not int:
            raise ElementwiseSchemaError("capability version must be an integer")
        return cls(
            capability_id=_text(data["capability_id"], "capability id"),
            version=version,
            sha256=_digest(data["sha256"], "capability digest"),
        )


@dataclass(frozen=True, slots=True)
class LayoutInstance:
    capability: CapabilityRef
    element_c_type: str
    input_streams: tuple[str, ...]
    output_streams: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.element_c_type, "layout element C type")
        for field, values in (("input streams", self.input_streams), ("output streams", self.output_streams)):
            if not values or tuple(sorted(set(values))) != values:
                raise ElementwiseSchemaError(f"{field} must be non-empty, sorted, and unique")
            for value in values:
                _text(value, field)

    def to_record(self) -> dict[str, Any]:
        return {
            "capability": self.capability.to_record(),
            "element_c_type": self.element_c_type,
            "input_streams": list(self.input_streams),
            "output_streams": list(self.output_streams),
        }

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "LayoutInstance":
        _exact_keys(data, {"capability", "element_c_type", "input_streams", "output_streams"}, "layout instance")
        return cls(
            capability=CapabilityRef.from_record(_mapping(data["capability"], "layout capability")),
            element_c_type=_text(data["element_c_type"], "layout element C type"),
            input_streams=tuple(_text(item, "input stream") for item in _sequence(data["input_streams"], "input streams")),
            output_streams=tuple(_text(item, "output stream") for item in _sequence(data["output_streams"], "output streams")),
        )


@dataclass(frozen=True, slots=True)
class ScheduleInstance:
    architecture: Architecture
    capability: CapabilityRef
    parameters: tuple[tuple[str, int | str | bool], ...]
    control_sha256: str

    def __post_init__(self) -> None:
        keys = [key for key, _ in self.parameters]
        if keys != sorted(set(keys)):
            raise ElementwiseSchemaError("schedule parameter names must be sorted and unique")
        for key, value in self.parameters:
            _text(key, "schedule parameter name")
            if not isinstance(value, (int, str, bool)):
                raise ElementwiseSchemaError("schedule parameter value must be scalar JSON")
        _digest(self.control_sha256, "schedule control digest")

    def to_record(self) -> dict[str, Any]:
        return {
            "architecture": self.architecture.value,
            "capability": self.capability.to_record(),
            "parameters": {key: value for key, value in self.parameters},
            "control_sha256": self.control_sha256,
        }

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "ScheduleInstance":
        _exact_keys(data, {"architecture", "capability", "parameters", "control_sha256"}, "schedule instance")
        parameters = _mapping(data["parameters"], "schedule parameters")
        return cls(
            architecture=_enum(Architecture, data["architecture"], "schedule architecture"),
            capability=CapabilityRef.from_record(_mapping(data["capability"], "schedule capability")),
            parameters=tuple(sorted(parameters.items())),
            control_sha256=_digest(data["control_sha256"], "schedule control digest"),
        )


@dataclass(frozen=True, slots=True)
class LocalAssertionFact:
    architecture: Architecture
    parent_control: str
    expression: ContractExpr
    derivation: str
    source_sha256: str

    def __post_init__(self) -> None:
        _text(self.parent_control, "local assertion parent control")
        if self.expression.type != BOOL:
            raise ElementwiseSchemaError("local assertion must be boolean")
        if self.derivation != "fixed-tail-remainder":
            raise ElementwiseSchemaError("phase one supports only fixed-tail local assertions")
        _digest(self.source_sha256, "local assertion source digest")

    def to_record(self) -> dict[str, Any]:
        return {
            "architecture": self.architecture.value,
            "parent_control": self.parent_control,
            "expression": self.expression.to_record(),
            "derivation": self.derivation,
            "source_sha256": self.source_sha256,
        }

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "LocalAssertionFact":
        _exact_keys(data, {"architecture", "parent_control", "expression", "derivation", "source_sha256"}, "local assertion fact")
        return cls(
            architecture=_enum(Architecture, data["architecture"], "assertion architecture"),
            parent_control=_text(data["parent_control"], "local assertion parent control"),
            expression=ContractExpr.from_record(_mapping(data["expression"], "local assertion expression")),
            derivation=_text(data["derivation"], "local assertion derivation"),
            source_sha256=_digest(data["source_sha256"], "local assertion source digest"),
        )


@dataclass(frozen=True, slots=True)
class ProgramManifest:
    compiler_sha256: str
    sources: tuple[SourceArtifact, SourceArtifact]
    contracts: ContractBinding
    intrinsic_capabilities: tuple[CapabilityRef, ...]
    layout: LayoutInstance
    schedules: tuple[ScheduleInstance, ScheduleInstance]
    local_assertions: tuple[LocalAssertionFact, ...]
    consumed_effects_sha256: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ElementwiseSchemaError(f"unsupported manifest schema version {self.schema_version}")
        _digest(self.compiler_sha256, "compiler digest")
        if tuple(source.architecture for source in self.sources) != (Architecture.NEON, Architecture.RVV):
            raise ElementwiseSchemaError("manifest sources must be Neon then RVV")
        if tuple(schedule.architecture for schedule in self.schedules) != (Architecture.NEON, Architecture.RVV):
            raise ElementwiseSchemaError("manifest schedules must be Neon then RVV")
        capability_keys = [(item.capability_id, item.version, item.sha256) for item in self.intrinsic_capabilities]
        if capability_keys != sorted(set(capability_keys)):
            raise ElementwiseSchemaError("intrinsic capabilities must be sorted and unique")
        assertion_keys = [canonical_json(item.to_record()) for item in self.local_assertions]
        if assertion_keys != sorted(set(assertion_keys)):
            raise ElementwiseSchemaError("local assertions must be sorted and unique")
        _digest(self.consumed_effects_sha256, "consumed effects digest")

    def unsigned_record(self) -> dict[str, Any]:
        return {
            "artifact_kind": "elementwise-program-manifest",
            "schema_version": self.schema_version,
            "compiler_sha256": self.compiler_sha256,
            "sources": [source.to_record() for source in self.sources],
            "contracts": self.contracts.to_record(),
            "intrinsic_capabilities": [item.to_record() for item in self.intrinsic_capabilities],
            "layout": self.layout.to_record(),
            "schedules": [schedule.to_record() for schedule in self.schedules],
            "local_assertions": [item.to_record() for item in self.local_assertions],
            "consumed_effects_sha256": self.consumed_effects_sha256,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.unsigned_record())

    def to_record(self) -> dict[str, Any]:
        return {**self.unsigned_record(), "manifest_sha256": self.sha256}

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "ProgramManifest":
        expected = {
            "artifact_kind", "schema_version", "compiler_sha256", "sources",
            "contracts", "intrinsic_capabilities", "layout", "schedules",
            "local_assertions", "consumed_effects_sha256", "manifest_sha256",
        }
        _exact_keys(data, expected, "program manifest")
        if data["artifact_kind"] != "elementwise-program-manifest":
            raise ElementwiseSchemaError("invalid program manifest artifact kind")
        sources = tuple(SourceArtifact.from_record(_mapping(item, "source artifact")) for item in _sequence(data["sources"], "sources"))
        schedules = tuple(ScheduleInstance.from_record(_mapping(item, "schedule instance")) for item in _sequence(data["schedules"], "schedules"))
        if len(sources) != 2 or len(schedules) != 2:
            raise ElementwiseSchemaError("manifest needs exactly two sources and schedules")
        result = cls(
            schema_version=data["schema_version"],
            compiler_sha256=_digest(data["compiler_sha256"], "compiler digest"),
            sources=(sources[0], sources[1]),
            contracts=ContractBinding.from_record(_mapping(data["contracts"], "contract binding")),
            intrinsic_capabilities=tuple(CapabilityRef.from_record(_mapping(item, "intrinsic capability")) for item in _sequence(data["intrinsic_capabilities"], "intrinsic capabilities")),
            layout=LayoutInstance.from_record(_mapping(data["layout"], "layout")),
            schedules=(schedules[0], schedules[1]),
            local_assertions=tuple(LocalAssertionFact.from_record(_mapping(item, "local assertion")) for item in _sequence(data["local_assertions"], "local assertions")),
            consumed_effects_sha256=_digest(data["consumed_effects_sha256"], "consumed effects digest"),
        )
        if _digest(data["manifest_sha256"], "manifest digest") != result.sha256:
            raise ElementwiseSchemaError("program manifest digest disagrees with contents")
        return result


class ArtifactKind(str, Enum):
    MODELS = "models"
    SPEC = "spec"
    PROOF = "proof"


@dataclass(frozen=True, slots=True)
class GeneratedArtifact:
    kind: ArtifactKind
    path: str
    sha256: str
    parent_sha256: str

    def __post_init__(self) -> None:
        _relative_path(self.path, "generated artifact path")
        _digest(self.sha256, "generated artifact digest")
        _digest(self.parent_sha256, "generated artifact parent digest")

    def to_record(self) -> dict[str, Any]:
        return {"kind": self.kind.value, "path": self.path, "sha256": self.sha256, "parent_sha256": self.parent_sha256}

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "GeneratedArtifact":
        _exact_keys(data, {"kind", "path", "sha256", "parent_sha256"}, "generated artifact")
        return cls(
            kind=_enum(ArtifactKind, data["kind"], "generated artifact kind"),
            path=_relative_path(data["path"], "generated artifact path"),
            sha256=_digest(data["sha256"], "generated artifact digest"),
            parent_sha256=_digest(data["parent_sha256"], "generated artifact parent digest"),
        )


class ClaimScope(str, Enum):
    VALUE = "value"


@dataclass(frozen=True, slots=True)
class ProofTask:
    manifest_sha256: str
    models: GeneratedArtifact
    spec: GeneratedArtifact
    proof_path: str
    module: str
    theorem: str
    elaborated_type_sha256: str
    checker_policy_sha256: str
    toolchain_sha256: str
    claim_scope: ClaimScope = ClaimScope.VALUE
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ElementwiseSchemaError("unsupported proof-task schema version")
        _digest(self.manifest_sha256, "proof-task manifest digest")
        if self.models.kind is not ArtifactKind.MODELS or self.models.parent_sha256 != self.manifest_sha256:
            raise ElementwiseSchemaError("Models artifact is not bound to manifest")
        if self.spec.kind is not ArtifactKind.SPEC or self.spec.parent_sha256 != self.models.sha256:
            raise ElementwiseSchemaError("Spec artifact is not bound to Models")
        _relative_path(self.proof_path, "proof path")
        if _IDENTIFIER_RE.fullmatch(self.module) is None or _IDENTIFIER_RE.fullmatch(self.theorem) is None:
            raise ElementwiseSchemaError("proof module/theorem must be Lean identifiers")
        _digest(self.elaborated_type_sha256, "elaborated theorem type digest")
        _digest(self.checker_policy_sha256, "checker policy digest")
        _digest(self.toolchain_sha256, "toolchain digest")

    def unsigned_record(self) -> dict[str, Any]:
        return {
            "artifact_kind": "elementwise-proof-task",
            "schema_version": self.schema_version,
            "manifest_sha256": self.manifest_sha256,
            "models": self.models.to_record(),
            "spec": self.spec.to_record(),
            "proof_path": self.proof_path,
            "module": self.module,
            "theorem": self.theorem,
            "elaborated_type_sha256": self.elaborated_type_sha256,
            "checker_policy_sha256": self.checker_policy_sha256,
            "toolchain_sha256": self.toolchain_sha256,
            "claim_scope": self.claim_scope.value,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.unsigned_record())

    def to_record(self) -> dict[str, Any]:
        return {**self.unsigned_record(), "proof_task_sha256": self.sha256}

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "ProofTask":
        expected = {
            "artifact_kind", "schema_version", "manifest_sha256", "models", "spec",
            "proof_path", "module", "theorem", "elaborated_type_sha256",
            "checker_policy_sha256", "toolchain_sha256", "claim_scope", "proof_task_sha256",
        }
        _exact_keys(data, expected, "proof task")
        if data["artifact_kind"] != "elementwise-proof-task":
            raise ElementwiseSchemaError("invalid proof-task artifact kind")
        result = cls(
            schema_version=data["schema_version"],
            manifest_sha256=_digest(data["manifest_sha256"], "proof-task manifest digest"),
            models=GeneratedArtifact.from_record(_mapping(data["models"], "models artifact")),
            spec=GeneratedArtifact.from_record(_mapping(data["spec"], "spec artifact")),
            proof_path=_relative_path(data["proof_path"], "proof path"),
            module=_text(data["module"], "proof module"),
            theorem=_text(data["theorem"], "proof theorem"),
            elaborated_type_sha256=_digest(data["elaborated_type_sha256"], "elaborated theorem type digest"),
            checker_policy_sha256=_digest(data["checker_policy_sha256"], "checker policy digest"),
            toolchain_sha256=_digest(data["toolchain_sha256"], "toolchain digest"),
            claim_scope=_enum(ClaimScope, data["claim_scope"], "claim scope"),
        )
        if _digest(data["proof_task_sha256"], "proof-task digest") != result.sha256:
            raise ElementwiseSchemaError("proof-task digest disagrees with contents")
        return result


class ResultStatus(str, Enum):
    PARSE_UNSUPPORTED = "parse-unsupported"
    INTRINSIC_MISSING = "intrinsic-missing"
    INTRINSIC_AMBIGUOUS = "intrinsic-ambiguous"
    ENTRY_CONTRACT_MISMATCH = "entry-contract-mismatch"
    LAYOUT_UNRECOGNIZED = "layout-unrecognized"
    FAMILY_UNRECOGNIZED = "family-unrecognized"
    GENERATION_FAILED = "generation-failed"
    PROOF_SEARCH_FAILED = "proof-search-failed"
    COUNTEREXAMPLE = "counterexample"
    LEAN_FAILED = "lean-failed"
    VERIFIED_VALUE = "verified(value)"


@dataclass(frozen=True, slots=True)
class Result:
    status: ResultStatus
    proof_task_sha256: str | None
    proof_sha256: str | None
    checker_sha256: str
    toolchain_sha256: str
    start_closure_sha256: str | None
    end_closure_sha256: str | None
    detail: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ElementwiseSchemaError("unsupported result schema version")
        _optional_digest(self.proof_task_sha256, "result proof-task digest")
        _optional_digest(self.proof_sha256, "result proof digest")
        _digest(self.checker_sha256, "result checker digest")
        _digest(self.toolchain_sha256, "result toolchain digest")
        _optional_digest(self.start_closure_sha256, "result start-closure digest")
        _optional_digest(self.end_closure_sha256, "result end-closure digest")
        _text(self.detail, "result detail")
        if self.status is ResultStatus.VERIFIED_VALUE:
            required = (
                self.proof_task_sha256,
                self.proof_sha256,
                self.start_closure_sha256,
                self.end_closure_sha256,
            )
            if any(item is None for item in required):
                raise ElementwiseSchemaError("verified result needs complete proof/closure bindings")
            if self.start_closure_sha256 != self.end_closure_sha256:
                raise ElementwiseSchemaError("verified result protected closure changed")

    def unsigned_record(self) -> dict[str, Any]:
        return {
            "artifact_kind": "elementwise-result",
            "schema_version": self.schema_version,
            "status": self.status.value,
            "proof_task_sha256": self.proof_task_sha256,
            "proof_sha256": self.proof_sha256,
            "checker_sha256": self.checker_sha256,
            "toolchain_sha256": self.toolchain_sha256,
            "start_closure_sha256": self.start_closure_sha256,
            "end_closure_sha256": self.end_closure_sha256,
            "detail": self.detail,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.unsigned_record())

    def to_record(self) -> dict[str, Any]:
        return {**self.unsigned_record(), "result_sha256": self.sha256}

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "Result":
        expected = {
            "artifact_kind", "schema_version", "status", "proof_task_sha256", "proof_sha256",
            "checker_sha256", "toolchain_sha256", "start_closure_sha256",
            "end_closure_sha256", "detail", "result_sha256",
        }
        _exact_keys(data, expected, "result")
        if data["artifact_kind"] != "elementwise-result":
            raise ElementwiseSchemaError("invalid result artifact kind")
        result = cls(
            schema_version=data["schema_version"],
            status=_enum(ResultStatus, data["status"], "result status"),
            proof_task_sha256=_optional_digest(data["proof_task_sha256"], "result proof-task digest"),
            proof_sha256=_optional_digest(data["proof_sha256"], "result proof digest"),
            checker_sha256=_digest(data["checker_sha256"], "result checker digest"),
            toolchain_sha256=_digest(data["toolchain_sha256"], "result toolchain digest"),
            start_closure_sha256=_optional_digest(data["start_closure_sha256"], "result start-closure digest"),
            end_closure_sha256=_optional_digest(data["end_closure_sha256"], "result end-closure digest"),
            detail=_text(data["detail"], "result detail"),
        )
        if _digest(data["result_sha256"], "result digest") != result.sha256:
            raise ElementwiseSchemaError("result digest disagrees with contents")
        return result
