"""Restricted, typed translation of C ``assert`` conditions.

The parser is intentionally small and fail-closed.  It covers the side-effect-free
entry contracts and fixed-tail remainder facts in the audited elementwise corpus;
it is not a general C expression parser.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Mapping, Sequence

from .schema import (
    BOOL,
    SIZE_T,
    ContractExpr,
    ContractOp,
    ContractType,
    ContractTypeKind,
    ElementwiseSchemaError,
    EntryContract,
)


class ContractParseError(ElementwiseSchemaError):
    """An assertion is outside the supported side-effect-free grammar."""


_TOKEN = re.compile(
    r"\s*(?:(\|\||&&|==|!=|<=|>=)|([A-Za-z_][A-Za-z0-9_]*)|"
    r"(0[xX][0-9A-Fa-f]+|[0-9]+)|([()!+\-*/%<>]))"
)
_BINARY_PRECEDENCE = {
    "||": 1,
    "&&": 2,
    "==": 3,
    "!=": 3,
    "<": 4,
    "<=": 4,
    ">": 4,
    ">=": 4,
    "+": 5,
    "-": 5,
    "*": 6,
    "%": 6,
}
_OP = {
    "||": ContractOp.OR,
    "&&": ContractOp.AND,
    "==": ContractOp.EQ,
    "!=": ContractOp.NE,
    "<": ContractOp.LT,
    "<=": ContractOp.LE,
    ">": ContractOp.GT,
    ">=": ContractOp.GE,
    "+": ContractOp.ADD,
    "-": ContractOp.SUB,
    "*": ContractOp.MUL,
    "%": ContractOp.MOD,
}


@dataclass(frozen=True, slots=True)
class ParsedAssertion:
    source_text: str
    parent_control: str | None
    expression: ContractExpr


@dataclass(frozen=True, slots=True)
class _Raw:
    kind: str
    value: str | int | None = None
    args: tuple["_Raw", ...] = ()


def _tokens(text: str) -> tuple[str, ...]:
    result: list[str] = []
    position = 0
    while position < len(text):
        match = _TOKEN.match(text, position)
        if match is None:
            raise ContractParseError(
                f"unsupported contract token near {text[position:position + 24]!r}"
            )
        result.append(next(group for group in match.groups() if group is not None))
        position = match.end()
    return tuple(result)


class _Parser:
    def __init__(self, tokens: Sequence[str]) -> None:
        self.tokens = tokens
        self.position = 0

    def peek(self) -> str | None:
        return self.tokens[self.position] if self.position < len(self.tokens) else None

    def take(self, expected: str | None = None) -> str:
        token = self.peek()
        if token is None or (expected is not None and token != expected):
            raise ContractParseError(
                f"expected {expected or 'expression token'} at token {self.position}, got {token!r}"
            )
        self.position += 1
        return token

    def expression(self, minimum_precedence: int = 1) -> _Raw:
        left = self.prefix()
        while True:
            operator = self.peek()
            precedence = _BINARY_PRECEDENCE.get(operator or "")
            if precedence is None or precedence < minimum_precedence:
                break
            self.take()
            right = self.expression(precedence + 1)
            left = _Raw("binary", operator, (left, right))
        return left

    def prefix(self) -> _Raw:
        token = self.take()
        if token == "!":
            return _Raw("not", args=(self.prefix(),))
        if token == "(":
            result = self.expression()
            self.take(")")
            return result
        if token == "sizeof":
            self.take("(")
            depth = 1
            type_tokens: list[str] = []
            while depth:
                item = self.take()
                if item == "(":
                    depth += 1
                elif item == ")":
                    depth -= 1
                    if depth == 0:
                        break
                type_tokens.append(item)
            if not type_tokens or any(item not in {"*"} and not item.isidentifier() for item in type_tokens):
                raise ContractParseError("sizeof operand must be a type spelling")
            return _Raw("sizeof", _render_type_tokens(type_tokens))
        if token == "NULL":
            return _Raw("null", "NULL")
        if token.startswith(("0x", "0X")) or token.isdigit():
            return _Raw("integer", int(token, 0))
        if token.isidentifier():
            return _Raw("variable", token)
        raise ContractParseError(f"unsupported prefix token {token!r}")


def _render_type_tokens(tokens: Sequence[str]) -> str:
    result = " ".join(tokens)
    return result.replace(" *", "*")


def _condition_from_assertion(source_text: str) -> str:
    text = source_text.strip()
    match = re.match(r"assert\s*\(", text)
    if match is None:
        raise ContractParseError("contract source must be one assert(...) invocation")
    start = match.end()
    depth = 1
    index = start
    while index < len(text) and depth:
        if text[index] == "(":
            depth += 1
        elif text[index] == ")":
            depth -= 1
        index += 1
    if depth != 0 or text[index:].strip() != ";":
        raise ContractParseError("malformed or compound assert invocation")
    condition = text[start:index - 1].strip()
    if not condition:
        raise ContractParseError("assert condition must not be empty")
    return condition


def contract_type_from_c(type_spelling: str) -> ContractType:
    """Map a Clang C spelling to the pinned LP64 contract type universe."""

    normalized = re.sub(r"\s+", " ", type_spelling.strip())
    normalized = re.sub(r"\b(restrict|__restrict|__restrict__)\b", "", normalized)
    normalized = re.sub(r"\s+", " ", normalized).strip()
    if "*" in normalized:
        return ContractType(ContractTypeKind.POINTER, normalized, 64, None)
    scalar = normalized.replace("const ", "").strip()
    if scalar in {"size_t", "unsigned long", "unsigned long int"}:
        return SIZE_T
    if scalar in {"_Bool", "bool"}:
        return BOOL
    integer_types: dict[str, tuple[int, bool]] = {
        "char": (8, True),
        "signed char": (8, True),
        "int8_t": (8, True),
        "unsigned char": (8, False),
        "uint8_t": (8, False),
        "short": (16, True),
        "short int": (16, True),
        "signed short": (16, True),
        "int16_t": (16, True),
        "unsigned short": (16, False),
        "uint16_t": (16, False),
        "int": (32, True),
        "signed int": (32, True),
        "int32_t": (32, True),
        "unsigned": (32, False),
        "unsigned int": (32, False),
        "uint32_t": (32, False),
        "long": (64, True),
        "long int": (64, True),
        "signed long": (64, True),
        "int64_t": (64, True),
        "unsigned long long": (64, False),
        "uint64_t": (64, False),
    }
    properties = integer_types.get(scalar)
    if properties is None:
        raise ContractParseError(f"unsupported contract C type {type_spelling!r}")
    return ContractType(ContractTypeKind.INTEGER, scalar, properties[0], properties[1])


def _resolve_pair(
    left: _Raw,
    right: _Raw,
    variables: Mapping[str, ContractType],
) -> tuple[ContractExpr, ContractExpr]:
    if left.kind in {"integer", "null"} and right.kind not in {"integer", "null"}:
        resolved_right = _resolve(right, variables)
        return _resolve(left, variables, resolved_right.type), resolved_right
    resolved_left = _resolve(left, variables)
    return resolved_left, _resolve(right, variables, resolved_left.type)


def _resolve(
    raw: _Raw,
    variables: Mapping[str, ContractType],
    expected: ContractType | None = None,
) -> ContractExpr:
    if raw.kind == "variable":
        name = str(raw.value)
        value_type = variables.get(name)
        if value_type is None:
            raise ContractParseError(f"assertion references unknown variable {name!r}")
        if expected is not None and value_type != expected:
            raise ContractParseError(
                f"variable {name!r} has type {value_type.c_spelling}, expected {expected.c_spelling}"
            )
        return ContractExpr.variable(name, value_type)
    if raw.kind == "integer":
        value_type = expected or SIZE_T
        if value_type.kind is not ContractTypeKind.INTEGER:
            raise ContractParseError("integer literal used with a non-integer type")
        return ContractExpr.integer(int(raw.value), value_type)
    if raw.kind == "null":
        if expected is None or expected.kind is not ContractTypeKind.POINTER:
            raise ContractParseError("NULL must be compared with a known pointer type")
        return ContractExpr(ContractOp.NULL, expected, value="NULL")
    if raw.kind == "sizeof":
        if expected is not None and expected != SIZE_T:
            raise ContractParseError("sizeof value is incompatible with its context")
        return ContractExpr.sizeof(str(raw.value))
    if raw.kind == "not":
        argument = _resolve(raw.args[0], variables, BOOL)
        return ContractExpr.make(ContractOp.NOT, argument)
    if raw.kind != "binary" or len(raw.args) != 2:
        raise ContractParseError(f"unsupported parsed contract node {raw.kind!r}")
    operator = str(raw.value)
    op = _OP[operator]
    if op in {ContractOp.AND, ContractOp.OR}:
        left = _resolve(raw.args[0], variables, BOOL)
        right = _resolve(raw.args[1], variables, BOOL)
    else:
        left, right = _resolve_pair(raw.args[0], raw.args[1], variables)
    try:
        return ContractExpr.make(op, left, right)
    except ElementwiseSchemaError as error:
        raise ContractParseError(f"ill-typed contract operator {operator!r}: {error}") from error


def parse_assertion(
    source_text: str,
    *,
    variable_types: Mapping[str, ContractType],
    parent_control: str | None,
) -> ParsedAssertion:
    """Translate one assertion invocation into a normalized typed expression."""

    parser = _Parser(_tokens(_condition_from_assertion(source_text)))
    raw = parser.expression()
    if parser.peek() is not None:
        raise ContractParseError(f"trailing contract token {parser.peek()!r}")
    expression = _resolve(raw, variable_types, BOOL)
    return ParsedAssertion(source_text.strip(), parent_control, expression)


def assertion_types(parameters: Sequence[object]) -> dict[str, ContractType]:
    """Build the contract environment from frontend ``ParameterFact`` objects."""

    result: dict[str, ContractType] = {}
    for parameter in parameters:
        try:
            name = parameter.name
            type_spelling = parameter.type_spelling
        except AttributeError as error:
            raise ContractParseError("frontend parameter lacks name/type facts") from error
        if name in result:
            raise ContractParseError(f"duplicate assertion variable {name!r}")
        try:
            result[name] = contract_type_from_c(type_spelling)
        except ContractParseError:
            # Record-valued parameters are only usable through member reads in the
            # implementation, not as scalar assertion operands.  Pointer records
            # are handled by the pointer branch above.
            continue
    return result


def translate_assertions(
    assertions: Sequence[object],
    *,
    parameters: Sequence[object],
) -> tuple[EntryContract, tuple[ParsedAssertion, ...]]:
    """Split translated assertions into entry contract and local obligations."""

    variables = assertion_types(parameters)
    translated: list[ParsedAssertion] = []
    for assertion in assertions:
        try:
            source_text = assertion.source_text
            parent_control = assertion.parent_control
        except AttributeError as error:
            raise ContractParseError("frontend assertion lacks source/control facts") from error
        translated.append(
            parse_assertion(
                source_text,
                variable_types=variables,
                parent_control=parent_control,
            )
        )
    entry = EntryContract.normalized(
        tuple(item.expression for item in translated if item.parent_control is None)
    )
    local = tuple(item for item in translated if item.parent_control is not None)
    return entry, local

