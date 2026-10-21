#!/usr/bin/env python3
"""Extract the 64-byte main loop of SALTy-RN's u8-vclamp into typed Lean IR."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
from typing import Any, Iterator


Node = dict[str, Any]
Expr = tuple[Any, ...]


class ExtractError(RuntimeError):
    pass


def walk(node: Any) -> Iterator[Node]:
    if not isinstance(node, dict):
        return
    yield node
    for child in node.get("inner", []):
        yield from walk(child)


def first(node: Node, kind: str) -> Node | None:
    return next((item for item in walk(node) if item.get("kind") == kind), None)


def function_name(call: Node) -> str:
    for item in walk(call.get("inner", [{}])[0]):
        decl = item.get("referencedDecl", {})
        if item.get("kind") == "DeclRefExpr" and decl.get("kind") == "FunctionDecl":
            return str(decl["name"])
    raise ExtractError("call expression has no function declaration")


def call_args(call: Node) -> list[Node]:
    return list(call.get("inner", [])[1:])


def referenced_value(node: Node) -> str:
    for item in walk(node):
        decl = item.get("referencedDecl", {})
        if item.get("kind") == "DeclRefExpr" and decl.get("kind") in {
            "VarDecl",
            "ParmVarDecl",
        }:
            return str(decl["name"])
    raise ExtractError(f"expected a variable reference in {node.get('kind')}")


def integer_value(node: Node) -> int:
    literal = first(node, "IntegerLiteral")
    if literal is None:
        raise ExtractError(f"expected an integer literal in {node.get('kind')}")
    return int(literal["value"], 0)


def parenthesize(rendered: str, indent: int) -> str:
    lines = rendered.splitlines()
    lines[0] = " " * indent + "(" + lines[0].lstrip()
    lines[-1] += ")"
    return "\n".join(lines)


def render_expr(expr: Expr, indent: int = 0) -> str:
    prefix = " " * indent
    match expr:
        case ("load", offset):
            return f"{prefix}.load {offset}"
        case ("splat", param):
            return f'{prefix}.splat (.paramU32Trunc "{param}")'
        case ("bin", op, lhs, rhs):
            lhs_text = parenthesize(render_expr(lhs, indent + 4), indent + 2)
            rhs_text = parenthesize(render_expr(rhs, indent + 4), indent + 2)
            return f"{prefix}.bin (.{op} .unsigned)\n{lhs_text}\n{rhs_text}"
        case _:
            raise ExtractError(f"unknown expression node: {expr!r}")


def clang_ast(clang: str, facade: Path, source: Path) -> Node:
    command = [
        clang,
        "-std=c11",
        "-include",
        str(facade),
        "-Xclang",
        "-ast-dump=json",
        "-fsyntax-only",
        str(source),
    ]
    result = subprocess.run(command, text=True, capture_output=True, check=False)
    if result.returncode != 0:
        raise ExtractError(f"clang failed:\n{result.stderr}")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ExtractError(f"clang emitted invalid AST JSON: {error}") from error


def extract(ast: Node, source: Path) -> tuple[Node, int, int, int, list[tuple[int, Expr]]]:
    function = next(
        (
            node
            for node in walk(ast)
            if node.get("kind") == "FunctionDecl"
            and node.get("name") == "test_neon"
            and any(child.get("kind") == "CompoundStmt" for child in node.get("inner", []))
        ),
        None,
    )
    if function is None:
        raise ExtractError("could not find the definition of test_neon")

    body = next(
        child for child in function["inner"] if child.get("kind") == "CompoundStmt"
    )
    top_level = body.get("inner", [])
    main_loop = next((node for node in top_level if node.get("kind") == "ForStmt"), None)
    if main_loop is None:
        raise ExtractError("test_neon has no fixed-width for loop")

    values: dict[str, Expr] = {}
    for statement in top_level[: top_level.index(main_loop)]:
        if statement.get("kind") != "DeclStmt":
            continue
        variable = statement.get("inner", [{}])[0]
        call = first(variable, "CallExpr")
        if call is None or function_name(call) != "vdupq_n_u8":
            continue
        members = [
            node
            for node in walk(call_args(call)[0])
            if node.get("kind") == "MemberExpr" and node.get("name") in {"min", "max"}
        ]
        if len(members) != 1:
            raise ExtractError(f"cannot identify the parameter for {variable.get('name')}")
        member = members[0]
        member_type = str(member.get("type", {}).get("qualType", "")).removeprefix("const ")
        if member_type != "uint32_t":
            raise ExtractError(
                f"expected a uint32_t parameter for {variable.get('name')}, got {member_type}"
            )
        values[str(variable["name"])] = ("splat", str(member["name"]))

    condition = next(
        node
        for node in main_loop.get("inner", [])
        if node.get("kind") == "BinaryOperator" and node.get("opcode") == ">="
    )
    update = next(
        node
        for node in main_loop.get("inner", [])
        if node.get("kind") == "CompoundAssignOperator" and node.get("opcode") == "-="
    )
    batch_guard = integer_value(condition)
    batch_decrement = integer_value(update)
    loop_body = next(
        node for node in main_loop.get("inner", []) if node.get("kind") == "CompoundStmt"
    )

    input_offset = 0
    output_offset = 0
    stores: list[tuple[int, Expr]] = []
    allowed_vector_calls = {"vld1q_u8", "vmaxq_u8", "vminq_u8", "vst1q_u8"}

    for statement in loop_body.get("inner", []):
        kind = statement.get("kind")
        if kind == "DeclStmt":
            variable = statement.get("inner", [{}])[0]
            call = first(variable, "CallExpr")
            if call is None or function_name(call) != "vld1q_u8":
                raise ExtractError(f"unsupported declaration at AST offset {variable.get('loc')}")
            if call.get("type", {}).get("qualType") != "uint8x16_t":
                raise ExtractError("vld1q_u8 did not produce uint8x16_t")
            if referenced_value(call_args(call)[0]) != "input":
                raise ExtractError("the main-loop load is not based on input")
            values[str(variable["name"])] = ("load", input_offset)
            continue

        if kind == "CompoundAssignOperator" and statement.get("opcode") == "+=":
            pointer = referenced_value(statement.get("inner", [{}])[0])
            amount = integer_value(statement)
            if pointer == "input":
                input_offset += amount
            elif pointer == "output":
                output_offset += amount
            else:
                raise ExtractError(f"unsupported pointer update: {pointer}")
            continue

        if kind == "BinaryOperator" and statement.get("opcode") == "=":
            lhs, rhs = statement.get("inner", [None, None])
            if lhs is None or rhs is None:
                raise ExtractError("malformed assignment")
            target = referenced_value(lhs)
            call = first(rhs, "CallExpr")
            if call is None:
                raise ExtractError(f"assignment to {target} has no intrinsic call")
            name = function_name(call)
            if name not in {"vmaxq_u8", "vminq_u8"}:
                raise ExtractError(f"unsupported intrinsic in assignment: {name}")
            if call.get("type", {}).get("qualType") != "uint8x16_t":
                raise ExtractError(f"{name} did not produce uint8x16_t")
            args = call_args(call)
            if len(args) != 2:
                raise ExtractError(f"{name} does not have two arguments")
            arg_names = [referenced_value(arg) for arg in args]
            try:
                lhs_expr, rhs_expr = (values[arg_names[0]], values[arg_names[1]])
            except KeyError as error:
                raise ExtractError(f"use before definition: {error.args[0]}") from error
            op = "max" if name == "vmaxq_u8" else "min"
            values[target] = ("bin", op, lhs_expr, rhs_expr)
            continue

        if kind == "CallExpr":
            name = function_name(statement)
            if name not in allowed_vector_calls:
                raise ExtractError(f"unsupported call in main loop: {name}")
            if name != "vst1q_u8":
                raise ExtractError(f"unexpected top-level intrinsic call: {name}")
            args = call_args(statement)
            if referenced_value(args[0]) != "output":
                raise ExtractError("the main-loop store is not based on output")
            value_name = referenced_value(args[1])
            if value_name not in values:
                raise ExtractError(f"store uses unknown vector: {value_name}")
            stores.append((output_offset, values[value_name]))
            continue

        raise ExtractError(f"unsupported {kind} in the main loop")

    calls = {
        function_name(node)
        for node in walk(loop_body)
        if node.get("kind") == "CallExpr"
    }
    unknown_calls = calls - allowed_vector_calls
    if unknown_calls:
        raise ExtractError(f"unmapped main-loop intrinsics: {sorted(unknown_calls)}")
    if batch_guard != batch_decrement:
        raise ExtractError("loop guard and decrement disagree")
    if input_offset != batch_decrement or output_offset != batch_decrement:
        raise ExtractError("pointer advances do not match the batch decrement")
    if [offset for offset, _ in stores] != [0, 16, 32, 48]:
        raise ExtractError("main-loop stores are not four contiguous 16-byte writes")

    return main_loop, batch_guard, input_offset, output_offset, stores


def emit(source: Path, source_display: str, loop: Node, batch: int, input_advance: int,
         output_advance: int, stores: list[tuple[int, Expr]]) -> str:
    source_bytes = source.read_bytes()
    digest = hashlib.sha256(source_bytes).hexdigest()
    source_range = loop.get("range", {})
    begin = int(source_range.get("begin", {}).get("offset", 0))
    end_info = source_range.get("end", {})
    end = int(end_info.get("offset", begin)) + int(end_info.get("tokLen", 0))

    blocks: list[str] = []
    for index, (offset, expr) in enumerate(stores):
        blocks.append(
            f"def u8VClampBlock{index} : Store 16 8 :=\n"
            f"  {{ outputOffset := {offset}\n"
            f"    value :=\n{render_expr(expr, 6)} }}\n"
        )
    block_names = ",\n       ".join(
        f"u8VClampBlock{index}" for index in range(len(stores))
    )
    source_literal = json.dumps(source_display)

    return "\n".join(
        [
            "-- Generated by tools/extract_u8_vclamp.py. Do not hand-edit.",
            "import Neon2LeanDemo.IR",
            "",
            "namespace Neon2LeanDemo.Generated",
            "",
            f"def extractedSource : SourceInfo :=",
            f"  {{ path := {source_literal}",
            f"    sha256 := \"{digest}\"",
            f"    beginOffset := {begin}",
            f"    endOffset := {end} }}",
            "",
            *blocks,
            "def u8VClampMain : FixedLoop 16 8 :=",
            "  { source := extractedSource",
            f"    batchGuard := {batch}",
            f"    batchDecrement := {batch}",
            f"    inputAdvance := {input_advance}",
            f"    outputAdvance := {output_advance}",
            "    stores :=",
            f"      [{block_names}] }}",
            "",
            "end Neon2LeanDemo.Generated",
            "",
        ]
    )


def repository_display(path: Path, repo_root: Path) -> str:
    try:
        display = path.relative_to(repo_root).as_posix()
    except ValueError as error:
        raise ExtractError(f"{path} is outside repository root {repo_root}") from error
    if not display or display.startswith("upstream-main/"):
        raise ExtractError("--repo-root must name the actual SALTyRN checkout")
    return display


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--clang", default="clang")
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    source = (args.source if args.source.is_absolute() else repo_root / args.source).resolve()
    source_display = repository_display(source, repo_root)
    facade = Path(__file__).with_name("u8_vclamp_parse_facade.h").resolve()
    try:
        ast = clang_ast(args.clang, facade, source)
        loop, batch, input_advance, output_advance, stores = extract(ast, source)
        generated = emit(
            source, source_display, loop, batch, input_advance, output_advance, stores
        )
    except (ExtractError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(generated, encoding="utf-8")
    print(
        f"extracted {len(stores)} stores, {batch} bytes/iteration -> {args.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
