#!/usr/bin/env python3
"""Lower the supported s8-clamp16 C subset to typed semantic IR data.

The frontend is deliberately small and fail closed. It accepts straight-line
load/splat/min/max/store statements and one RVV strip-mined loop. Supported
intrinsic mutations are lowered to different operation spellings rather than
being rejected because they no longer match the expected theorem.
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
from typing import Any, Iterator


Node = dict[str, Any]


class ExtractError(RuntimeError):
    pass


FUNCTION_TYPE = "void (const int8_t *, int8_t *, int8_t, int8_t)"
PARAMETERS = (
    ("input", "const int8_t *", "pointer"),
    ("output", "int8_t *", "pointer"),
    ("lo", "int8_t", "i8"),
    ("hi", "int8_t", "i8"),
)

NODE_KINDS = {
    "BinaryOperator",
    "CallExpr",
    "CompoundAssignOperator",
    "CompoundStmt",
    "DeclRefExpr",
    "DeclStmt",
    "ImplicitCastExpr",
    "IntegerLiteral",
    "VarDecl",
    "WhileStmt",
}

IMPLICIT_CASTS = {"FunctionToPointerDecay", "IntegralCast", "LValueToRValue"}
FLOAT_RE = re.compile(r"(?<![A-Za-z0-9_])(?:float|double|_Float\d+|__fp16|half)(?![A-Za-z0-9_])")

OPS: dict[str, dict[str, Any]] = {
    "vld1q_s8": {
        "architecture": "neon", "family": "memory", "operands": ["pointer"],
        "result": "fixed16", "c_result": "int8x16_t", "effect": "read",
    },
    "vdupq_n_s8": {
        "architecture": "neon", "family": "integer", "operands": ["i8"],
        "result": "fixed16", "c_result": "int8x16_t", "effect": "pure",
    },
    "vmaxq_s8": {
        "architecture": "neon", "family": "integer", "operands": ["fixed16", "fixed16"],
        "result": "fixed16", "c_result": "int8x16_t", "effect": "pure",
    },
    "vminq_s8": {
        "architecture": "neon", "family": "integer", "operands": ["fixed16", "fixed16"],
        "result": "fixed16", "c_result": "int8x16_t", "effect": "pure",
    },
    "vst1q_s8": {
        "architecture": "neon", "family": "memory", "operands": ["pointer", "fixed16"],
        "result": None, "c_result": "void", "effect": "write",
    },
    "__riscv_vsetvl_e8m1": {
        "architecture": "rvv", "family": "control", "operands": ["u64"],
        "result": "u64", "c_result": "size_t", "effect": "control",
    },
    "__riscv_vle8_v_i8m1": {
        "architecture": "rvv", "family": "memory", "operands": ["pointer", "u64"],
        "result": "scalable_m1", "c_result": "vint8m1_t", "effect": "read",
        "rvv": {"sew": 8, "lmul": "m1"},
    },
    "__riscv_vmax_vx_i8m1": {
        "architecture": "rvv", "family": "integer", "operands": ["scalable_m1", "i8", "u64"],
        "result": "scalable_m1", "c_result": "vint8m1_t", "effect": "pure",
        "rvv": {"sew": 8, "lmul": "m1"},
    },
    "__riscv_vmin_vx_i8m1": {
        "architecture": "rvv", "family": "integer", "operands": ["scalable_m1", "i8", "u64"],
        "result": "scalable_m1", "c_result": "vint8m1_t", "effect": "pure",
        "rvv": {"sew": 8, "lmul": "m1"},
    },
    "__riscv_vse8_v_i8m1": {
        "architecture": "rvv", "family": "memory", "operands": ["pointer", "scalable_m1", "u64"],
        "result": None, "c_result": "void", "effect": "write",
        "rvv": {"sew": 8, "lmul": "m1"},
    },
}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ExtractError(message)


def walk(node: Any) -> Iterator[Node]:
    if not isinstance(node, dict):
        return
    if node.get("kind"):
        yield node
    for child in node.get("inner", []):
        yield from walk(child)


def children(node: Node) -> list[Node]:
    return [child for child in node.get("inner", []) if child.get("kind")]


def only_child(node: Node, context: str) -> Node:
    items = children(node)
    require(len(items) == 1, f"{context}: expected one child, got {len(items)}")
    return items[0]


def strip_expr(node: Node) -> Node:
    current = node
    while current.get("kind") == "ImplicitCastExpr":
        current = only_child(current, "implicit cast")
    return current


def direct_ref(node: Node, context: str) -> str:
    item = strip_expr(node)
    require(item.get("kind") == "DeclRefExpr", f"{context}: expected direct value reference")
    declaration = item.get("referencedDecl", {})
    require(
        declaration.get("kind") in {"ParmVarDecl", "VarDecl"},
        f"{context}: reference is not a value",
    )
    return str(declaration.get("name"))


def function_name(call: Node) -> str:
    require(call.get("kind") == "CallExpr", "expected CallExpr")
    raw = call.get("inner", [])
    require(raw, "call has no callee")
    references = [
        node for node in walk(raw[0])
        if node.get("kind") == "DeclRefExpr"
        and node.get("referencedDecl", {}).get("kind") == "FunctionDecl"
    ]
    require(len(references) == 1, "call does not resolve to one function")
    return str(references[0]["referencedDecl"]["name"])


def call_args(call: Node) -> list[Node]:
    raw = call.get("inner", [])
    require(raw, "call has no callee")
    return list(raw[1:])


def find_definition(ast: Node, name: str) -> Node:
    matches = [
        node for node in walk(ast)
        if node.get("kind") == "FunctionDecl"
        and node.get("name") == name
        and any(child.get("kind") == "CompoundStmt" for child in node.get("inner", []))
    ]
    require(len(matches) == 1, f"expected one definition of {name}, found {len(matches)}")
    return matches[0]


def function_body(function: Node) -> Node:
    bodies = [node for node in children(function) if node.get("kind") == "CompoundStmt"]
    require(len(bodies) == 1, "function must have one body")
    return bodies[0]


def direct_location(location: Node) -> Node:
    if "expansionLoc" in location:
        return direct_location(location["expansionLoc"])
    if "spellingLoc" in location:
        return direct_location(location["spellingLoc"])
    return location


def source_range(node: Node, data: bytes, context: str) -> dict[str, int]:
    raw = node.get("range", {})
    begin = direct_location(raw.get("begin", {}))
    end = direct_location(raw.get("end", {}))
    require("offset" in begin and "offset" in end, f"{context}: missing source offset")
    begin_offset = int(begin["offset"])
    end_offset = int(end["offset"]) + int(end.get("tokLen", 0))
    require(0 <= begin_offset < end_offset <= len(data), f"{context}: invalid source range")
    return {"begin_offset": begin_offset, "end_offset": end_offset}


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def repo_path(path: Path, repo_root: Path) -> str:
    try:
        return path.resolve().relative_to(repo_root.resolve()).as_posix()
    except ValueError as error:
        raise ExtractError(f"artifact is outside repository root: {path}") from error


def run_clang(clang: str, repo_root: Path, source: Path, include_dir: Path) -> tuple[Node, bytes]:
    relative_source = repo_path(source, repo_root)
    relative_include = repo_path(include_dir, repo_root)
    command = [
        clang, "-std=c11", "-Werror", "-fno-color-diagnostics", f"-I{relative_include}",
        "-Xclang", "-ast-dump=json", "-fsyntax-only", relative_source,
    ]
    result = subprocess.run(command, cwd=repo_root, text=True, capture_output=True, check=False)
    require(result.returncode == 0, f"clang AST extraction failed:\n{result.stderr}")
    try:
        ast = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ExtractError(f"clang emitted invalid JSON: {error}") from error

    preprocess = subprocess.run(
        [clang, "-std=c11", "-E", "-P", f"-I{relative_include}", relative_source],
        cwd=repo_root, capture_output=True, check=False,
    )
    require(preprocess.returncode == 0, "clang preprocessing failed")
    return ast, preprocess.stdout


def validate_signature(function: Node) -> list[Node]:
    require(function.get("type", {}).get("qualType") == FUNCTION_TYPE, "function signature changed")
    parameters = [node for node in children(function) if node.get("kind") == "ParmVarDecl"]
    require(len(parameters) == len(PARAMETERS), "function parameter count changed")
    for index, (parameter, expected) in enumerate(zip(parameters, PARAMETERS, strict=True)):
        actual = (parameter.get("name"), parameter.get("type", {}).get("qualType"))
        require(actual == expected[:2], f"parameter {index} changed: expected {expected[:2]}, got {actual}")
    return parameters


def audit_node(node: Node, role: str) -> None:
    kind = str(node.get("kind"))
    require(kind in NODE_KINDS, f"{role}: unsupported AST node kind {kind}")
    for field in ("type", "argType", "computeLHSType", "computeResultType"):
        value = node.get(field)
        if isinstance(value, dict):
            for key in ("qualType", "desugaredQualType"):
                text = value.get(key)
                if isinstance(text, str):
                    require(not FLOAT_RE.search(text), f"{role}: floating type {text!r}")
    if kind == "CallExpr":
        name = function_name(node)
        require(name in OPS, f"{role}: unsupported call spelling {name}")
        require(node.get("type", {}).get("qualType") == OPS[name]["c_result"], f"{role}: call type changed")
    elif kind == "ImplicitCastExpr":
        require(node.get("castKind") in IMPLICIT_CASTS, f"{role}: unsupported cast {node.get('castKind')}")
        only_child(node, f"{role} cast")
    elif kind == "BinaryOperator":
        require(node.get("opcode") in {"=", "!="}, f"{role}: unsupported binary operator")
    elif kind == "CompoundAssignOperator":
        require(role == "rvv" and node.get("opcode") in {"+=", "-="}, "unsupported update")
    elif kind == "WhileStmt":
        require(role == "rvv" and len(children(node)) == 2, "unsupported while statement")
    elif kind == "IntegerLiteral":
        try:
            int(str(node.get("value")), 0)
        except ValueError as error:
            raise ExtractError(f"malformed integer literal {node.get('value')!r}") from error


def declaration(statement: Node, context: str) -> Node:
    require(statement.get("kind") == "DeclStmt", f"{context}: expected declaration")
    variable = only_child(statement, context)
    require(variable.get("kind") == "VarDecl", f"{context}: declaration is not VarDecl")
    return variable


def initializer_call(variable: Node, context: str) -> Node:
    value = only_child(variable, context)
    require(value.get("kind") == "CallExpr", f"{context}: initializer is not a call")
    return value


def assignment_call(statement: Node, context: str) -> tuple[str, Node]:
    require(
        statement.get("kind") == "BinaryOperator" and statement.get("opcode") == "=",
        f"{context}: expected assignment",
    )
    items = children(statement)
    require(len(items) == 2, f"{context}: assignment arity changed")
    target = direct_ref(items[0], f"{context} lhs")
    call = strip_expr(items[1])
    require(call.get("kind") == "CallExpr", f"{context}: rhs is not a call")
    return target, call


def int_literal(node: Node, expected: int, context: str) -> None:
    item = strip_expr(node)
    require(item.get("kind") == "IntegerLiteral", f"{context}: expected integer literal")
    require(int(str(item.get("value")), 0) == expected, f"{context}: literal changed")


def validate_update(statement: Node, target: str, opcode: str) -> None:
    require(
        statement.get("kind") == "CompoundAssignOperator" and statement.get("opcode") == opcode,
        f"expected {target} {opcode} vl",
    )
    items = children(statement)
    require(len(items) == 2, "update arity changed")
    require(direct_ref(items[0], "update lhs") == target, "update target changed")
    require(direct_ref(items[1], "update rhs") == "vl", "update amount changed")


def ir_ref(kind: str, node_id: int) -> dict[str, Any]:
    return {"kind": kind, "node_id": node_id}


class Lowering:
    def __init__(self, role: str, source_path: str, data: bytes) -> None:
        self.role = role
        self.source_path = source_path
        self.data = data
        self.next_operation = 10
        self.environment: dict[str, int] = {name: index + 1 for index, (name, _, _) in enumerate(PARAMETERS)}
        self.operations: list[dict[str, Any]] = []
        self.owners: dict[int, dict[str, Any]] = {}

    def mark(self, node: Node, reference: dict[str, Any]) -> None:
        for item in walk(node):
            self.owners[id(item)] = reference

    def lower_call(self, call: Node, owner: Node) -> int:
        name = function_name(call)
        descriptor = OPS.get(name)
        require(descriptor is not None, f"{self.role}: unsupported call {name}")
        arguments = call_args(call)
        require(len(arguments) == len(descriptor["operands"]), f"{name}: argument count changed")
        operand_nodes: list[int] = []
        for index, argument in enumerate(arguments):
            reference = direct_ref(argument, f"{name} argument {index}")
            require(reference in self.environment, f"{name}: undefined value {reference}")
            operand_nodes.append(self.environment[reference])

        node_id = self.next_operation
        self.next_operation += 1
        rvv = descriptor.get("rvv")
        active_vl = None
        if rvv is not None:
            require("vl" in self.environment, f"{name}: active vl is unavailable")
            active_vl = self.environment["vl"]
        location = source_range(call, self.data, f"{self.role} call {name}")
        self.operations.append(
            {
                "node_id": node_id,
                "architecture": descriptor["architecture"],
                "family": descriptor["family"],
                "spelling": name,
                "operand_nodes": operand_nodes,
                "operand_types": descriptor["operands"],
                "result_type": descriptor["result"],
                "rvv_config": None if rvv is None else {**rvv, "active_vl_node": active_vl},
                "source": {"path": self.source_path, **location},
            }
        )
        self.mark(owner, ir_ref("operation", node_id))
        return node_id


def validate_neon(body: Node, lowering: Lowering) -> None:
    statements = children(body)
    require(len(statements) == 6, "neon: expected six straight-line statements")
    for index in range(3):
        variable = declaration(statements[index], f"neon declaration {index}")
        call = initializer_call(variable, f"neon declaration {index}")
        node_id = lowering.lower_call(call, statements[index])
        lowering.environment[str(variable.get("name"))] = node_id
    for index in range(3, 5):
        target, call = assignment_call(statements[index], f"neon assignment {index}")
        require(target in lowering.environment, f"neon: assignment to unknown {target}")
        node_id = lowering.lower_call(call, statements[index])
        lowering.environment[target] = node_id
    require(statements[5].get("kind") == "CallExpr", "neon: final statement must be a call")
    node_id = lowering.lower_call(statements[5], statements[5])
    require(lowering.operations[-1]["result_type"] is None, "neon: final call must be effectful")
    require(node_id == lowering.operations[-1]["node_id"], "internal lowering error")


def validate_rvv(body: Node, lowering: Lowering) -> Node:
    statements = children(body)
    require(len(statements) == 2, "rvv: expected remaining declaration and while loop")
    remaining = declaration(statements[0], "rvv remaining")
    require(
        (remaining.get("name"), remaining.get("type", {}).get("qualType")) == ("remaining", "size_t"),
        "rvv: remaining declaration changed",
    )
    int_literal(only_child(remaining, "remaining initializer"), 16, "remaining initializer")
    lowering.environment["remaining"] = 5
    lowering.mark(statements[0], ir_ref("parameter", 5))

    loop = statements[1]
    require(loop.get("kind") == "WhileStmt", "rvv: expected while loop")
    loop_items = children(loop)
    require(len(loop_items) == 2, "rvv: while shape changed")
    condition = strip_expr(loop_items[0])
    require(condition.get("kind") == "BinaryOperator" and condition.get("opcode") == "!=", "rvv guard changed")
    guard_items = children(condition)
    require(len(guard_items) == 2, "rvv guard arity changed")
    require(direct_ref(guard_items[0], "rvv guard") == "remaining", "rvv guard variable changed")
    int_literal(guard_items[1], 0, "rvv guard")

    loop_body = loop_items[1]
    loop_statements = children(loop_body)
    require(len(loop_statements) == 8, "rvv: loop body statement count changed")

    for index in range(2):
        variable = declaration(loop_statements[index], f"rvv declaration {index}")
        call = initializer_call(variable, f"rvv declaration {index}")
        node_id = lowering.lower_call(call, loop_statements[index])
        lowering.environment[str(variable.get("name"))] = node_id
    for index in range(2, 4):
        target, call = assignment_call(loop_statements[index], f"rvv assignment {index}")
        require(target in lowering.environment, f"rvv: assignment to unknown {target}")
        lowering.environment[target] = lowering.lower_call(call, loop_statements[index])
    require(loop_statements[4].get("kind") == "CallExpr", "rvv: expected store call")
    lowering.lower_call(loop_statements[4], loop_statements[4])
    require(lowering.operations[-1]["result_type"] is None, "rvv: store call must be effectful")
    validate_update(loop_statements[5], "input", "+=")
    validate_update(loop_statements[6], "output", "+=")
    validate_update(loop_statements[7], "remaining", "-=")
    return loop


def parameter_record(node_id: int, name: str, value_type: str, origin: str,
                     node: Node, path: str, data: bytes) -> dict[str, Any]:
    return {
        "node_id": node_id,
        "name": name,
        "value_type": value_type,
        "origin": origin,
        "source": {"path": path, **source_range(node, data, f"parameter {name}")},
    }


def build_unit(role: str, source: Path, display_path: str, ast: Node, preprocessed: bytes,
               function_name_expected: str) -> dict[str, Any]:
    data = source.read_bytes()
    function = find_definition(ast, function_name_expected)
    parameters = validate_signature(function)
    body = function_body(function)
    for node in walk(body):
        audit_node(node, role)

    lowering = Lowering(role, display_path, data)
    lowering.mark(body, ir_ref("block", 100))
    if role == "neon":
        validate_neon(body, lowering)
        block_source_node = body
        control = {"kind": "fixed", "total": 16}
    else:
        loop = validate_rvv(body, lowering)
        block_source_node = body
        control = {"kind": "positive_strip_mine", "total": 16, "loop_range": source_range(loop, data, "rvv loop")}

    parameter_records = [
        parameter_record(index + 1, expected[0], expected[2], "function", parameter,
                         display_path, data)
        for index, (parameter, expected) in enumerate(zip(parameters, PARAMETERS, strict=True))
    ]
    if role == "rvv":
        remaining_node = only_child(children(body)[0], "remaining declaration")
        parameter_records.append(
            parameter_record(5, "remaining", "u64", "structured_control_input",
                             remaining_node, display_path, data)
        )

    semantic_nodes = list(walk(body))
    entries = []
    parameter_refs = {name: index + 1 for index, (name, _, _) in enumerate(PARAMETERS)}
    if role == "rvv":
        parameter_refs["remaining"] = 5
    for ast_node_id, node in enumerate(semantic_nodes):
        reference = lowering.owners.get(id(node), ir_ref("block", 100))
        references = [reference]
        if node.get("kind") == "DeclRefExpr":
            referenced_name = str(node.get("referencedDecl", {}).get("name"))
            if referenced_name in parameter_refs:
                parameter_reference = ir_ref("parameter", parameter_refs[referenced_name])
                if parameter_reference not in references:
                    references.append(parameter_reference)
        entries.append(
            {
                "ast_node_id": ast_node_id,
                "kind": str(node.get("kind")),
                "source": {"path": display_path, **source_range(node, data, f"coverage node {ast_node_id}")},
                "disposition": {"kind": "translated", "ir_nodes": references},
            }
        )

    body_source = {"path": display_path, **source_range(body, data, "function body")}
    kind_counts = Counter(entry["kind"] for entry in entries)
    return {
        "artifact": {
            "path": display_path,
            "byte_length": len(data),
            "sha256": sha256_bytes(data),
            "preprocessed_path": f"<generated:{function_name_expected}.i>",
            "preprocessed_byte_length": len(preprocessed),
            "preprocessed_sha256": sha256_bytes(preprocessed),
        },
        "function": {
            "name": function_name_expected,
            "qual_type": FUNCTION_TYPE,
            "source": body_source,
        },
        "coverage": {
            "expected_node_count": len(entries),
            "kind_counts": dict(sorted(kind_counts.items())),
            "entries": entries,
        },
        "ir": {
            "name": function_name_expected,
            "translation_unit_sha256": sha256_bytes(data),
            "function_source": body_source,
            "parameters": parameter_records,
            "entry_block": 100,
            "blocks": [
                {
                    "block_id": 100,
                    "operations": lowering.operations,
                    "successors": [],
                    "source": {"path": display_path, **source_range(block_source_node, data, "block")},
                }
            ],
        },
        "control": control,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--neon", type=Path, required=True)
    parser.add_argument("--rvv", type=Path, required=True)
    parser.add_argument("--facade", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--clang", default="clang")
    args = parser.parse_args()

    try:
        repo_root = args.repo_root.resolve()
        neon = args.neon.resolve()
        rvv = args.rvv.resolve()
        facade = args.facade.resolve()
        clang = shutil.which(args.clang)
        require(clang is not None, f"clang executable not found: {args.clang}")
        for path in (neon, rvv, facade):
            require(path.is_file(), f"missing input: {path}")

        neon_ast, neon_preprocessed = run_clang(clang, repo_root, neon, facade.parent)
        rvv_ast, rvv_preprocessed = run_clang(clang, repo_root, rvv, facade.parent)
        version = subprocess.run(
            [clang, "--version"], text=True, capture_output=True, check=True
        ).stdout.splitlines()[0]
        facade_data = facade.read_bytes()
        manifest = {
            "artifact_kind": "saltyrn.s8-clamp16.semantic-ir",
            "schema_version": 1,
            "operation_registry_id": "saltyrn.s8-clamp16.integer.v1",
            "trust_boundary": (
                "A fail-closed Clang AST frontend emitted typed IR data for a restricted C subset. "
                "Lean rechecks registry, reference order, coverage, and execution. Clang/C and "
                "intrinsic-to-ISA adequacy remain external bridges."
            ),
            "clang": {
                "name": "clang",
                "version": version,
                "target_triple": "host-parse-facade-only",
                "language_standard": "c11",
            },
            "extractor": {
                "path": repo_path(Path(__file__), repo_root),
                "byte_length": Path(__file__).stat().st_size,
                "sha256": sha256_bytes(Path(__file__).read_bytes()),
            },
            "facade": {
                "path": repo_path(facade, repo_root),
                "byte_length": len(facade_data),
                "sha256": sha256_bytes(facade_data),
            },
            "units": {
                "neon": build_unit(
                    "neon", neon, repo_path(neon, repo_root), neon_ast,
                    neon_preprocessed, "s8_clamp16_neon"
                ),
                "rvv": build_unit(
                    "rvv", rvv, repo_path(rvv, repo_root), rvv_ast,
                    rvv_preprocessed, "s8_clamp16_rvv"
                ),
            },
        }
        output = args.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except (ExtractError, OSError, subprocess.SubprocessError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
