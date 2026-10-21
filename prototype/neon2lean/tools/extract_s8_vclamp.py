#!/usr/bin/env python3
"""Fail-closed Clang AST audit for the current-main s8-vclamp pair.

The output is a provenance and coverage manifest, not a semantic model. Every
Clang AST node in each function body (apart from Clang's empty ForStmt slots) is
treated as semantic and must be accepted by a strict node handler. The extractor
then validates the complete expected Neon and RVV control/data-flow shapes.
"""

from __future__ import annotations

import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, Callable, Iterator


Node = dict[str, Any]
Check = Callable[[Node], None]


class ExtractError(RuntimeError):
    pass


SOURCE_CALLS = {
    "vdupq_n_s8",
    "vext_s8",
    "vget_low_s8",
    "vld1_s8",
    "vld1q_s8",
    "vmax_s8",
    "vmaxq_s8",
    "vmin_s8",
    "vminq_s8",
    "vreinterpret_u16_s8",
    "vreinterpret_u32_s8",
    "vst1_lane_s8",
    "vst1_lane_u16",
    "vst1_lane_u32",
    "vst1_s8",
    "vst1q_s8",
}

TARGET_CALLS = {
    "__riscv_vle8_v_i8m8",
    "__riscv_vmax_vx_i8m8",
    "__riscv_vmin_vx_i8m8",
    "__riscv_vse8_v_i8m8",
    "__riscv_vsetvl_e8m8",
}

COMMON_NODE_KINDS = {
    "BinaryOperator",
    "CallExpr",
    "CompoundAssignOperator",
    "CompoundStmt",
    "CStyleCastExpr",
    "DeclRefExpr",
    "DeclStmt",
    "ImplicitCastExpr",
    "IntegerLiteral",
    "MemberExpr",
    "ParenExpr",
    "UnaryExprOrTypeTraitExpr",
    "VarDecl",
}

ROLE_NODE_KINDS = {
    "source": COMMON_NODE_KINDS | {"ForStmt", "IfStmt"},
    "target": COMMON_NODE_KINDS | {"WhileStmt"},
}

ROLE_BINARY_OPS = {
    "source": {"!=", "%", "==", ">=", "=", "&"},
    "target": {"!=", "%", "==", ">", "="},
}

ROLE_CSTYLE_CASTS = {
    "source": {"BitCast", "NullToPointer", "ToVoid"},
    "target": {"IntegralCast", "NullToPointer", "ToVoid"},
}

IMPLICIT_CASTS = {
    "BitCast",
    "FunctionToPointerDecay",
    "IntegralCast",
    "LValueToRValue",
}

ALLOWED_TYPE_IDENTIFIERS = {
    "anon_struct",
    "char",
    "const",
    "int",
    "int8_t",
    "int8x8_t",
    "int8x16_t",
    "int32_t",
    "long",
    "restrict",
    "signed",
    "size_t",
    "struct",
    "uint16_t",
    "uint16x4_t",
    "uint32_t",
    "uint32x2_t",
    "unsigned",
    "vint8m8_t",
    "void",
    "xnn_s8_minmax_params",
}

FLOAT_TYPE_RE = re.compile(
    r"(?<![A-Za-z0-9_])(?:float|double|_Float[0-9]+|__fp16|half)(?![A-Za-z0-9_])",
    re.IGNORECASE,
)

EXPECTED_FUNCTION_QUALTYPE = (
    "void (size_t, const int8_t *, int8_t *, "
    "const struct xnn_s8_minmax_params *restrict)"
)

EXPECTED_PARAMETERS = (
    ("batch", "size_t"),
    ("input", "const int8_t *"),
    ("output", "int8_t *"),
    ("params", "const struct xnn_s8_minmax_params *restrict"),
)


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ExtractError(message)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def walk(node: Any) -> Iterator[Node]:
    if not isinstance(node, dict):
        return
    if node.get("kind"):
        yield node
    for child in node.get("inner", []):
        yield from walk(child)


def raw_placeholders(node: Any) -> Iterator[Node]:
    if not isinstance(node, dict):
        return
    if "kind" not in node and not node:
        yield node
    for child in node.get("inner", []):
        yield from raw_placeholders(child)


def children(node: Node) -> list[Node]:
    return [child for child in node.get("inner", []) if child.get("kind")]


def only_child(node: Node, context: str) -> Node:
    items = children(node)
    require(len(items) == 1, f"{context}: expected one child, got {len(items)}")
    return items[0]


def find_definition(ast: Node, name: str) -> Node:
    matches = [
        node
        for node in walk(ast)
        if node.get("kind") == "FunctionDecl"
        and node.get("name") == name
        and any(child.get("kind") == "CompoundStmt" for child in node.get("inner", []))
    ]
    require(len(matches) == 1, f"expected one definition of {name}, found {len(matches)}")
    return matches[0]


def function_body(function: Node) -> Node:
    bodies = [child for child in children(function) if child.get("kind") == "CompoundStmt"]
    require(len(bodies) == 1, "function must have exactly one CompoundStmt body")
    return bodies[0]


def function_name(call: Node) -> str:
    require(call.get("kind") == "CallExpr", "expected CallExpr")
    raw = call.get("inner", [])
    require(raw, "CallExpr has no callee")
    refs = [
        node
        for node in walk(raw[0])
        if node.get("kind") == "DeclRefExpr"
        and node.get("referencedDecl", {}).get("kind") == "FunctionDecl"
    ]
    require(len(refs) == 1, "CallExpr does not resolve to exactly one FunctionDecl")
    return str(refs[0]["referencedDecl"]["name"])


def call_args(call: Node) -> list[Node]:
    require(call.get("kind") == "CallExpr", "expected CallExpr")
    raw = call.get("inner", [])
    require(len(raw) >= 1, "CallExpr has no callee")
    return list(raw[1:])


def strip_expr(node: Node) -> Node:
    current = node
    while current.get("kind") in {"ParenExpr", "ImplicitCastExpr", "CStyleCastExpr"}:
        current = only_child(current, current.get("kind", "expression wrapper"))
    return current


def direct_ref(node: Node, expected: str, context: str) -> None:
    item = strip_expr(node)
    decl = item.get("referencedDecl", {})
    require(item.get("kind") == "DeclRefExpr", f"{context}: expected a direct reference")
    require(decl.get("kind") in {"ParmVarDecl", "VarDecl"}, f"{context}: not a value reference")
    require(decl.get("name") == expected, f"{context}: expected {expected}, got {decl.get('name')}")


def direct_int(node: Node, expected: int, context: str) -> None:
    item = strip_expr(node)
    require(item.get("kind") == "IntegerLiteral", f"{context}: expected IntegerLiteral")
    try:
        value = int(str(item.get("value")), 0)
    except ValueError as error:
        raise ExtractError(f"{context}: invalid integer literal {item.get('value')!r}") from error
    require(value == expected, f"{context}: expected {expected}, got {value}")


def member_path(node: Node, context: str) -> tuple[str, list[str]]:
    item = strip_expr(node)
    members: list[str] = []
    while item.get("kind") == "MemberExpr":
        members.append(str(item.get("name")))
        item = strip_expr(only_child(item, f"{context} member"))
    require(item.get("kind") == "DeclRefExpr", f"{context}: member base is not a reference")
    decl = item.get("referencedDecl", {})
    require(decl.get("kind") in {"ParmVarDecl", "VarDecl"}, f"{context}: invalid member base")
    return str(decl.get("name")), list(reversed(members))


def expect_member(node: Node, base: str, path: list[str], context: str) -> None:
    actual_base, actual_path = member_path(node, context)
    require(
        (actual_base, actual_path) == (base, path),
        f"{context}: expected {base}.{'.'.join(path)}, got {actual_base}.{'.'.join(actual_path)}",
    )


def expect_call(node: Node, name: str, checks: list[Check], context: str) -> Node:
    item = strip_expr(node)
    require(item.get("kind") == "CallExpr", f"{context}: expected call to {name}")
    actual = function_name(item)
    require(actual == name, f"{context}: expected call to {name}, got {actual}")
    args = call_args(item)
    require(len(args) == len(checks), f"{context}: {name} argument count changed")
    for check, argument in zip(checks, args, strict=True):
        check(argument)
    return item


def ref_check(name: str, context: str) -> Check:
    return lambda node: direct_ref(node, name, context)


def int_check(value: int, context: str) -> Check:
    return lambda node: direct_int(node, value, context)


def member_check(base: str, path: list[str], context: str) -> Check:
    return lambda node: expect_member(node, base, path, context)


def nested_call_check(name: str, checks: list[Check], context: str) -> Check:
    return lambda node: expect_call(node, name, checks, context)


def decl_var(statement: Node, name: str, qual_type: str, context: str) -> Node:
    require(statement.get("kind") == "DeclStmt", f"{context}: expected DeclStmt")
    variable = only_child(statement, context)
    require(variable.get("kind") == "VarDecl", f"{context}: declaration is not VarDecl")
    require(variable.get("name") == name, f"{context}: expected variable {name}")
    actual_type = variable.get("type", {}).get("qualType")
    require(actual_type == qual_type, f"{context}: expected type {qual_type}, got {actual_type}")
    return variable


def expect_decl_call(
    statement: Node,
    variable_name: str,
    qual_type: str,
    call_name: str,
    checks: list[Check],
    context: str,
) -> None:
    variable = decl_var(statement, variable_name, qual_type, context)
    initializer = only_child(variable, f"{context} initializer")
    expect_call(initializer, call_name, checks, context)


def assignment_parts(statement: Node, context: str) -> tuple[Node, Node]:
    require(
        statement.get("kind") == "BinaryOperator" and statement.get("opcode") == "=",
        f"{context}: expected assignment",
    )
    items = children(statement)
    require(len(items) == 2, f"{context}: assignment must have two operands")
    return items[0], items[1]


def expect_assignment_call(
    statement: Node, target: str, call_name: str, checks: list[Check], context: str
) -> None:
    lhs, rhs = assignment_parts(statement, context)
    direct_ref(lhs, target, f"{context} lhs")
    expect_call(rhs, call_name, checks, context)


def expect_update(
    statement: Node,
    opcode: str,
    target: str,
    rhs_check: Check,
    context: str,
) -> None:
    require(
        statement.get("kind") == "CompoundAssignOperator"
        and statement.get("opcode") == opcode,
        f"{context}: expected {target} {opcode} ...",
    )
    items = children(statement)
    require(len(items) == 2, f"{context}: update must have two operands")
    direct_ref(items[0], target, f"{context} lhs")
    rhs_check(items[1])


def expect_binary_ref_int(
    node: Node, opcode: str, lhs: str, rhs: int, context: str
) -> None:
    item = strip_expr(node)
    require(
        item.get("kind") == "BinaryOperator" and item.get("opcode") == opcode,
        f"{context}: expected {lhs} {opcode} {rhs}",
    )
    operands = children(item)
    require(len(operands) == 2, f"{context}: binary operator arity changed")
    direct_ref(operands[0], lhs, f"{context} lhs")
    direct_int(operands[1], rhs, f"{context} rhs")


def expr_text(node: Node) -> str:
    kind = node.get("kind")
    if kind in {"ParenExpr", "ImplicitCastExpr"}:
        return expr_text(only_child(node, kind))
    if kind == "CStyleCastExpr":
        if node.get("castKind") == "NullToPointer":
            return "NULL"
        return expr_text(only_child(node, kind))
    if kind == "DeclRefExpr":
        return str(node.get("referencedDecl", {}).get("name"))
    if kind == "IntegerLiteral":
        return str(int(str(node.get("value")), 0))
    if kind == "UnaryExprOrTypeTraitExpr" and node.get("name") == "sizeof":
        return f"sizeof({node.get('argType', {}).get('qualType')})"
    if kind == "BinaryOperator":
        operands = children(node)
        require(len(operands) == 2, "expression renderer: binary arity changed")
        return f"({expr_text(operands[0])} {node.get('opcode')} {expr_text(operands[1])})"
    raise ExtractError(f"cannot normalize assertion node {kind}")


def expect_assertions(statements: list[Node], context: str) -> list[str]:
    require(len(statements) >= 4, f"{context}: missing entry assertions")
    rendered = [expr_text(node) for node in statements[:4]]
    expected = [
        "(batch != 0)",
        "((batch % sizeof(int8_t)) == 0)",
        "(input != NULL)",
        "(output != NULL)",
    ]
    require(rendered == expected, f"{context}: entry assertions changed: {rendered}")
    return rendered


def call_counter(node: Node) -> Counter[str]:
    return Counter(
        function_name(item) for item in walk(node) if item.get("kind") == "CallExpr"
    )


def expect_call_counts(node: Node, expected: dict[str, int], context: str) -> None:
    actual = call_counter(node)
    require(actual == Counter(expected), f"{context}: intrinsic multiset changed: {dict(actual)}")


def expect_for(loop: Node, amount: int, context: str) -> Node:
    require(loop.get("kind") == "ForStmt", f"{context}: expected ForStmt")
    raw = loop.get("inner", [])
    require(len(raw) == 5, f"{context}: expected five Clang ForStmt slots")
    require(not raw[0] and not raw[1], f"{context}: loop initializer/condition-variable changed")
    expect_binary_ref_int(raw[2], ">=", "batch", amount, f"{context} guard")
    expect_update(
        raw[3], "-=", "batch", int_check(amount, f"{context} decrement"), f"{context} update"
    )
    require(raw[4].get("kind") == "CompoundStmt", f"{context}: loop body changed")
    return raw[4]


def validate_neon_main_loop(loop: Node) -> dict[str, Any]:
    body = expect_for(loop, 64, "Neon 64-byte loop")
    statements = children(body)
    expected_kinds = (
        ["DeclStmt", "CompoundAssignOperator"] * 4
        + ["BinaryOperator"] * 8
        + ["CallExpr", "CompoundAssignOperator"] * 4
    )
    require(
        [node.get("kind") for node in statements] == expected_kinds,
        "Neon 64-byte loop statement schedule changed",
    )
    for index in range(4):
        name = f"vacc{index}"
        expect_decl_call(
            statements[index * 2],
            name,
            "int8x16_t",
            "vld1q_s8",
            [ref_check("input", f"{name} load")],
            f"Neon {name} load",
        )
        expect_update(
            statements[index * 2 + 1],
            "+=",
            "input",
            int_check(16, f"{name} input advance"),
            f"Neon {name} input advance",
        )
        expect_assignment_call(
            statements[8 + index],
            name,
            "vmaxq_s8",
            [ref_check(name, f"{name} max value"), ref_check("voutput_min", f"{name} min")],
            f"Neon {name} max",
        )
        expect_assignment_call(
            statements[12 + index],
            name,
            "vminq_s8",
            [ref_check(name, f"{name} min value"), ref_check("voutput_max", f"{name} max")],
            f"Neon {name} min",
        )
        expect_call(
            statements[16 + index * 2],
            "vst1q_s8",
            [ref_check("output", f"{name} store output"), ref_check(name, f"{name} store value")],
            f"Neon {name} store",
        )
        expect_update(
            statements[17 + index * 2],
            "+=",
            "output",
            int_check(16, f"{name} output advance"),
            f"Neon {name} output advance",
        )
    expected_calls = {"vld1q_s8": 4, "vmaxq_s8": 4, "vminq_s8": 4, "vst1q_s8": 4}
    expect_call_counts(body, expected_calls, "Neon 64-byte loop")
    return {
        "kind": "ForStmt",
        "guard": "batch >= 64",
        "batch_decrement": 64,
        "input_advance": 64,
        "output_advance": 64,
        "intrinsic_counts": dict(sorted(expected_calls.items())),
    }


def validate_neon_eight_loop(loop: Node) -> dict[str, Any]:
    body = expect_for(loop, 8, "Neon 8-byte loop")
    statements = children(body)
    require(
        [node.get("kind") for node in statements]
        == [
            "DeclStmt",
            "CompoundAssignOperator",
            "BinaryOperator",
            "BinaryOperator",
            "CallExpr",
            "CompoundAssignOperator",
        ],
        "Neon 8-byte loop statement schedule changed",
    )
    expect_decl_call(
        statements[0],
        "vacc",
        "int8x8_t",
        "vld1_s8",
        [ref_check("input", "8-byte load")],
        "Neon 8-byte load",
    )
    expect_update(
        statements[1], "+=", "input", int_check(8, "8-byte input advance"), "8-byte input"
    )
    expect_assignment_call(
        statements[2],
        "vacc",
        "vmin_s8",
        [
            ref_check("vacc", "8-byte min value"),
            nested_call_check(
                "vget_low_s8",
                [ref_check("voutput_max", "8-byte low max")],
                "8-byte low max",
            ),
        ],
        "Neon 8-byte min",
    )
    expect_assignment_call(
        statements[3],
        "vacc",
        "vmax_s8",
        [
            ref_check("vacc", "8-byte max value"),
            nested_call_check(
                "vget_low_s8",
                [ref_check("voutput_min", "8-byte low min")],
                "8-byte low min",
            ),
        ],
        "Neon 8-byte max",
    )
    expect_call(
        statements[4],
        "vst1_s8",
        [ref_check("output", "8-byte store output"), ref_check("vacc", "8-byte store value")],
        "Neon 8-byte store",
    )
    expect_update(
        statements[5], "+=", "output", int_check(8, "8-byte output advance"), "8-byte output"
    )
    expected_calls = {
        "vget_low_s8": 2,
        "vld1_s8": 1,
        "vmax_s8": 1,
        "vmin_s8": 1,
        "vst1_s8": 1,
    }
    expect_call_counts(body, expected_calls, "Neon 8-byte loop")
    return {
        "kind": "ForStmt",
        "guard": "batch >= 8",
        "batch_decrement": 8,
        "input_advance": 8,
        "output_advance": 8,
        "intrinsic_counts": dict(sorted(expected_calls.items())),
    }


def validate_tail_lane(
    node: Node,
    mask: int,
    store: str,
    reinterpret: str | None,
    advance: int | None,
) -> None:
    context = f"Neon tail mask {mask}"
    require(node.get("kind") == "IfStmt", f"{context}: expected IfStmt")
    parts = children(node)
    require(len(parts) == 2, f"{context}: expected condition and body")
    condition = parts[0]
    require(
        condition.get("kind") == "BinaryOperator" and condition.get("opcode") == "&",
        f"{context}: mask condition changed",
    )
    operands = children(condition)
    require(len(operands) == 2, f"{context}: mask arity changed")
    direct_ref(operands[0], "batch", f"{context} batch")
    direct_int(operands[1], mask, f"{context} bit")
    body = parts[1]
    require(body.get("kind") == "CompoundStmt", f"{context}: body changed")
    statements = children(body)
    expected_kinds = ["CallExpr"] if advance is None else [
        "CallExpr",
        "CompoundAssignOperator",
        "BinaryOperator",
    ]
    require(
        [item.get("kind") for item in statements] == expected_kinds,
        f"{context}: statement schedule changed",
    )
    value_check: Check
    if reinterpret is None:
        value_check = ref_check("vacc", f"{context} store value")
    else:
        value_check = nested_call_check(
            reinterpret,
            [ref_check("vacc", f"{context} reinterpret value")],
            f"{context} reinterpret",
        )
    expect_call(
        statements[0],
        store,
        [
            ref_check("output", f"{context} store output"),
            value_check,
            int_check(0, f"{context} lane"),
        ],
        f"{context} store",
    )
    if advance is not None:
        expect_update(
            statements[1],
            "+=",
            "output",
            int_check(advance, f"{context} output advance"),
            f"{context} output",
        )
        expect_assignment_call(
            statements[2],
            "vacc",
            "vext_s8",
            [
                ref_check("vacc", f"{context} ext lhs"),
                ref_check("vacc", f"{context} ext rhs"),
                int_check(advance, f"{context} ext amount"),
            ],
            f"{context} ext",
        )


def validate_neon_tail(tail: Node) -> dict[str, Any]:
    require(tail.get("kind") == "IfStmt", "Neon tail must be IfStmt")
    parts = children(tail)
    require(len(parts) == 2, "Neon tail must have condition and body")
    expect_binary_ref_int(parts[0], "!=", "batch", 0, "Neon tail guard")
    body = parts[1]
    require(body.get("kind") == "CompoundStmt", "Neon tail body changed")
    statements = children(body)
    require(
        [node.get("kind") for node in statements]
        == [
            "DeclStmt",
            "CompoundAssignOperator",
            "BinaryOperator",
            "BinaryOperator",
            "IfStmt",
            "IfStmt",
            "IfStmt",
        ],
        "Neon tail statement schedule changed",
    )
    expect_decl_call(
        statements[0],
        "vacc",
        "int8x8_t",
        "vld1_s8",
        [ref_check("input", "tail load")],
        "Neon tail load",
    )
    expect_update(
        statements[1], "+=", "input", int_check(8, "tail input advance"), "tail input"
    )
    expect_assignment_call(
        statements[2],
        "vacc",
        "vmin_s8",
        [
            ref_check("vacc", "tail min value"),
            nested_call_check(
                "vget_low_s8",
                [ref_check("voutput_max", "tail low max")],
                "tail low max",
            ),
        ],
        "Neon tail min",
    )
    expect_assignment_call(
        statements[3],
        "vacc",
        "vmax_s8",
        [
            ref_check("vacc", "tail max value"),
            nested_call_check(
                "vget_low_s8",
                [ref_check("voutput_min", "tail low min")],
                "tail low min",
            ),
        ],
        "Neon tail max",
    )
    validate_tail_lane(statements[4], 4, "vst1_lane_u32", "vreinterpret_u32_s8", 4)
    validate_tail_lane(statements[5], 2, "vst1_lane_u16", "vreinterpret_u16_s8", 2)
    validate_tail_lane(statements[6], 1, "vst1_lane_s8", None, None)
    expected_calls = {
        "vext_s8": 2,
        "vget_low_s8": 2,
        "vld1_s8": 1,
        "vmax_s8": 1,
        "vmin_s8": 1,
        "vreinterpret_u16_s8": 1,
        "vreinterpret_u32_s8": 1,
        "vst1_lane_s8": 1,
        "vst1_lane_u16": 1,
        "vst1_lane_u32": 1,
    }
    expect_call_counts(body, expected_calls, "Neon tail")
    return {
        "kind": "IfStmt",
        "guard": "batch != 0",
        "oob_load_width": 8,
        "partial_store_masks": [4, 2, 1],
        "maximum_written_bytes": 7,
        "intrinsic_counts": dict(sorted(expected_calls.items())),
    }


def validate_source(function: Node, body: Node) -> dict[str, Any]:
    statements = children(body)
    require(
        [node.get("kind") for node in statements]
        == ["ParenExpr"] * 4 + ["DeclStmt", "DeclStmt", "ForStmt", "ForStmt", "IfStmt"],
        "Neon top-level statement schedule changed",
    )
    assertions = expect_assertions(statements, "Neon")
    expect_decl_call(
        statements[4],
        "voutput_max",
        "const int8x16_t",
        "vdupq_n_s8",
        [member_check("params", ["scalar", "max"], "Neon max parameter")],
        "Neon max splat",
    )
    expect_decl_call(
        statements[5],
        "voutput_min",
        "const int8x16_t",
        "vdupq_n_s8",
        [member_check("params", ["scalar", "min"], "Neon min parameter")],
        "Neon min splat",
    )
    return {
        "entry_assertions": assertions,
        "top_level_statement_kinds": [node.get("kind") for node in statements],
        "loops": [
            validate_neon_main_loop(statements[6]),
            validate_neon_eight_loop(statements[7]),
        ],
        "tail": validate_neon_tail(statements[8]),
    }


def validate_target(function: Node, body: Node) -> dict[str, Any]:
    statements = children(body)
    require(
        [node.get("kind") for node in statements]
        == ["ParenExpr"] * 4 + ["DeclStmt", "DeclStmt", "WhileStmt"],
        "RVV top-level statement schedule changed",
    )
    assertions = expect_assertions(statements, "RVV")
    for index, name in enumerate(("min", "max"), start=4):
        variable = decl_var(statements[index], name, "const int8_t", f"RVV {name} parameter")
        initializer = only_child(variable, f"RVV {name} initializer")
        require(
            initializer.get("kind") == "CStyleCastExpr"
            and initializer.get("castKind") == "IntegralCast"
            and initializer.get("type", {}).get("qualType") == "int8_t",
            f"RVV {name}: explicit int8_t cast changed",
        )
        value_read = only_child(initializer, f"RVV {name} int8_t cast")
        require(
            value_read.get("kind") == "ImplicitCastExpr"
            and value_read.get("castKind") == "LValueToRValue"
            and value_read.get("type", {}).get("qualType") == "int32_t",
            f"RVV {name}: expected direct int32_t lvalue read under int8_t cast",
        )
        member = only_child(value_read, f"RVV {name} lvalue read")
        require(member.get("kind") == "MemberExpr", f"RVV {name}: nested cast is forbidden")
        expect_member(member, "params", ["scalar", name], f"RVV {name} member")

    loop = statements[6]
    require(loop.get("kind") == "WhileStmt", "RVV loop must be WhileStmt")
    parts = children(loop)
    require(len(parts) == 2, "RVV while must have condition and body")
    expect_binary_ref_int(parts[0], ">", "batch", 0, "RVV while guard")
    loop_body = parts[1]
    require(loop_body.get("kind") == "CompoundStmt", "RVV while body changed")
    loop_statements = children(loop_body)
    require(
        [node.get("kind") for node in loop_statements]
        == [
            "DeclStmt",
            "DeclStmt",
            "BinaryOperator",
            "BinaryOperator",
            "CallExpr",
            "CompoundAssignOperator",
            "CompoundAssignOperator",
            "CompoundAssignOperator",
        ],
        "RVV while statement schedule changed",
    )
    expect_decl_call(
        loop_statements[0],
        "vl",
        "size_t",
        "__riscv_vsetvl_e8m8",
        [ref_check("batch", "RVV vsetvl AVL")],
        "RVV vsetvl",
    )
    expect_decl_call(
        loop_statements[1],
        "vacc",
        "vint8m8_t",
        "__riscv_vle8_v_i8m8",
        [ref_check("input", "RVV load input"), ref_check("vl", "RVV load vl")],
        "RVV load",
    )
    expect_assignment_call(
        loop_statements[2],
        "vacc",
        "__riscv_vmax_vx_i8m8",
        [
            ref_check("vacc", "RVV max value"),
            ref_check("min", "RVV max scalar"),
            ref_check("vl", "RVV max vl"),
        ],
        "RVV max",
    )
    expect_assignment_call(
        loop_statements[3],
        "vacc",
        "__riscv_vmin_vx_i8m8",
        [
            ref_check("vacc", "RVV min value"),
            ref_check("max", "RVV min scalar"),
            ref_check("vl", "RVV min vl"),
        ],
        "RVV min",
    )
    expect_call(
        loop_statements[4],
        "__riscv_vse8_v_i8m8",
        [
            ref_check("output", "RVV store output"),
            ref_check("vacc", "RVV store value"),
            ref_check("vl", "RVV store vl"),
        ],
        "RVV store",
    )
    expect_update(
        loop_statements[5], "+=", "input", ref_check("vl", "RVV input vl"), "RVV input"
    )
    expect_update(
        loop_statements[6], "+=", "output", ref_check("vl", "RVV output vl"), "RVV output"
    )
    expect_update(
        loop_statements[7], "-=", "batch", ref_check("vl", "RVV batch vl"), "RVV batch"
    )
    expected_calls = {
        "__riscv_vle8_v_i8m8": 1,
        "__riscv_vmax_vx_i8m8": 1,
        "__riscv_vmin_vx_i8m8": 1,
        "__riscv_vse8_v_i8m8": 1,
        "__riscv_vsetvl_e8m8": 1,
    }
    expect_call_counts(loop_body, expected_calls, "RVV while")
    return {
        "entry_assertions": assertions,
        "top_level_statement_kinds": [node.get("kind") for node in statements],
        "loop": {
            "kind": "WhileStmt",
            "guard": "batch > 0",
            "vl": "__riscv_vsetvl_e8m8(batch)",
            "input_advance": "vl",
            "output_advance": "vl",
            "batch_decrement": "vl",
            "intrinsic_counts": dict(sorted(expected_calls.items())),
        },
    }


def iter_type_strings(node: Node) -> Iterator[tuple[str, str]]:
    for field in ("type", "argType"):
        value = node.get(field)
        if not isinstance(value, dict):
            continue
        for type_field in ("qualType", "desugaredQualType"):
            type_text = value.get(type_field)
            if isinstance(type_text, str):
                yield f"{field}.{type_field}", type_text


def validate_type(type_text: str, context: str) -> None:
    require(not FLOAT_TYPE_RE.search(type_text), f"{context}: reachable floating type {type_text!r}")
    normalized = re.sub(
        r"\(unnamed(?: struct)? at [^)]+\)", "anon_struct", type_text
    )
    identifiers = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", normalized))
    unknown = identifiers - ALLOWED_TYPE_IDENTIFIERS
    require(not unknown, f"{context}: unsupported type identifiers {sorted(unknown)} in {type_text!r}")


def audit_node(node: Node, role: str, allowed_calls: set[str]) -> None:
    kind = str(node.get("kind"))
    require(kind in ROLE_NODE_KINDS[role], f"{role}: unsupported reachable AST kind {kind}")
    for field, type_text in iter_type_strings(node):
        validate_type(type_text, f"{role} {kind} {field}")

    if kind == "FloatingLiteral":
        raise ExtractError(f"{role}: reachable floating literal")
    if kind == "CallExpr":
        name = function_name(node)
        require(name in allowed_calls, f"{role}: unsupported call spelling {name!r}")
    elif kind == "BinaryOperator":
        require(node.get("opcode") in ROLE_BINARY_OPS[role], f"{role}: unsupported binary opcode {node.get('opcode')!r}")
        require(len(children(node)) == 2, f"{role}: BinaryOperator arity changed")
    elif kind == "CompoundAssignOperator":
        require(node.get("opcode") in {"+=", "-="}, f"{role}: unsupported update opcode {node.get('opcode')!r}")
        require(len(children(node)) == 2, f"{role}: CompoundAssignOperator arity changed")
    elif kind == "CStyleCastExpr":
        require(node.get("castKind") in ROLE_CSTYLE_CASTS[role], f"{role}: unsupported C cast {node.get('castKind')!r}")
        only_child(node, f"{role} CStyleCastExpr")
    elif kind == "ImplicitCastExpr":
        require(node.get("castKind") in IMPLICIT_CASTS, f"{role}: unsupported implicit cast {node.get('castKind')!r}")
        only_child(node, f"{role} ImplicitCastExpr")
    elif kind == "ParenExpr":
        only_child(node, f"{role} ParenExpr")
    elif kind == "DeclStmt":
        child = only_child(node, f"{role} DeclStmt")
        require(child.get("kind") == "VarDecl", f"{role}: DeclStmt is not a single VarDecl")
    elif kind == "DeclRefExpr":
        decl_kind = node.get("referencedDecl", {}).get("kind")
        require(decl_kind in {"FunctionDecl", "ParmVarDecl", "VarDecl"}, f"{role}: unsupported reference kind {decl_kind!r}")
    elif kind == "MemberExpr":
        require(node.get("name") in {"scalar", "min", "max"}, f"{role}: unsupported member {node.get('name')!r}")
        only_child(node, f"{role} MemberExpr")
    elif kind == "IntegerLiteral":
        try:
            int(str(node.get("value")), 0)
        except ValueError as error:
            raise ExtractError(f"{role}: malformed integer literal {node.get('value')!r}") from error
    elif kind == "UnaryExprOrTypeTraitExpr":
        require(node.get("name") == "sizeof", f"{role}: unsupported unary/type trait {node.get('name')!r}")
        require(node.get("argType", {}).get("qualType") == "int8_t", f"{role}: unsupported sizeof type")
    elif kind == "ForStmt":
        require(role == "source", "target: ForStmt is unsupported")
    elif kind == "IfStmt":
        require(role == "source", "target: IfStmt is unsupported")
        require(len(children(node)) == 2, "source: IfStmt with else or declaration is unsupported")
    elif kind == "WhileStmt":
        require(role == "target", "source: WhileStmt is unsupported")
        require(len(children(node)) == 2, "target: WhileStmt shape changed")


def audit_coverage(
    function: Node,
    body: Node,
    role: str,
    allowed_calls: set[str],
    data: bytes,
    display_path: str,
) -> dict[str, Any]:
    for node in walk(function):
        if node.get("kind") == "FloatingLiteral":
            raise ExtractError(f"{role}: reachable floating literal")
        for field, type_text in iter_type_strings(node):
            require(
                not FLOAT_TYPE_RE.search(type_text),
                f"{role} {node.get('kind')} {field}: reachable floating type {type_text!r}",
            )

    semantic_nodes = list(walk(body))
    consumed: list[Node] = []
    for node in semantic_nodes:
        audit_node(node, role, allowed_calls)
        consumed.append(node)
    require(len(consumed) == len(semantic_nodes), f"{role}: coverage is not complete")
    total = len(semantic_nodes)
    consumed_total = len(consumed)
    kind_counts = Counter(str(node.get("kind")) for node in semantic_nodes)
    consumed_counts = Counter(str(node.get("kind")) for node in consumed)
    entries = []
    for node_id, node in enumerate(consumed):
        node_range = source_range(node, data, f"{role} coverage node {node_id}")
        entries.append(
            {
                "ast_node_id": node_id,
                "kind": str(node.get("kind")),
                "source": {
                    "path": display_path,
                    "begin_offset": node_range["begin"]["offset"],
                    "end_offset": node_range["end_exclusive"]["offset"],
                },
                "disposition": {
                    "kind": "justified_exclusion",
                    "rule_id": "AST_AUDIT_ONLY",
                    "reason": "strictly audited; semantic KernelIR lowering is not implemented yet",
                },
            }
        )
    return {
        "scope": "function CompoundStmt body and every descendant with a nonempty Clang AST kind",
        "semantic_node_definition": (
            "Every node in scope is semantic. A node is consumed only after its kind, type, "
            "and applicable call/operator/cast discriminator pass the strict handler."
        ),
        "excluded_empty_for_slots": sum(1 for _ in raw_placeholders(body)),
        "semantic_nodes": total,
        "consumed_semantic_nodes": consumed_total,
        "coverage_percent": 100.0 if total == consumed_total else 0.0,
        "kind_counts": dict(sorted(kind_counts.items())),
        "consumed_kind_counts": dict(sorted(consumed_counts.items())),
        "accepted_node_kinds": sorted(ROLE_NODE_KINDS[role]),
        "entries": entries,
    }


def line_column(data: bytes, offset: int) -> tuple[int, int]:
    require(0 <= offset <= len(data), f"source offset {offset} is out of bounds")
    line = data.count(b"\n", 0, offset) + 1
    last_newline = data.rfind(b"\n", 0, offset)
    column = offset + 1 if last_newline < 0 else offset - last_newline
    return line, column


def offset_record(data: bytes, offset: int) -> dict[str, int]:
    line, column = line_column(data, offset)
    return {"offset": offset, "line": line, "column": column}


def direct_location(location: Node) -> Node:
    if "expansionLoc" in location:
        return direct_location(location["expansionLoc"])
    if "spellingLoc" in location:
        return direct_location(location["spellingLoc"])
    return location


def source_range(node: Node, data: bytes, context: str) -> dict[str, Any]:
    range_info = node.get("range", {})
    begin_info = direct_location(range_info.get("begin", {}))
    end_info = direct_location(range_info.get("end", {}))
    require("offset" in begin_info and "offset" in end_info, f"{context}: missing source offsets")
    begin = int(begin_info["offset"])
    end_token = int(end_info["offset"])
    end_exclusive = end_token + int(end_info.get("tokLen", 0))
    require(begin <= end_token < end_exclusive <= len(data), f"{context}: invalid source range")
    return {
        "begin": offset_record(data, begin),
        "end_exclusive": offset_record(data, end_exclusive),
        "clang_end_token": offset_record(data, end_token),
    }


def parameters(function: Node) -> list[dict[str, str]]:
    result: list[dict[str, str]] = []
    for node in children(function):
        if node.get("kind") == "ParmVarDecl":
            result.append(
                {
                    "name": str(node.get("name")),
                    "type": str(node.get("type", {}).get("qualType")),
                }
            )
    return result


def validate_function_signature(function: Node, role: str) -> None:
    actual_parameters = parameters(function)
    require(
        len(actual_parameters) == len(EXPECTED_PARAMETERS),
        f"{role}: function signature expected {len(EXPECTED_PARAMETERS)} parameters, "
        f"got {len(actual_parameters)}",
    )
    for index, ((expected_name, expected_type), actual) in enumerate(
        zip(EXPECTED_PARAMETERS, actual_parameters, strict=True)
    ):
        require(
            actual == {"name": expected_name, "type": expected_type},
            f"{role}: parameter {index} signature changed: expected "
            f"{expected_type} {expected_name}, got {actual['type']} {actual['name']}",
        )

    actual_type = str(function.get("type", {}).get("qualType"))
    require(
        actual_type == EXPECTED_FUNCTION_QUALTYPE,
        f"{role}: function signature changed: expected "
        f"{EXPECTED_FUNCTION_QUALTYPE}, got {actual_type}",
    )


def run_clang(
    clang: str,
    facade: Path,
    facade_display: str,
    source: Path,
    source_display: str,
) -> tuple[Node, list[str], str]:
    command = [
        clang,
        "-std=c11",
        "-Werror",
        "-fno-color-diagnostics",
        "-include",
        str(facade),
        "-Xclang",
        "-ast-dump=json",
        "-fsyntax-only",
        str(source),
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise ExtractError(
            f"clang rejected {source}: exit {result.returncode}\n{result.stderr.rstrip()}"
        )
    try:
        ast = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ExtractError(f"clang emitted invalid AST JSON for {source}: {error}") from error
    recorded_command = command.copy()
    recorded_command[0] = Path(recorded_command[0]).name
    recorded_command[5] = facade_display
    recorded_command[-1] = source_display
    return ast, recorded_command, result.stderr


def preprocess_unit(
    clang: str,
    facade: Path,
    facade_display: str,
    source: Path,
    source_display: str,
) -> dict[str, Any]:
    command = [
        clang,
        "-std=c11",
        "-Werror",
        "-fno-color-diagnostics",
        "-include",
        str(facade),
        "-E",
        "-P",
        str(source),
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode != 0:
        diagnostics = result.stderr.decode("utf-8", errors="replace").rstrip()
        raise ExtractError(
            f"clang preprocessing failed for {source}: exit {result.returncode}\n{diagnostics}"
        )
    recorded_command = command.copy()
    recorded_command[0] = Path(recorded_command[0]).name
    recorded_command[5] = facade_display
    recorded_command[-1] = source_display
    return {
        "clang_command": recorded_command,
        "byte_length": len(result.stdout),
        "sha256": hashlib.sha256(result.stdout).hexdigest(),
    }


def extract_unit(
    role: str,
    display_path: str,
    path: Path,
    function_name_expected: str,
    clang: str,
    facade: Path,
    facade_display: str,
) -> dict[str, Any]:
    ast, command, diagnostics = run_clang(
        clang, facade, facade_display, path, display_path
    )
    function = find_definition(ast, function_name_expected)
    validate_function_signature(function, role)
    body = function_body(function)
    allowed_calls = SOURCE_CALLS if role == "source" else TARGET_CALLS
    data = path.read_bytes()
    coverage = audit_coverage(
        function, body, role, allowed_calls, data, display_path
    )
    structure = validate_source(function, body) if role == "source" else validate_target(function, body)
    calls = call_counter(body)
    return {
        "role": role,
        "path": display_path,
        "byte_length": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "preprocessed_unit": preprocess_unit(
            clang, facade, facade_display, path, display_path
        ),
        "clang_command": command,
        "clang_diagnostics": diagnostics,
        "function": {
            "name": function_name_expected,
            "type": str(function.get("type", {}).get("qualType")),
            "parameters": parameters(function),
            "range": source_range(function, data, f"{role} function"),
            "body_range": source_range(body, data, f"{role} body"),
        },
        "intrinsic_spellings": sorted(calls),
        "intrinsic_call_counts": dict(sorted(calls.items())),
        "ast_coverage": coverage,
        "validated_structure": structure,
    }


def resolve_clang(requested: str) -> str:
    found = shutil.which(requested)
    require(found is not None, f"could not find clang executable {requested!r}")
    return str(Path(found).resolve())


def clang_version(clang: str) -> str:
    result = subprocess.run([clang, "--version"], text=True, capture_output=True, check=False)
    require(result.returncode == 0, f"failed to query clang version: {result.stderr.rstrip()}")
    lines = [line for line in result.stdout.splitlines() if not line.startswith("InstalledDir:")]
    return "\n".join(lines).rstrip()


def resolve_input(path: Path, repo_root: Path) -> Path:
    return (path if path.is_absolute() else repo_root / path).resolve()


def repository_display(path: Path, repo_root: Path) -> str:
    try:
        display = path.relative_to(repo_root).as_posix()
    except ValueError as error:
        raise ExtractError(f"{path} is outside repository root {repo_root}") from error
    require(display != "", "artifact path must name a file below the repository root")
    require(
        not display.startswith("upstream-main/"),
        "--repo-root must name the actual SALTyRN checkout",
    )
    return display


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True, help="C file defining test_neon")
    parser.add_argument("--target", type=Path, required=True, help="C file defining test_rvv")
    parser.add_argument("--output", type=Path, required=True, help="JSON manifest path")
    parser.add_argument("--clang", default="clang")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--facade", type=Path)
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    source = resolve_input(args.source, repo_root)
    target = resolve_input(args.target, repo_root)
    source_display = repository_display(source, repo_root)
    target_display = repository_display(target, repo_root)
    facade = (args.facade or Path(__file__).with_name("s8_vclamp_parse_facade.h")).resolve()
    extractor = Path(__file__).resolve()
    facade_display = repository_display(facade, repo_root)
    extractor_display = repository_display(extractor, repo_root)

    try:
        require(source.is_file(), f"source file does not exist: {source}")
        require(target.is_file(), f"target file does not exist: {target}")
        require(facade.is_file(), f"parse facade does not exist: {facade}")
        clang = resolve_clang(args.clang)
        manifest = {
            "schema_version": 1,
            "artifact_kind": "saltyrn.s8-vclamp.clang-ast-audit",
            "trust_boundary": (
                "This manifest proves extraction coverage for a pinned Clang AST and parse facade. "
                "It does not prove C, intrinsic, ISA, or Lean semantic adequacy."
            ),
            "extractor": {
                "path": extractor_display,
                "byte_length": extractor.stat().st_size,
                "sha256": sha256(extractor),
            },
            "parse_facade": {
                "path": facade_display,
                "byte_length": facade.stat().st_size,
                "sha256": sha256(facade),
            },
            "clang": {
                "executable": Path(clang).name,
                "version_command": [Path(clang).name, "--version"],
                "version": clang_version(clang),
            },
            "coverage_policy": {
                "semantic_scope": "all nonempty Clang AST nodes rooted at each function body",
                "consumed": (
                    "accepted by a role-specific node-kind handler with strict type, call, "
                    "operator, and cast discriminator checks"
                ),
                "fail_closed_on": [
                    "reachable floating-point literal or type",
                    "unknown function call spelling",
                    "unknown AST node kind",
                    "unknown operator or cast kind",
                    "departure from the expected full source/target control and data flow",
                ],
            },
            "units": {
                "source": extract_unit(
                    "source", source_display, source, "test_neon", clang, facade,
                    facade_display
                ),
                "target": extract_unit(
                    "target", target_display, target, "test_rvv", clang, facade,
                    facade_display
                ),
            },
        }
    except (ExtractError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    source_count = manifest["units"]["source"]["ast_coverage"]["semantic_nodes"]
    target_count = manifest["units"]["target"]["ast_coverage"]["semantic_nodes"]
    print(
        f"audited test_neon ({source_count}/{source_count}) and "
        f"test_rvv ({target_count}/{target_count}) -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
