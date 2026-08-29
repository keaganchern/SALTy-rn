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
EXTERNAL_CONDITION_SCHEMA_VERSION = 2
PROGRAM_MANIFEST_SCHEMA_VERSION = 2
PROOF_TASK_SCHEMA_VERSION = 2
RESULT_SCHEMA_VERSION = 2
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
    stream_c_types: tuple[tuple[str, str], ...]
    input_streams: tuple[str, ...]
    output_streams: tuple[str, ...]
    broadcast_input_streams: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        for field, values in (("input streams", self.input_streams), ("output streams", self.output_streams)):
            if not values or tuple(sorted(set(values))) != values:
                raise ElementwiseSchemaError(f"{field} must be non-empty, sorted, and unique")
            for value in values:
                _text(value, field)
        if tuple(sorted(set(self.broadcast_input_streams))) != self.broadcast_input_streams:
            raise ElementwiseSchemaError(
                "broadcast input streams must be sorted and unique"
            )
        if set(self.input_streams) & set(self.broadcast_input_streams):
            raise ElementwiseSchemaError("varying and broadcast input streams overlap")
        stream_names = (
            self.input_streams + self.broadcast_input_streams + self.output_streams
        )
        type_names = tuple(name for name, _ in self.stream_c_types)
        if type_names != tuple(sorted(stream_names)):
            raise ElementwiseSchemaError(
                "layout stream C types must name every input/output stream exactly once"
            )
        for name, c_type in self.stream_c_types:
            _text(name, "layout stream name")
            _text(c_type, "layout stream C type")

    def to_record(self) -> dict[str, Any]:
        return {
            "capability": self.capability.to_record(),
            "stream_c_types": [
                {"stream": stream, "c_type": c_type}
                for stream, c_type in self.stream_c_types
            ],
            "input_streams": list(self.input_streams),
            "broadcast_input_streams": list(self.broadcast_input_streams),
            "output_streams": list(self.output_streams),
        }

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "LayoutInstance":
        expected = {"capability", "stream_c_types", "input_streams", "output_streams"}
        actual = set(data)
        if actual not in {frozenset(expected), frozenset(expected | {"broadcast_input_streams"})}:
            raise ElementwiseSchemaError("layout instance has unexpected fields")
        stream_types: list[tuple[str, str]] = []
        for item in _sequence(data["stream_c_types"], "layout stream C types"):
            record = _mapping(item, "layout stream C type")
            _exact_keys(record, {"stream", "c_type"}, "layout stream C type")
            stream_types.append(
                (
                    _text(record["stream"], "layout stream name"),
                    _text(record["c_type"], "layout stream C type"),
                )
            )
        return cls(
            capability=CapabilityRef.from_record(_mapping(data["capability"], "layout capability")),
            stream_c_types=tuple(stream_types),
            input_streams=tuple(_text(item, "input stream") for item in _sequence(data["input_streams"], "input streams")),
            output_streams=tuple(_text(item, "output stream") for item in _sequence(data["output_streams"], "output streams")),
            broadcast_input_streams=tuple(
                _text(item, "broadcast input stream")
                for item in _sequence(
                    data.get("broadcast_input_streams", ()),
                    "broadcast input streams",
                )
            ),
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


class ExternalConditionStatus(str, Enum):
    """Whether facts outside the isolated kernels are needed and established."""

    NOT_REQUIRED = "not-required"
    REQUIRED_MISSING = "required-missing"
    RESOLVED = "resolved"


class ExternalConditionScope(str, Enum):
    """Domain whose caller conditions were audited."""

    LOCAL_UNCONDITIONAL = "local-unconditional-claim"
    XNNPACK_REGISTERED = "xnnpack-registered-domain"


@dataclass(frozen=True, slots=True)
class EvidenceSource:
    """One immutable repository file used by an external-condition audit."""

    role: str
    path: str
    sha256: str
    symbols: tuple[str, ...]

    def __post_init__(self) -> None:
        _text(self.role, "evidence source role")
        _relative_path(self.path, "evidence source path")
        _digest(self.sha256, "evidence source digest")
        if not self.symbols:
            raise ElementwiseSchemaError("evidence source needs at least one symbol")
        if tuple(sorted(set(self.symbols))) != self.symbols:
            raise ElementwiseSchemaError("evidence source symbols must be sorted and unique")
        for symbol in self.symbols:
            _text(symbol, "evidence source symbol")

    def to_record(self) -> dict[str, Any]:
        return {
            "role": self.role,
            "path": self.path,
            "sha256": self.sha256,
            "symbols": list(self.symbols),
        }

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "EvidenceSource":
        _exact_keys(data, {"role", "path", "sha256", "symbols"}, "evidence source")
        return cls(
            role=_text(data["role"], "evidence source role"),
            path=_relative_path(data["path"], "evidence source path"),
            sha256=_digest(data["sha256"], "evidence source digest"),
            symbols=tuple(
                _text(item, "evidence source symbol")
                for item in _sequence(data["symbols"], "evidence source symbols")
            ),
        )


@dataclass(frozen=True, slots=True)
class ExternalConditionEvidence:
    """Content-addressed result of tracing facts outside a kernel pair.

    ``candidate_contract`` is deliberately not an assumption.  It records a
    condition suggested by the semantics audit.  Only ``RESOLVED`` evidence may
    make that condition available to a proof task.
    """

    local_sources_sha256: str
    scope: ExternalConditionScope
    upstream_root: str | None
    upstream_commit: str | None
    parameter_type: str
    initializer: str
    status: ExternalConditionStatus
    candidate_contract: EntryContract
    sources: tuple[EvidenceSource, ...]
    extractor_sha256: str
    derivation: str
    detail: str
    schema_version: int = EXTERNAL_CONDITION_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != EXTERNAL_CONDITION_SCHEMA_VERSION:
            raise ElementwiseSchemaError("unsupported external-condition schema version")
        _digest(self.local_sources_sha256, "external-condition local-sources digest")
        if self.scope is ExternalConditionScope.XNNPACK_REGISTERED:
            if self.upstream_root is None or self.upstream_commit is None:
                raise ElementwiseSchemaError(
                    "registered-domain evidence needs an upstream root and commit"
                )
            _relative_path(self.upstream_root, "external-condition upstream root")
            if re.fullmatch(r"[0-9a-f]{40}", self.upstream_commit) is None:
                raise ElementwiseSchemaError(
                    "external-condition upstream commit must be a Git SHA-1"
                )
        elif self.upstream_root is not None or self.upstream_commit is not None:
            raise ElementwiseSchemaError(
                "local unconditional evidence cannot name an upstream checkout"
            )
        _text(self.parameter_type, "external-condition parameter type")
        _text(self.initializer, "external-condition initializer")
        _digest(self.extractor_sha256, "external-condition extractor digest")
        _text(self.derivation, "external-condition derivation")
        _text(self.detail, "external-condition detail")
        source_keys = [canonical_json(source.to_record()) for source in self.sources]
        if not source_keys or source_keys != sorted(set(source_keys)):
            raise ElementwiseSchemaError("evidence sources must be sorted and unique")
        if self.status is ExternalConditionStatus.NOT_REQUIRED and self.candidate_contract.clauses:
            raise ElementwiseSchemaError("not-required evidence cannot carry candidate conditions")
        if self.status is ExternalConditionStatus.RESOLVED and not self.candidate_contract.clauses:
            raise ElementwiseSchemaError("resolved evidence needs a non-empty contract")
        if (
            self.scope is ExternalConditionScope.LOCAL_UNCONDITIONAL
            and self.status is not ExternalConditionStatus.NOT_REQUIRED
        ):
            raise ElementwiseSchemaError(
                "an unconditional local claim cannot depend on an external condition"
            )

    def unsigned_record(self) -> dict[str, Any]:
        return {
            "artifact_kind": "elementwise-external-condition",
            "schema_version": self.schema_version,
            "local_sources_sha256": self.local_sources_sha256,
            "scope": self.scope.value,
            "upstream_root": self.upstream_root,
            "upstream_commit": self.upstream_commit,
            "parameter_type": self.parameter_type,
            "initializer": self.initializer,
            "status": self.status.value,
            "candidate_contract": self.candidate_contract.to_record(),
            "sources": [source.to_record() for source in self.sources],
            "extractor_sha256": self.extractor_sha256,
            "derivation": self.derivation,
            "detail": self.detail,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.unsigned_record())

    def to_record(self) -> dict[str, Any]:
        return {**self.unsigned_record(), "external_condition_sha256": self.sha256}

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "ExternalConditionEvidence":
        expected = {
            "artifact_kind", "schema_version", "local_sources_sha256", "scope",
            "upstream_root", "upstream_commit", "parameter_type", "initializer",
            "status", "candidate_contract", "sources", "extractor_sha256",
            "derivation", "detail", "external_condition_sha256",
        }
        _exact_keys(data, expected, "external-condition evidence")
        if data["artifact_kind"] != "elementwise-external-condition":
            raise ElementwiseSchemaError("invalid external-condition artifact kind")
        result = cls(
            schema_version=data["schema_version"],
            local_sources_sha256=_digest(
                data["local_sources_sha256"], "external-condition local-sources digest"
            ),
            scope=_enum(
                ExternalConditionScope, data["scope"], "external-condition scope"
            ),
            upstream_root=(
                None
                if data["upstream_root"] is None
                else _relative_path(
                    data["upstream_root"], "external-condition upstream root"
                )
            ),
            upstream_commit=(
                None
                if data["upstream_commit"] is None
                else _text(data["upstream_commit"], "external-condition upstream commit")
            ),
            parameter_type=_text(data["parameter_type"], "external-condition parameter type"),
            initializer=_text(data["initializer"], "external-condition initializer"),
            status=_enum(
                ExternalConditionStatus, data["status"], "external-condition status"
            ),
            candidate_contract=EntryContract.from_record(
                _mapping(data["candidate_contract"], "external-condition candidate contract")
            ),
            sources=tuple(
                EvidenceSource.from_record(_mapping(item, "evidence source"))
                for item in _sequence(data["sources"], "evidence sources")
            ),
            extractor_sha256=_digest(
                data["extractor_sha256"], "external-condition extractor digest"
            ),
            derivation=_text(data["derivation"], "external-condition derivation"),
            detail=_text(data["detail"], "external-condition detail"),
        )
        if _digest(
            data["external_condition_sha256"], "external-condition digest"
        ) != result.sha256:
            raise ElementwiseSchemaError(
                "external-condition digest disagrees with contents"
            )
        return result


@dataclass(frozen=True, slots=True)
class ExternalConditionRef:
    path: str
    sha256: str
    status: ExternalConditionStatus

    def __post_init__(self) -> None:
        _relative_path(self.path, "external-condition reference path")
        _digest(self.sha256, "external-condition reference digest")

    def to_record(self) -> dict[str, Any]:
        return {"path": self.path, "sha256": self.sha256, "status": self.status.value}

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "ExternalConditionRef":
        _exact_keys(data, {"path", "sha256", "status"}, "external-condition reference")
        return cls(
            path=_relative_path(data["path"], "external-condition reference path"),
            sha256=_digest(data["sha256"], "external-condition reference digest"),
            status=_enum(
                ExternalConditionStatus, data["status"], "external-condition reference status"
            ),
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
    external_condition: ExternalConditionRef
    schema_version: int = PROGRAM_MANIFEST_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PROGRAM_MANIFEST_SCHEMA_VERSION:
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
            "external_condition": self.external_condition.to_record(),
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
            "local_assertions", "consumed_effects_sha256", "external_condition",
            "manifest_sha256",
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
            external_condition=ExternalConditionRef.from_record(
                _mapping(data["external_condition"], "external-condition reference")
            ),
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


@dataclass(frozen=True, slots=True)
class CounterexampleWitness:
    """A concrete, Lean-checked disagreement between two generated functions."""

    manifest_sha256: str
    models_sha256: str
    spec_sha256: str
    claim: str
    left_function: str
    right_function: str
    parameter_values: tuple[tuple[str, int], ...]
    input_values: tuple[int, ...]
    left_output: int
    right_output: int
    lean_path: str
    lean_sha256: str
    checker_sha256: str
    toolchain_sha256: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ElementwiseSchemaError("unsupported counterexample schema version")
        for value, field in (
            (self.manifest_sha256, "counterexample manifest digest"),
            (self.models_sha256, "counterexample Models digest"),
            (self.spec_sha256, "counterexample Spec digest"),
            (self.lean_sha256, "counterexample Lean digest"),
            (self.checker_sha256, "counterexample checker digest"),
            (self.toolchain_sha256, "counterexample toolchain digest"),
        ):
            _digest(value, field)
        for value, field in (
            (self.claim, "counterexample claim"),
            (self.left_function, "counterexample left function"),
            (self.right_function, "counterexample right function"),
        ):
            if _IDENTIFIER_RE.fullmatch(value) is None:
                raise ElementwiseSchemaError(f"{field} must be a Lean identifier")
        keys = [name for name, _ in self.parameter_values]
        if keys != sorted(set(keys)):
            raise ElementwiseSchemaError(
                "counterexample parameter assignments must be sorted and unique"
            )
        if any(type(value) is not int for _, value in self.parameter_values):
            raise ElementwiseSchemaError("counterexample parameter values must be integers")
        if not self.input_values or any(type(value) is not int for value in self.input_values):
            raise ElementwiseSchemaError("counterexample inputs must be non-empty integers")
        if type(self.left_output) is not int or type(self.right_output) is not int:
            raise ElementwiseSchemaError("counterexample outputs must be integers")
        if self.left_output == self.right_output:
            raise ElementwiseSchemaError("counterexample outputs must disagree")
        _relative_path(self.lean_path, "counterexample Lean path")

    def unsigned_record(self) -> dict[str, Any]:
        return {
            "artifact_kind": "elementwise-counterexample",
            "schema_version": self.schema_version,
            "manifest_sha256": self.manifest_sha256,
            "models_sha256": self.models_sha256,
            "spec_sha256": self.spec_sha256,
            "claim": self.claim,
            "left_function": self.left_function,
            "right_function": self.right_function,
            "parameter_values": {
                name: value for name, value in self.parameter_values
            },
            "input_values": list(self.input_values),
            "left_output": self.left_output,
            "right_output": self.right_output,
            "lean_path": self.lean_path,
            "lean_sha256": self.lean_sha256,
            "checker_sha256": self.checker_sha256,
            "toolchain_sha256": self.toolchain_sha256,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.unsigned_record())

    def to_record(self) -> dict[str, Any]:
        return {**self.unsigned_record(), "counterexample_sha256": self.sha256}

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "CounterexampleWitness":
        expected = {
            "artifact_kind", "schema_version", "manifest_sha256", "models_sha256",
            "spec_sha256", "claim", "left_function", "right_function",
            "parameter_values", "input_values", "left_output", "right_output",
            "lean_path", "lean_sha256", "checker_sha256", "toolchain_sha256",
            "counterexample_sha256",
        }
        _exact_keys(data, expected, "counterexample")
        if data["artifact_kind"] != "elementwise-counterexample":
            raise ElementwiseSchemaError("invalid counterexample artifact kind")
        assignments = _mapping(data["parameter_values"], "counterexample parameters")
        if any(type(value) is not int for value in assignments.values()):
            raise ElementwiseSchemaError("counterexample parameter values must be integers")
        input_values = tuple(_sequence(data["input_values"], "counterexample inputs"))
        result = cls(
            schema_version=data["schema_version"],
            manifest_sha256=_digest(data["manifest_sha256"], "counterexample manifest digest"),
            models_sha256=_digest(data["models_sha256"], "counterexample Models digest"),
            spec_sha256=_digest(data["spec_sha256"], "counterexample Spec digest"),
            claim=_text(data["claim"], "counterexample claim"),
            left_function=_text(data["left_function"], "counterexample left function"),
            right_function=_text(data["right_function"], "counterexample right function"),
            parameter_values=tuple(sorted(assignments.items())),
            input_values=input_values,
            left_output=data["left_output"],
            right_output=data["right_output"],
            lean_path=_relative_path(data["lean_path"], "counterexample Lean path"),
            lean_sha256=_digest(data["lean_sha256"], "counterexample Lean digest"),
            checker_sha256=_digest(
                data["checker_sha256"], "counterexample checker digest"
            ),
            toolchain_sha256=_digest(
                data["toolchain_sha256"], "counterexample toolchain digest"
            ),
        )
        if _digest(data["counterexample_sha256"], "counterexample digest") != result.sha256:
            raise ElementwiseSchemaError("counterexample digest disagrees with contents")
        return result


class CrossPhaseAuditStatus(str, Enum):
    """Outcome of the mandatory audit for distinct Neon phase functions."""

    NOT_APPLICABLE = "not-applicable"
    BLOCKED_EXTERNAL_CONDITION = "blocked-external-condition"
    NO_COUNTEREXAMPLE_BOUNDED = "no-counterexample-bounded"
    COUNTEREXAMPLE = "counterexample"


@dataclass(frozen=True, slots=True)
class CrossPhaseAudit:
    """Content-addressed record of the generic cross-phase pre-proof audit."""

    manifest_sha256: str
    models_sha256: str
    spec_sha256: str
    claim: str
    status: CrossPhaseAuditStatus
    trial_count: int
    checker_sha256: str | None
    toolchain_sha256: str | None
    external_condition_sha256: str | None
    counterexample_sha256: str | None
    detail: str
    schema_version: int = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ElementwiseSchemaError("unsupported cross-phase audit schema version")
        for value, field in (
            (self.manifest_sha256, "cross-phase manifest digest"),
            (self.models_sha256, "cross-phase Models digest"),
            (self.spec_sha256, "cross-phase Spec digest"),
        ):
            _digest(value, field)
        if _IDENTIFIER_RE.fullmatch(self.claim) is None:
            raise ElementwiseSchemaError("cross-phase claim must be a Lean identifier")
        if type(self.trial_count) is not int or self.trial_count < 0:
            raise ElementwiseSchemaError("cross-phase trial count must be nonnegative")
        _optional_digest(self.checker_sha256, "cross-phase checker digest")
        _optional_digest(self.toolchain_sha256, "cross-phase toolchain digest")
        _optional_digest(
            self.external_condition_sha256, "cross-phase external-condition digest"
        )
        _optional_digest(
            self.counterexample_sha256, "cross-phase counterexample digest"
        )
        _text(self.detail, "cross-phase audit detail")
        if self.status is CrossPhaseAuditStatus.NOT_APPLICABLE:
            if self.trial_count != 0 or any(
                value is not None
                for value in (
                    self.checker_sha256,
                    self.toolchain_sha256,
                    self.external_condition_sha256,
                    self.counterexample_sha256,
                )
            ):
                raise ElementwiseSchemaError(
                    "not-applicable cross-phase audit cannot bind a search"
                )
        elif self.status is CrossPhaseAuditStatus.BLOCKED_EXTERNAL_CONDITION:
            if (
                self.trial_count != 0
                or self.external_condition_sha256 is None
                or self.checker_sha256 is not None
                or self.toolchain_sha256 is not None
                or self.counterexample_sha256 is not None
            ):
                raise ElementwiseSchemaError(
                    "blocked cross-phase audit needs only an external-condition binding"
                )
        else:
            if (
                self.trial_count <= 0
                or self.checker_sha256 is None
                or self.toolchain_sha256 is None
            ):
                raise ElementwiseSchemaError(
                    "searched cross-phase audit needs trials, checker, and toolchain"
                )
            if (
                self.status is CrossPhaseAuditStatus.COUNTEREXAMPLE
            ) != (self.counterexample_sha256 is not None):
                raise ElementwiseSchemaError(
                    "cross-phase counterexample status and witness binding disagree"
                )

    def unsigned_record(self) -> dict[str, Any]:
        return {
            "artifact_kind": "elementwise-cross-phase-audit",
            "schema_version": self.schema_version,
            "manifest_sha256": self.manifest_sha256,
            "models_sha256": self.models_sha256,
            "spec_sha256": self.spec_sha256,
            "claim": self.claim,
            "status": self.status.value,
            "trial_count": self.trial_count,
            "checker_sha256": self.checker_sha256,
            "toolchain_sha256": self.toolchain_sha256,
            "external_condition_sha256": self.external_condition_sha256,
            "counterexample_sha256": self.counterexample_sha256,
            "detail": self.detail,
        }

    @property
    def sha256(self) -> str:
        return canonical_sha256(self.unsigned_record())

    def to_record(self) -> dict[str, Any]:
        return {**self.unsigned_record(), "cross_phase_audit_sha256": self.sha256}

    @classmethod
    def from_record(cls, data: Mapping[str, Any]) -> "CrossPhaseAudit":
        expected = {
            "artifact_kind", "schema_version", "manifest_sha256", "models_sha256",
            "spec_sha256", "claim", "status", "trial_count", "checker_sha256",
            "toolchain_sha256", "external_condition_sha256",
            "counterexample_sha256", "detail", "cross_phase_audit_sha256",
        }
        _exact_keys(data, expected, "cross-phase audit")
        if data["artifact_kind"] != "elementwise-cross-phase-audit":
            raise ElementwiseSchemaError("invalid cross-phase audit artifact kind")
        trials = data["trial_count"]
        if type(trials) is not int:
            raise ElementwiseSchemaError("cross-phase trial count must be an integer")
        result = cls(
            schema_version=data["schema_version"],
            manifest_sha256=_digest(data["manifest_sha256"], "cross-phase manifest digest"),
            models_sha256=_digest(data["models_sha256"], "cross-phase Models digest"),
            spec_sha256=_digest(data["spec_sha256"], "cross-phase Spec digest"),
            claim=_text(data["claim"], "cross-phase claim"),
            status=_enum(CrossPhaseAuditStatus, data["status"], "cross-phase status"),
            trial_count=trials,
            checker_sha256=_optional_digest(data["checker_sha256"], "cross-phase checker digest"),
            toolchain_sha256=_optional_digest(data["toolchain_sha256"], "cross-phase toolchain digest"),
            external_condition_sha256=_optional_digest(
                data["external_condition_sha256"], "cross-phase external-condition digest"
            ),
            counterexample_sha256=_optional_digest(
                data["counterexample_sha256"], "cross-phase counterexample digest"
            ),
            detail=_text(data["detail"], "cross-phase audit detail"),
        )
        if _digest(
            data["cross_phase_audit_sha256"], "cross-phase audit digest"
        ) != result.sha256:
            raise ElementwiseSchemaError("cross-phase audit digest disagrees with contents")
        return result


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
    claim: str
    elaborated_type_sha256: str
    checker_policy_sha256: str
    toolchain_sha256: str
    claim_scope: ClaimScope = ClaimScope.VALUE
    schema_version: int = PROOF_TASK_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != PROOF_TASK_SCHEMA_VERSION:
            raise ElementwiseSchemaError("unsupported proof-task schema version")
        _digest(self.manifest_sha256, "proof-task manifest digest")
        if self.models.kind is not ArtifactKind.MODELS or self.models.parent_sha256 != self.manifest_sha256:
            raise ElementwiseSchemaError("Models artifact is not bound to manifest")
        if self.spec.kind is not ArtifactKind.SPEC or self.spec.parent_sha256 != self.models.sha256:
            raise ElementwiseSchemaError("Spec artifact is not bound to Models")
        _relative_path(self.proof_path, "proof path")
        if any(
            _IDENTIFIER_RE.fullmatch(value) is None
            for value in (self.module, self.theorem, self.claim)
        ):
            raise ElementwiseSchemaError("proof module/theorem/claim must be Lean identifiers")
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
            "claim": self.claim,
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
            "proof_path", "module", "theorem", "claim", "elaborated_type_sha256",
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
            claim=_text(data["claim"], "proof claim"),
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
    EXTERNAL_CONDITION_MISSING = "external-condition-missing"
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
    counterexample_sha256: str | None = None
    schema_version: int = RESULT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != RESULT_SCHEMA_VERSION:
            raise ElementwiseSchemaError("unsupported result schema version")
        _optional_digest(self.proof_task_sha256, "result proof-task digest")
        _optional_digest(self.proof_sha256, "result proof digest")
        _digest(self.checker_sha256, "result checker digest")
        _digest(self.toolchain_sha256, "result toolchain digest")
        _optional_digest(self.start_closure_sha256, "result start-closure digest")
        _optional_digest(self.end_closure_sha256, "result end-closure digest")
        _optional_digest(self.counterexample_sha256, "result counterexample digest")
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
        if self.status is ResultStatus.COUNTEREXAMPLE:
            if self.counterexample_sha256 is None:
                raise ElementwiseSchemaError(
                    "counterexample result needs a checked witness binding"
                )
            if self.proof_task_sha256 is not None or self.proof_sha256 is not None:
                raise ElementwiseSchemaError(
                    "counterexample result cannot claim an accepted proof"
                )
        elif self.counterexample_sha256 is not None:
            raise ElementwiseSchemaError(
                "only a counterexample result may bind a counterexample"
            )

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
            "counterexample_sha256": self.counterexample_sha256,
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
            "counterexample_sha256",
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
            counterexample_sha256=_optional_digest(
                data["counterexample_sha256"], "result counterexample digest"
            ),
        )
        if _digest(data["result_sha256"], "result digest") != result.sha256:
            raise ElementwiseSchemaError("result digest disagrees with contents")
        return result
