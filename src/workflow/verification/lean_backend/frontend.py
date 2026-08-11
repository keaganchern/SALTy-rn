"""Restricted Clang-JSON frontend for the initial Neon-to-Lean slice.

This module deliberately does not interpret CVC5 terms and does not attempt to
parse C itself.  It asks the system Clang executable for a typed JSON AST, then
extracts exact intrinsic calls, syntactic variable dataflow, source ranges, and
structured control nodes for one explicitly reviewed kernel-side profile.

``DefinitionFact`` versions order definition statements and connect uses within
the extracted syntax.  They are not SSA/CFG semantics: this prototype does not
insert branch phi nodes or model loop back-edges.

The accepted language is intentionally small.  A reachable call, AST node,
operator, cast, or type outside the allowlist rejects the whole translation.
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import re
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Iterator, Sequence

from .profiles import FrontendAssertion, FrontendSideProfile, QS8_VADD_MINMAX


class FrontendError(RuntimeError):
    """Base class for deterministic, fail-closed frontend failures."""


class ClangError(FrontendError):
    """Clang was unavailable or rejected the translation unit."""


class UnsupportedConstructError(FrontendError):
    """The selected function contains syntax outside the supported subset."""


@dataclass(frozen=True)
class SourceRange:
    path: str
    begin_offset: int
    end_offset: int
    begin_line: int
    begin_column: int
    end_line: int
    end_column: int


@dataclass(frozen=True)
class ParameterFact:
    name: str
    type_spelling: str
    source: SourceRange


@dataclass(frozen=True)
class ArgumentFact:
    type_spelling: str
    dependencies: tuple[str, ...]
    source_text: str
    constant_value: int | str | None
    source: SourceRange
    semantic_operations: tuple[str, ...] = ()


@dataclass
class IntrinsicCall:
    node_id: str
    spelling: str
    callee_type: str
    result_type: str
    arguments: tuple[ArgumentFact, ...]
    dependencies: tuple[str, ...]
    assigned_to: str | None
    parent_control: str | None
    control_path: tuple[str, ...]
    source: SourceRange


@dataclass(frozen=True)
class DefinitionFact:
    node_id: str
    value: str
    variable: str
    version: int
    type_spelling: str
    definition_kind: str
    dependencies: tuple[str, ...]
    value_call: str | None
    expression_text: str
    parent_control: str | None
    control_path: tuple[str, ...]
    source: SourceRange


@dataclass(frozen=True)
class ControlFact:
    node_id: str
    kind: str
    parent_control: str | None
    condition_text: str
    condition_dependencies: tuple[str, ...]
    update_text: str
    source: SourceRange


@dataclass(frozen=True)
class KernelExtraction:
    schema_version: int
    source_path: str
    source_sha256: str
    facade_path: str
    facade_sha256: str
    clang_executable: str
    clang_version: str
    target_triple: str
    clang_command: tuple[str, ...]
    preprocess_command: tuple[str, ...]
    preprocessed_sha256: str
    function_name: str
    function_type: str
    dialect: str
    parameters: tuple[ParameterFact, ...]
    calls: tuple[IntrinsicCall, ...]
    definitions: tuple[DefinitionFact, ...]
    controls: tuple[ControlFact, ...]
    reachable_ast_nodes: int

    def to_dict(self) -> dict[str, Any]:
        return dataclasses.asdict(self)


# Backward-compatible alias used by the first emitter. New callers should use a
# profile's facade_path rather than importing this private name.
_FACADE = QS8_VADD_MINMAX.neon.facade_path

_ALLOWED_KINDS = {
    "BinaryOperator",
    "CStyleCastExpr",
    "CallExpr",
    "CompoundAssignOperator",
    "CompoundStmt",
    "DeclRefExpr",
    "DeclStmt",
    "DoStmt",
    "ForStmt",
    "IfStmt",
    "ImplicitCastExpr",
    "IntegerLiteral",
    "MemberExpr",
    "ParenExpr",
    "UnaryExprOrTypeTraitExpr",
    "UnaryOperator",
    "VarDecl",
    "WhileStmt",
}

_ALLOWED_BINARY_OPS = {"=", "!=", ">", ">=", "&", "*"}
_ALLOWED_COMPOUND_OPS = {"+=", "-="}
_ALLOWED_UNARY_OPS = {"-"}
_ALLOWED_CSTYLE_CASTS = {"BitCast", "IntegralCast", "ToVoid"}
_ALLOWED_IMPLICIT_CASTS = {
    "BitCast",
    "FunctionToPointerDecay",
    "IntegralCast",
    "LValueToRValue",
}
_FLOAT_TYPE_RE = re.compile(r"(^|[^A-Za-z0-9_])(float|double|_Float16)([^A-Za-z0-9_]|$)")
def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _strip_c_comments_preserving_lines(text: str) -> str:
    """Replace comments with spaces so comment-prefixed directives stay visible."""

    result: list[str] = []
    index = 0
    state = "normal"
    quote = ""
    while index < len(text):
        char = text[index]
        following = text[index + 1] if index + 1 < len(text) else ""
        if state == "block-comment":
            if char == "*" and following == "/":
                result.extend((" ", " "))
                index += 2
                state = "normal"
                continue
            result.append("\n" if char == "\n" else " ")
            index += 1
            continue
        if state == "line-comment":
            result.append("\n" if char == "\n" else " ")
            if char == "\n":
                state = "normal"
            index += 1
            continue
        if state == "quoted":
            result.append(char)
            if char == "\\" and following:
                result.append(following)
                index += 2
                continue
            if char == quote:
                state = "normal"
            index += 1
            continue
        if char == "/" and following == "*":
            result.extend((" ", " "))
            index += 2
            state = "block-comment"
            continue
        if char == "/" and following == "/":
            result.extend((" ", " "))
            index += 2
            state = "line-comment"
            continue
        result.append(char)
        if char in {'"', "'"}:
            state = "quoted"
            quote = char
        index += 1
    return "".join(result)


def _reject_source_preprocessor_directives(path: Path) -> None:
    try:
        text = path.read_bytes().decode("ascii")
    except UnicodeDecodeError as error:
        raise UnsupportedConstructError(
            f"non-ASCII source is outside this initial slice: {path}"
        ) from error
    phase_two = re.sub(r"\\[^\S\r\n]*\r?\n", "", text)
    stripped = _strip_c_comments_preserving_lines(phase_two)
    for line_number, line in enumerate(stripped.splitlines(), 1):
        if re.match(r"^\s*(?:#|%:|\?\?=)", line):
            raise UnsupportedConstructError(
                f"preprocessor directive at {path}:{line_number} is outside this slice"
            )


def _children(node: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        child
        for child in node.get("inner", [])
        if isinstance(child, dict) and child.get("kind")
    ]


def _walk(node: dict[str, Any]) -> Iterator[dict[str, Any]]:
    yield node
    for child in _children(node):
        yield from _walk(child)


def _unique(items: Iterable[str]) -> tuple[str, ...]:
    return tuple(dict.fromkeys(items))


class _Source:
    def __init__(self, path: Path) -> None:
        self.path = path.resolve()
        self.text = self.path.read_text(encoding="utf-8")
        self._line_starts = [0]
        for index, char in enumerate(self.text):
            if char == "\n":
                self._line_starts.append(index + 1)

    def line_column(self, offset: int) -> tuple[int, int]:
        import bisect

        clamped = max(0, min(offset, len(self.text)))
        line_index = bisect.bisect_right(self._line_starts, clamped) - 1
        return line_index + 1, clamped - self._line_starts[line_index] + 1

    @staticmethod
    def _location(raw: dict[str, Any], *, end: bool) -> dict[str, Any]:
        if "spellingLoc" in raw and "expansionLoc" in raw:
            expansion = raw["expansionLoc"]
            # Macro arguments have their real spelling in the kernel file.  For
            # tokens originating in a macro body, the expansion site is the only
            # kernel location worth recording.
            if expansion.get("isMacroArgExpansion"):
                return raw["spellingLoc"]
            return expansion
        return raw.get("expansionLoc") or raw.get("spellingLoc") or raw

    def source_range(self, node: dict[str, Any]) -> SourceRange:
        raw_range = node.get("range") or {}
        begin_raw = self._location(raw_range.get("begin") or node.get("loc") or {}, end=False)
        end_raw = self._location(raw_range.get("end") or node.get("loc") or {}, end=True)
        begin = int(begin_raw.get("offset", 0))
        end = int(end_raw.get("offset", begin)) + int(end_raw.get("tokLen", 0))
        begin = max(0, min(begin, len(self.text)))
        end = max(begin, min(end, len(self.text)))
        begin_line, begin_column = self.line_column(begin)
        end_line, end_column = self.line_column(end)
        return SourceRange(
            path=str(self.path),
            begin_offset=begin,
            end_offset=end,
            begin_line=begin_line,
            begin_column=begin_column,
            end_line=end_line,
            end_column=end_column,
        )

    def snippet(self, node: dict[str, Any]) -> str:
        source_range = self.source_range(node)
        return self.text[source_range.begin_offset:source_range.end_offset]


def _clang_ast(
    source: Path,
    facade: Path,
    clang: str,
    target_triple: str,
) -> tuple[dict[str, Any], tuple[str, ...], tuple[str, ...], str, str]:
    command = (
        clang,
        f"--target={target_triple}",
        "-x",
        "c",
        "-std=c11",
        "-fsyntax-only",
        "-Werror=implicit-function-declaration",
        "-Werror=trigraphs",
        "-Werror=backslash-newline-escape",
        "-include",
        str(facade),
        "-Xclang",
        "-ast-dump=json",
        str(source),
    )
    try:
        completed = subprocess.run(command, capture_output=True, text=True, check=False)
    except OSError as error:
        raise ClangError(f"could not execute Clang {clang!r}: {error}") from error
    if completed.returncode != 0:
        diagnostics = completed.stderr.strip() or "no diagnostics"
        raise ClangError(f"Clang rejected {source}:\n{diagnostics}")
    try:
        ast = json.loads(completed.stdout)
    except json.JSONDecodeError as error:
        raise ClangError(f"Clang produced invalid AST JSON for {source}: {error}") from error

    preprocess_command = (
        clang,
        f"--target={target_triple}",
        "-x",
        "c",
        "-std=c11",
        "-Werror=trigraphs",
        "-Werror=backslash-newline-escape",
        "-E",
        "-P",
        "-include",
        str(facade),
        str(source),
    )
    try:
        preprocessed = subprocess.run(
            preprocess_command, capture_output=True, check=False
        )
    except OSError as error:
        raise ClangError(f"could not preprocess with Clang {clang!r}: {error}") from error
    if preprocessed.returncode != 0:
        diagnostics = preprocessed.stderr.decode("utf-8", errors="replace").strip()
        raise ClangError(
            f"Clang could not preprocess {source}:\n{diagnostics or 'no diagnostics'}"
        )
    preprocessed_sha256 = hashlib.sha256(preprocessed.stdout).hexdigest()

    version = subprocess.run(
        (clang, "--version"), capture_output=True, text=True, check=False
    ).stdout.splitlines()
    return (
        ast,
        command,
        preprocess_command,
        version[0] if version else "unknown",
        preprocessed_sha256,
    )


def _find_function(
    ast: dict[str, Any], source: Path, function_name: str | None
) -> dict[str, Any]:
    candidates = []
    source_resolved = source.resolve()
    for node in _walk(ast):
        if node.get("kind") != "FunctionDecl" or not any(
            child.get("kind") == "CompoundStmt" for child in _children(node)
        ):
            continue
        location = node.get("loc", {})
        file_name = location.get("file")
        if file_name and Path(file_name).resolve() != source_resolved:
            continue
        if function_name is None or node.get("name") == function_name:
            candidates.append(node)
    if len(candidates) != 1:
        requested = f" named {function_name!r}" if function_name else ""
        raise FrontendError(
            f"expected exactly one function definition{requested} in {source}; "
            f"found {len(candidates)}"
        )
    return candidates[0]


def _type_spelling(node: dict[str, Any]) -> str:
    type_info = node.get("type") or {}
    return str(type_info.get("desugaredQualType") or type_info.get("qualType") or "")


def _function_reference(node: dict[str, Any]) -> dict[str, Any] | None:
    if (
        node.get("kind") != "ImplicitCastExpr"
        or node.get("castKind") != "FunctionToPointerDecay"
    ):
        return None
    children = _children(node)
    if len(children) != 1 or children[0].get("kind") != "DeclRefExpr":
        return None
    referenced = children[0].get("referencedDecl") or {}
    return referenced if referenced.get("kind") == "FunctionDecl" else None


def _member_path(node: dict[str, Any]) -> str | None:
    kind = node.get("kind")
    if kind == "MemberExpr":
        children = _children(node)
        if len(children) != 1:
            return None
        base = _member_path(children[0])
        return f"{base}.{node.get('name')}" if base else None
    if kind == "DeclRefExpr":
        referenced = node.get("referencedDecl") or {}
        if referenced.get("kind") in {"ParmVarDecl", "VarDecl"}:
            return str(referenced.get("name") or node.get("name"))
        return None
    if kind in {"ImplicitCastExpr", "CStyleCastExpr", "ParenExpr"}:
        children = _children(node)
        return _member_path(children[0]) if len(children) == 1 else None
    return None


def _validate_kernel_signature(
    function: dict[str, Any], profile: FrontendSideProfile
) -> None:
    function_name = str(function.get("name") or "")
    if function.get("mangledName") != function_name:
        raise UnsupportedConstructError(
            f"kernel linkage name changed from {function_name!r} to "
            f"{function.get('mangledName')!r}"
        )
    if function.get("previousDecl") is not None or function.get("storageClass") is not None:
        raise UnsupportedConstructError(
            "kernel redeclarations and explicit storage classes are outside this slice"
        )
    unexpected_children = [
        child.get("kind")
        for child in _children(function)
        if child.get("kind") not in {"ParmVarDecl", "CompoundStmt"}
    ]
    if unexpected_children:
        raise UnsupportedConstructError(
            f"unsupported kernel declaration attributes {unexpected_children!r}"
        )
    function_type = str((function.get("type") or {}).get("qualType") or "")
    if function_type != profile.function_type:
        raise UnsupportedConstructError(
            f"kernel signature changed from {profile.function_type!r} "
            f"to {function_type!r}"
        )
    parameters = tuple(
        (str(parameter.get("name")), _type_spelling(parameter))
        for parameter in _children(function)
        if parameter.get("kind") == "ParmVarDecl"
    )
    if parameters != profile.parameters:
        raise UnsupportedConstructError(
            f"kernel parameters changed from {profile.parameters!r} to {parameters!r}"
        )


def _direct_variable(node: dict[str, Any]) -> tuple[str, str] | None:
    current = node
    while current.get("kind") in {"ImplicitCastExpr", "CStyleCastExpr", "ParenExpr"}:
        children = _children(current)
        if len(children) != 1:
            return None
        current = children[0]
    if current.get("kind") != "DeclRefExpr":
        return None
    referenced = current.get("referencedDecl") or {}
    if referenced.get("kind") not in {"ParmVarDecl", "VarDecl"}:
        return None
    name = str(referenced.get("name") or current.get("name"))
    return name, _type_spelling(current)


def _constant_value(node: dict[str, Any], source_text: str) -> int | str | None:
    """Read the canonical integer value from the typed, macro-expanded AST."""

    current = node
    while current.get("kind") in {"ImplicitCastExpr", "CStyleCastExpr", "ParenExpr"}:
        children = _children(current)
        if len(children) != 1:
            return None
        current = children[0]
    if current.get("kind") == "UnaryOperator" and current.get("opcode") == "-":
        children = _children(current)
        if len(children) != 1:
            return None
        value = _constant_value(children[0], source_text.removeprefix("-").strip())
        return -value if isinstance(value, int) else None
    if current.get("kind") != "IntegerLiteral":
        return None
    try:
        return int(str(current.get("value")), 0)
    except (TypeError, ValueError):
        raise UnsupportedConstructError(
            f"Clang emitted a malformed integer literal value: {current.get('value')!r}"
        )


def _audit_function(
    function: dict[str, Any],
    allowed_calls: dict[str, int],
    expected_signatures: dict[str, str],
    declaration_ids: dict[str, str],
) -> int:
    body = next(child for child in _children(function) if child.get("kind") == "CompoundStmt")
    count = 0
    for node in _walk(body):
        count += 1
        kind = node.get("kind")
        if kind not in _ALLOWED_KINDS:
            raise UnsupportedConstructError(f"unsupported reachable AST kind {kind!r}")
        for type_field in (node.get("type"), node.get("argType")):
            if not isinstance(type_field, dict):
                continue
            for spelling in (
                type_field.get("qualType"),
                type_field.get("desugaredQualType"),
            ):
                if spelling and _FLOAT_TYPE_RE.search(str(spelling)):
                    raise UnsupportedConstructError(
                        f"floating type is outside this slice: {spelling}"
                    )
                if spelling and re.search(r"\bvolatile\b|_Atomic", str(spelling)):
                    raise UnsupportedConstructError(
                        f"volatile/atomic type is outside this slice: {spelling}"
                    )
        if kind == "BinaryOperator" and node.get("opcode") not in _ALLOWED_BINARY_OPS:
            raise UnsupportedConstructError(f"unsupported binary operator {node.get('opcode')!r}")
        if kind == "CompoundAssignOperator" and node.get("opcode") not in _ALLOWED_COMPOUND_OPS:
            raise UnsupportedConstructError(f"unsupported compound operator {node.get('opcode')!r}")
        if kind == "UnaryOperator" and node.get("opcode") not in _ALLOWED_UNARY_OPS:
            raise UnsupportedConstructError(f"unsupported unary operator {node.get('opcode')!r}")
        if kind == "UnaryExprOrTypeTraitExpr" and node.get("name") != "sizeof":
            raise UnsupportedConstructError(
                f"unsupported unary type trait {node.get('name')!r}"
            )
        if kind == "CStyleCastExpr" and node.get("castKind") not in _ALLOWED_CSTYLE_CASTS:
            raise UnsupportedConstructError(f"unsupported C cast {node.get('castKind')!r}")
        if kind == "ImplicitCastExpr" and node.get("castKind") not in _ALLOWED_IMPLICIT_CASTS:
            raise UnsupportedConstructError(f"unsupported implicit cast {node.get('castKind')!r}")
        if kind == "CallExpr":
            call_children = _children(node)
            referenced = _function_reference(call_children[0]) if call_children else None
            spelling = referenced.get("name") if referenced else None
            if not spelling or spelling not in allowed_calls:
                raise UnsupportedConstructError(f"unknown call spelling {spelling!r}")
            if referenced.get("id") != declaration_ids[spelling]:
                raise UnsupportedConstructError(
                    f"{spelling}: call does not resolve to the unique parse-facade declaration"
                )
            callee_type = str((referenced.get("type") or {}).get("qualType") or "")
            if callee_type != expected_signatures[spelling]:
                raise UnsupportedConstructError(
                    f"{spelling}: expected type {expected_signatures[spelling]!r}, "
                    f"got {callee_type!r}"
                )
            actual_arity = max(0, len(node.get("inner", [])) - 1)
            if actual_arity != allowed_calls[spelling]:
                raise UnsupportedConstructError(
                    f"{spelling}: expected {allowed_calls[spelling]} arguments, got {actual_arity}"
                )
    return count


def _facade_declaration_ids(
    ast: dict[str, Any], expected_signatures: dict[str, str]
) -> dict[str, str]:
    """Bind each registered spelling to one declaration supplied by the facade."""

    declarations: dict[str, list[dict[str, Any]]] = {
        spelling: [] for spelling in expected_signatures
    }
    for node in _walk(ast):
        if node.get("kind") != "FunctionDecl":
            continue
        spelling = node.get("name")
        if spelling in declarations:
            declarations[spelling].append(node)

    result: dict[str, str] = {}
    for spelling, candidates in declarations.items():
        if len(candidates) != 1:
            raise UnsupportedConstructError(
                f"{spelling}: expected one parse-facade declaration, found {len(candidates)}"
            )
        declaration = candidates[0]
        if any(child.get("kind") == "CompoundStmt" for child in _children(declaration)):
            raise UnsupportedConstructError(
                f"{spelling}: a source definition cannot replace intrinsic semantics"
            )
        callee_type = str((declaration.get("type") or {}).get("qualType") or "")
        if callee_type != expected_signatures[spelling]:
            raise UnsupportedConstructError(
                f"{spelling}: facade type changed from {expected_signatures[spelling]!r} "
                f"to {callee_type!r}"
            )
        if declaration.get("mangledName") != spelling:
            raise UnsupportedConstructError(
                f"{spelling}: external linkage name changed to "
                f"{declaration.get('mangledName')!r}"
            )
        unexpected_children = [
            child.get("kind")
            for child in _children(declaration)
            if child.get("kind") != "ParmVarDecl"
        ]
        if unexpected_children:
            raise UnsupportedConstructError(
                f"{spelling}: unsupported declaration attributes {unexpected_children!r}"
            )
        result[spelling] = str(declaration.get("id"))
    return result


@dataclass(frozen=True)
class _ExprValue:
    dependencies: tuple[str, ...] = ()
    root_call: str | None = None
    semantic_operations: tuple[str, ...] = ()


def _semantic_operation(node: dict[str, Any]) -> str | None:
    kind = node.get("kind")
    if kind == "ImplicitCastExpr":
        cast_kind = str(node.get("castKind") or "unknown")
        if cast_kind in {"LValueToRValue", "FunctionToPointerDecay"}:
            return None
        return f"implicit-cast:{cast_kind}:{_type_spelling(node)}"
    if kind == "CStyleCastExpr":
        return f"explicit-cast:{node.get('castKind') or 'unknown'}:{_type_spelling(node)}"
    if kind == "UnaryOperator":
        return f"unary:{node.get('opcode') or 'unknown'}"
    if kind == "BinaryOperator":
        return f"binary:{node.get('opcode') or 'unknown'}"
    return None


def _is_canonical_assert_noop(node: dict[str, Any]) -> bool:
    if node.get("kind") != "ParenExpr" or _type_spelling(node) != "void":
        return False
    children = _children(node)
    if len(children) != 1:
        return False
    cast = children[0]
    if (
        cast.get("kind") != "CStyleCastExpr"
        or cast.get("castKind") != "ToVoid"
        or _type_spelling(cast) != "void"
    ):
        return False
    cast_children = _children(cast)
    return (
        len(cast_children) == 1
        and cast_children[0].get("kind") == "IntegerLiteral"
        and _type_spelling(cast_children[0]) == "int"
        and str(cast_children[0].get("value")) == "0"
    )


class _Extractor:
    def __init__(
        self,
        source: _Source,
        function: dict[str, Any],
        allowed_calls: dict[str, int],
        expected_assertions: tuple[FrontendAssertion, ...],
        member_roots: frozenset[str],
    ) -> None:
        self.source = source
        self.function = function
        self.allowed_calls = allowed_calls
        self.expected_assertions = expected_assertions
        self.member_roots = member_roots
        self.calls: list[IntrinsicCall] = []
        self.definitions: list[DefinitionFact] = []
        self.controls: list[ControlFact] = []
        self._versions: dict[str, int] = {}
        self._current_values: dict[str, str] = {}
        self._call_by_id: dict[str, IntrinsicCall] = {}
        self._assertions: list[FrontendAssertion] = []
        self._control_path: list[str] = []

    def extract(self) -> tuple[
        tuple[ParameterFact, ...],
        tuple[IntrinsicCall, ...],
        tuple[DefinitionFact, ...],
        tuple[ControlFact, ...],
    ]:
        parameters = []
        for parameter in (
            child for child in _children(self.function) if child.get("kind") == "ParmVarDecl"
        ):
            name = str(parameter.get("name"))
            source_range = self.source.source_range(parameter)
            parameters.append(ParameterFact(name, _type_spelling(parameter), source_range))
            self._define(
                name,
                _type_spelling(parameter),
                "parameter",
                (),
                None,
                parameter,
                None,
            )

        body = next(
            child for child in _children(self.function) if child.get("kind") == "CompoundStmt"
        )
        self._statement(body, None)
        if tuple(self._assertions) != self.expected_assertions:
            raise UnsupportedConstructError(
                f"kernel assertions changed from {self.expected_assertions!r} "
                f"to {tuple(self._assertions)!r}"
            )
        return (
            tuple(parameters),
            tuple(self.calls),
            tuple(self.definitions),
            tuple(self.controls),
        )

    def _current(self, name: str) -> str:
        value = self._current_values.get(name)
        if value is None:
            raise UnsupportedConstructError(f"reference to untracked variable {name!r}")
        return value

    def _define(
        self,
        name: str,
        type_spelling: str,
        definition_kind: str,
        dependencies: Sequence[str],
        root_call: str | None,
        node: dict[str, Any],
        parent_control: str | None,
    ) -> str:
        version = self._versions.get(name, -1) + 1
        self._versions[name] = version
        value = f"{name}@{version}"
        self._current_values[name] = value
        definition_id = f"def_{len(self.definitions):04d}"
        self.definitions.append(
            DefinitionFact(
                node_id=definition_id,
                value=value,
                variable=name,
                version=version,
                type_spelling=type_spelling,
                definition_kind=definition_kind,
                dependencies=_unique(dependencies),
                value_call=root_call,
                expression_text=self.source.snippet(node),
                parent_control=parent_control,
                control_path=tuple(self._control_path),
                source=self.source.source_range(node),
            )
        )
        if root_call is not None:
            self._call_by_id[root_call].assigned_to = value
        return value

    def _expression(self, node: dict[str, Any], parent_control: str | None) -> _ExprValue:
        kind = node.get("kind")
        if kind == "CallExpr":
            return self._call(node, parent_control)
        if kind == "MemberExpr":
            path = _member_path(node)
            if not path or "." not in path:
                raise UnsupportedConstructError(f"unsupported member path {path!r}")
            base, members = path.split(".", 1)
            if base not in self.member_roots:
                raise UnsupportedConstructError(f"unsupported member path {path!r}")
            return _ExprValue((f"field:{self._current(base)}.{members}",))
        if kind == "DeclRefExpr":
            referenced = node.get("referencedDecl") or {}
            if referenced.get("kind") == "FunctionDecl":
                return _ExprValue()
            if referenced.get("kind") in {"ParmVarDecl", "VarDecl"}:
                name = str(referenced.get("name") or node.get("name"))
                return _ExprValue((self._current(name),))
            raise UnsupportedConstructError(
                f"unsupported declaration reference kind {referenced.get('kind')!r}"
            )
        if kind == "IntegerLiteral":
            return _ExprValue((f"constant:{node.get('value')}:{_type_spelling(node)}",))
        if kind == "UnaryExprOrTypeTraitExpr":
            arg_type = node.get("argType") or {}
            spelling = arg_type.get("qualType") or arg_type.get("desugaredQualType") or "?"
            return _ExprValue((f"sizeof:{spelling}",))

        dependencies: list[str] = []
        roots: list[str] = []
        semantic_operations: list[str] = []
        for child in _children(node):
            value = self._expression(child, parent_control)
            dependencies.extend(value.dependencies)
            semantic_operations.extend(value.semantic_operations)
            if value.root_call is not None:
                roots.append(value.root_call)
        operation = _semantic_operation(node)
        if operation is not None:
            semantic_operations.append(operation)
        root_call = (
            roots[0]
            if not semantic_operations and len(roots) == 1 and len(_children(node)) == 1
            else None
        )
        return _ExprValue(
            _unique(dependencies),
            root_call,
            tuple(semantic_operations),
        )

    def _call(self, node: dict[str, Any], parent_control: str | None) -> _ExprValue:
        raw_children = [child for child in node.get("inner", []) if isinstance(child, dict)]
        if not raw_children:
            raise UnsupportedConstructError("CallExpr has no callee")
        referenced = _function_reference(raw_children[0])
        if referenced is None:
            raise UnsupportedConstructError("indirect calls are outside this slice")
        spelling = str(referenced.get("name"))
        if spelling not in self.allowed_calls:
            raise UnsupportedConstructError(f"unknown call spelling {spelling!r}")

        arguments = []
        direct_dependencies: list[str] = []
        for argument in raw_children[1:]:
            value = self._expression(argument, parent_control)
            direct_dependencies.extend(value.dependencies)
            source_text = self.source.snippet(argument)
            arguments.append(
                ArgumentFact(
                    type_spelling=_type_spelling(argument),
                    dependencies=value.dependencies,
                    source_text=source_text,
                    constant_value=_constant_value(argument, source_text),
                    source=self.source.source_range(argument),
                    semantic_operations=value.semantic_operations,
                )
            )

        call_id = f"call_{len(self.calls):04d}"
        call = IntrinsicCall(
            node_id=call_id,
            spelling=spelling,
            callee_type=str((referenced.get("type") or {}).get("qualType") or ""),
            result_type=_type_spelling(node),
            arguments=tuple(arguments),
            dependencies=_unique(direct_dependencies),
            assigned_to=None,
            parent_control=parent_control,
            control_path=tuple(self._control_path),
            source=self.source.source_range(node),
        )
        self.calls.append(call)
        self._call_by_id[call_id] = call
        return _ExprValue((f"call:{call_id}",), call_id)

    def _condition(
        self, node: dict[str, Any] | None, parent_control: str | None
    ) -> tuple[str, tuple[str, ...]]:
        if node is None:
            return "", ()
        value = self._expression(node, parent_control)
        return self.source.snippet(node), value.dependencies

    def _new_control(
        self,
        node: dict[str, Any],
        parent_control: str | None,
        condition: dict[str, Any] | None,
        update: dict[str, Any] | None,
    ) -> str:
        control_id = f"control_{len(self.controls):04d}"
        condition_text, condition_dependencies = self._condition(condition, control_id)
        self.controls.append(
            ControlFact(
                node_id=control_id,
                kind=str(node.get("kind")),
                parent_control=parent_control,
                condition_text=condition_text,
                condition_dependencies=condition_dependencies,
                update_text=self.source.snippet(update) if update is not None else "",
                source=self.source.source_range(node),
            )
        )
        return control_id

    def _statement(self, node: dict[str, Any], parent_control: str | None) -> None:
        kind = node.get("kind")
        if kind == "CompoundStmt":
            for child in _children(node):
                self._statement(child, parent_control)
            return
        if kind == "DeclStmt":
            for child in _children(node):
                if child.get("kind") != "VarDecl":
                    raise UnsupportedConstructError("DeclStmt contains a non-variable declaration")
                self._declaration(child, parent_control)
            return
        if kind == "VarDecl":
            self._declaration(node, parent_control)
            return
        if kind == "CallExpr":
            self._expression(node, parent_control)
            return
        if kind == "BinaryOperator" and node.get("opcode") == "=":
            children = _children(node)
            if len(children) != 2:
                raise UnsupportedConstructError("assignment must have two operands")
            target = _direct_variable(children[0])
            if target is None:
                raise UnsupportedConstructError("only direct variable assignment is supported")
            value = self._expression(children[1], parent_control)
            self._define(
                target[0],
                target[1],
                "assignment",
                value.dependencies,
                value.root_call,
                node,
                parent_control,
            )
            return
        if kind == "CompoundAssignOperator":
            children = _children(node)
            if len(children) != 2:
                raise UnsupportedConstructError("compound assignment must have two operands")
            target = _direct_variable(children[0])
            if target is None:
                raise UnsupportedConstructError(
                    "only direct variable compound assignment is supported"
                )
            old_value = self._current(target[0])
            rhs = self._expression(children[1], parent_control)
            self._define(
                target[0],
                target[1],
                f"compound-{node.get('opcode')}",
                (old_value, *rhs.dependencies),
                None,
                node,
                parent_control,
            )
            return
        if kind == "ForStmt":
            raw = node.get("inner", [])
            meaningful = _children(node)
            condition = next(
                (child for child in meaningful if child.get("kind") == "BinaryOperator"), None
            )
            update = next(
                (child for child in meaningful if child.get("kind") == "CompoundAssignOperator"),
                None,
            )
            body = next(
                (child for child in meaningful if child.get("kind") == "CompoundStmt"), None
            )
            if len(raw) != 5 or condition is None or update is None or body is None:
                raise UnsupportedConstructError("unsupported ForStmt shape")
            control_id = self._new_control(node, parent_control, condition, update)
            self._statement(body, control_id)
            self._statement(update, control_id)
            return
        if kind == "WhileStmt":
            children = _children(node)
            if len(children) != 2 or children[1].get("kind") != "CompoundStmt":
                raise UnsupportedConstructError("unsupported WhileStmt shape")
            control_id = self._new_control(node, parent_control, children[0], None)
            self._statement(children[1], control_id)
            return
        if kind == "DoStmt":
            children = _children(node)
            if len(children) != 2 or children[0].get("kind") != "CompoundStmt":
                raise UnsupportedConstructError("unsupported DoStmt shape")
            control_id = self._new_control(node, parent_control, children[1], None)
            self._statement(children[0], control_id)
            return
        if kind == "IfStmt":
            children = _children(node)
            if len(children) not in {2, 3}:
                raise UnsupportedConstructError("unsupported IfStmt shape")
            control_id = self._new_control(node, parent_control, children[0], None)
            self._control_path.append(f"{control_id}:then")
            try:
                self._statement(children[1], control_id)
            finally:
                self._control_path.pop()
            if len(children) == 3:
                self._control_path.append(f"{control_id}:else")
                try:
                    self._statement(children[2], control_id)
                finally:
                    self._control_path.pop()
            return
        if (
            kind == "ParenExpr"
            and self.source.snippet(node).strip() == "assert"
        ):
            if not _is_canonical_assert_noop(node):
                raise UnsupportedConstructError(
                    "assert expansion differs from the pinned no-op facade macro"
                )
            source_range = self.source.source_range(node)
            line_end = self.source.text.find("\n", source_range.begin_offset)
            if line_end < 0:
                line_end = len(self.source.text)
            invocation = self.source.text[source_range.begin_offset:line_end]
            self._assertions.append(
                FrontendAssertion(
                    re.sub(r"\s+", "", invocation),
                    parent_control,
                )
            )
            self._expression(node, parent_control)
            return
        if kind in {
            "ParenExpr",
            "CStyleCastExpr",
            "ImplicitCastExpr",
            "UnaryOperator",
            "UnaryExprOrTypeTraitExpr",
            "BinaryOperator",
        }:
            raise UnsupportedConstructError(
                f"unsupported standalone expression statement {self.source.snippet(node)!r}"
            )
        raise UnsupportedConstructError(f"unsupported statement kind {kind!r}")

    def _declaration(self, node: dict[str, Any], parent_control: str | None) -> None:
        name = str(node.get("name"))
        children = _children(node)
        if len(children) > 1:
            raise UnsupportedConstructError(f"variable {name!r} has an unsupported initializer")
        value = self._expression(children[0], parent_control) if children else _ExprValue()
        self._define(
            name,
            _type_spelling(node),
            "declaration",
            value.dependencies,
            value.root_call,
            node,
            parent_control,
        )


def parse_kernel(
    path: str | Path,
    *,
    function_name: str | None = None,
    clang: str = "clang",
    facade: str | Path | None = None,
    profile: FrontendSideProfile | None = None,
) -> KernelExtraction:
    """Extract the supported typed body facts from one kernel translation unit.

    New kernels must pass an explicit architecture-side ``profile``. For backward
    compatibility, omitting it selects the ``qs8-vadd-minmax`` side from
    ``function_name`` or a ``source``/``target`` path component. ``facade`` and
    ``function_name`` remain overrides for focused mutation tests, but they do not
    alter the profile's target, signatures, or accepted calls.
    """

    source_path = Path(path).resolve()
    if not source_path.is_file():
        raise FrontendError(f"kernel source does not exist: {source_path}")

    if profile is None:
        if function_name == QS8_VADD_MINMAX.neon.function_name:
            profile = QS8_VADD_MINMAX.neon
        elif function_name == QS8_VADD_MINMAX.rvv.function_name:
            profile = QS8_VADD_MINMAX.rvv
        elif function_name is None:
            path_parts = set(source_path.parts)
            if "source" in path_parts:
                profile = QS8_VADD_MINMAX.neon
            elif "target" in path_parts:
                profile = QS8_VADD_MINMAX.rvv
        if profile is None:
            raise UnsupportedConstructError(
                "the default frontend profile requires test_neon/test_rvv or a "
                "source/target path; pass an explicit profile for another kernel"
            )

    selected_function_name = function_name or profile.function_name
    if selected_function_name != profile.function_name:
        raise UnsupportedConstructError(
            f"profile for {profile.function_name!r} cannot parse "
            f"{selected_function_name!r}"
        )
    facade_path = (
        Path(facade).resolve()
        if facade is not None
        else profile.facade_path.resolve()
    )
    if not facade_path.is_file():
        raise FrontendError(f"parse facade does not exist: {facade_path}")
    _reject_source_preprocessor_directives(source_path)

    ast, command, preprocess_command, clang_version, preprocessed_sha256 = _clang_ast(
        source_path, facade_path, clang, profile.target_triple
    )
    function = _find_function(ast, source_path, selected_function_name)
    _validate_kernel_signature(function, profile)
    selected_name = str(function.get("name"))
    if selected_name != profile.function_name:
        raise UnsupportedConstructError(
            f"profile expected function {profile.function_name!r}, got {selected_name!r}"
        )
    allowed_calls = profile.arities
    expected_signatures = profile.signatures

    declaration_ids = _facade_declaration_ids(ast, expected_signatures)
    reachable = _audit_function(
        function, allowed_calls, expected_signatures, declaration_ids
    )
    source = _Source(source_path)
    parameters, calls, definitions, controls = _Extractor(
        source,
        function,
        allowed_calls,
        profile.assertions,
        profile.member_roots,
    ).extract()

    return KernelExtraction(
        schema_version=2,
        source_path=str(source_path),
        source_sha256=_sha256(source_path),
        facade_path=str(facade_path),
        facade_sha256=_sha256(facade_path),
        clang_executable=clang,
        clang_version=clang_version,
        target_triple=profile.target_triple,
        clang_command=command,
        preprocess_command=preprocess_command,
        preprocessed_sha256=preprocessed_sha256,
        function_name=selected_name,
        function_type=_type_spelling(function),
        dialect=profile.architecture.value,
        parameters=parameters,
        calls=calls,
        definitions=definitions,
        controls=controls,
        reachable_ast_nodes=reachable,
    )


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("path", type=Path)
    parser.add_argument("--function")
    parser.add_argument("--clang", default="clang")
    parser.add_argument("--facade", type=Path)
    arguments = parser.parse_args(argv)
    result = parse_kernel(
        arguments.path,
        function_name=arguments.function,
        clang=arguments.clang,
        facade=arguments.facade,
    )
    print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
