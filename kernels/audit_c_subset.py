#!/usr/bin/env python3
"""Inventory kernel syntax using the existing Lean parser; emit JSON to stdout.

Build first: cd lean-transpiler && lake build
Run from any directory: python3 kernels/audit_c_subset.py
Audit checked-in RVV targets: add --sources kernels/target

Includes all conditional branches and the parameter records embedded in leading
comments (--kernel). Does not expand headers/macros, type-check, or infer runtime
semantics. Counts are AST occurrences and distinct files, not execution counts.
"""

import argparse
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
TAGS = {
    "block", "ifThen", "forLoop", "whileLoop", "doWhile", "returnStmt",
    "breakStmt", "continueStmt", "conditional", "cast", "sizeofType",
    "initList", "index", "member", "intrinsic", "call", "directive",
}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--sources", type=Path, default=ROOT / "kernels/source")
    ap.add_argument("--parser", type=Path,
                    default=ROOT / "lean-transpiler/.lake/build/bin/neon2rvv")
    ap.add_argument("--intrinsics", type=Path,
                    default=ROOT / "op-semantics/neon-intrinsics.md")
    ap.add_argument("--rvv-intrinsics", type=Path,
                    default=ROOT / "op-semantics/rvv-intrinsics.md")
    args = ap.parse_args()
    sources = sorted(args.sources.glob("*.c"))
    if not sources:
        ap.error("no source kernels found")
    counts = Counter()
    files = defaultdict(set)
    inventories = defaultdict(set)
    per_file = {}

    for source in sources:
        parsed = subprocess.run(
            [str(args.parser.resolve()), "ast", str(source), "--kernel"],
            check=True, capture_output=True, text=True,
        )
        ast = json.loads(parsed.stdout)
        local = Counter()

        def add(feature):
            counts[feature] += 1
            local[feature] += 1
            files[feature].add(source.name)

        def walk(node):
            if isinstance(node, list):
                for child in node:
                    walk(child)
                return
            if isinstance(node, str):
                if node in {"breakStmt", "continueStmt"}:
                    add(node)
                return
            if not isinstance(node, dict):
                return
            if len(node) == 1:
                tag, value = next(iter(node.items()))
                if tag in TAGS:
                    add(tag)
                if tag in {"unary", "postfix", "binary"}:
                    add(f"{tag}:{value['op']}")
                if tag == "call":
                    callee = value["callee"]
                    if "ident" in callee:
                        name = callee["ident"]["name"]
                        inventories["ordinary_calls"].add(name)
                        add(f"call:{name}")
                    else:
                        add("indirect_call")
                if tag == "intrinsic":
                    dialect, intrinsic = next(iter(value["op"].items()))
                    inventories[f"{dialect}_intrinsics"].add(intrinsic["name"])
                if tag == "function" and value["value"]["body"] is not None:
                    add("function_definition")
                if tag == "member":
                    add("member:arrow" if value["arrow"] else "member:dot")
                    if value["field"] == "val":
                        add("tuple_member")
                if tag == "forLoop":
                    init = value["init"]
                    add("for_init:" + (init if isinstance(init, str) else next(iter(init))))
                    if value["cond"] is None:
                        add("for_omitted_condition")
                    if value["step"] is None:
                        add("for_omitted_step")
                if tag == "ifThen" and value["no"] is not None:
                    add("if_else")
                if tag == "record" and "fields" in value:
                    add("record_definition:" + value["kind"])
                if tag == "nested":
                    add("nested_record:" + value["kind"])
                if tag == "decl" and len(value["vars"]) > 1:
                    add("multiple_declarators")
                if tag == "literal":
                    inventories["literals"].add(value["text"])
                if tag == "directive":
                    inventories["directives"].add(value["text"])
            if {"base", "qualifiers", "pointers"} <= node.keys():
                base = node["base"]
                if "named" in base:
                    inventories["scalar_type_spellings"].add(base["named"]["name"])
                elif "vector" in base:
                    inventories["vector_types"].add(base["vector"]["type"]["spelling"])
                if node["pointers"]:
                    add(f"pointer_depth:{len(node['pointers'])}")
                for q in node["qualifiers"]:
                    add("qualifier_or_storage:" + q)
                for level in node["pointers"]:
                    for q in level:
                        add("pointer_qualifier:" + q)
            if {"dimensions", "alignment", "type"} <= node.keys():
                if node["dimensions"]:
                    add("array_declaration")
                if node["alignment"] is not None:
                    add("aligned_declaration")
            if "attributes" in node:
                for attr in node["attributes"]:
                    add("attribute:" + attr)
            for child in node.values():
                walk(child)

        walk(ast)
        per_file[source.name] = {
            "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "top_level_items": len(ast["items"]),
            "features": dict(sorted(local.items())),
        }

    # A source spelling inventory misses types of nested intrinsic results.
    # Consult the local signature catalogue without parsing intrinsic bodies.
    found = set()
    for line in args.intrinsics.read_text().splitlines():
        signature = re.match(r"\| `([^`]+)` \|", line)
        if not signature:
            continue
        name = re.search(r"\b(v\w+)\(", signature[1])
        if name and name[1] in inventories["neon_intrinsics"]:
            found.add(name[1])
            inventories["intrinsic_signature_vector_types"].update(re.findall(
                r"\b(?:u?int|float)\d+x\d+(?:x\d+)?_t\b", signature[1]))

    rvv_signatures = {}
    for block in re.finditer(r"\*\*Signature:\*\*\s*```c\s*(.*?)```",
                             args.rvv_intrinsics.read_text(), re.S):
        for name in re.findall(r"(__riscv_\w+)\s*\(", block[1]):
            rvv_signatures[name] = block[1]
    missing_rvv = []
    for name in sorted(inventories["rvv_intrinsics"]):
        # Policy variants add mask/merge operands, not new vector element types.
        # Our corpus uses only _tu variants; reuse those base signatures solely
        # to inventory vector types, not to claim argument/signature validation.
        signature = rvv_signatures.get(name)
        if signature is None and name.endswith("_tu"):
            signature = rvv_signatures.get(name[:-3])
        if signature is None:
            missing_rvv.append(name)
        else:
            inventories["rvv_signature_vector_types"].update(re.findall(
                r"\bv(?:u?int|float|bool)\w*_t\b", signature))

    print(json.dumps({
        "scope": "all branches, including promoted parameter comments; no header expansion",
        "source_files": len(sources),
        "source_lines": sum(len(p.read_text().splitlines()) for p in sources),
        "empty_ast_files": [name for name, info in per_file.items() if not info["top_level_items"]],
        "missing_neon_intrinsic_signatures": sorted(inventories["neon_intrinsics"] - found),
        "missing_rvv_intrinsic_signatures": missing_rvv,
        "signature_scope": "local catalogue vector types; RVV _tu uses base signature; no type checking",
        "features": {name: {"occurrences": counts[name], "file_count": len(files[name]),
                             "files": sorted(files[name])} for name in sorted(counts)},
        "inventories": {name: sorted(values) for name, values in sorted(inventories.items())},
        "per_file": per_file,
    }, indent=2))


if __name__ == "__main__":
    main()
