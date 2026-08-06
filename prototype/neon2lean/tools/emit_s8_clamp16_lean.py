#!/usr/bin/env python3
"""Emit Lean data declarations from an s8-clamp16 semantic IR manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


class EmitError(RuntimeError):
    pass


TYPE_TAGS = {
    "pointer": ".pointer",
    "i8": ".scalar (.int 8 .signed)",
    "u64": ".scalar (.int 64 .unsigned)",
    "fixed16": ".vector (.fixed 16) (.int 8 .signed)",
    "scalable_m1": ".vector (.scalable .m1) (.int 8 .signed)",
}

ARCHITECTURES = {"neon", "rvv", "neutral", "c"}
FAMILIES = {"integer", "memory", "control", "conversion", "mask", "floatingPoint"}


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EmitError(message)


def integer(value: Any, context: str) -> int:
    require(isinstance(value, int) and not isinstance(value, bool) and value >= 0,
            f"{context}: expected nonnegative integer")
    return value


def string(value: Any, context: str) -> str:
    require(isinstance(value, str), f"{context}: expected string")
    return value


def lean_string(value: Any, context: str) -> str:
    return json.dumps(string(value, context), ensure_ascii=True)


def digest(value: Any, context: str) -> str:
    text = string(value, context)
    require(len(text) == 64 and all(character in "0123456789abcdef" for character in text),
            f"{context}: invalid sha256")
    return lean_string(text, context)


def source_range(value: Any, context: str) -> str:
    require(isinstance(value, dict), f"{context}: expected source range")
    begin = integer(value.get("begin_offset"), f"{context}.begin_offset")
    end = integer(value.get("end_offset"), f"{context}.end_offset")
    require(begin <= end, f"{context}: inverted source range")
    return (
        "{ path := " + lean_string(value.get("path"), f"{context}.path")
        + f", beginOffset := {begin}, endOffset := {end} }}"
    )


def value_tag(value: Any, context: str) -> str:
    key = string(value, context)
    require(key in TYPE_TAGS, f"{context}: unknown value type {key}")
    return TYPE_TAGS[key]


def node_ref(value: Any, context: str) -> str:
    require(isinstance(value, dict), f"{context}: expected IR reference")
    kind = string(value.get("kind"), f"{context}.kind")
    require(kind in {"parameter", "operation", "block"}, f"{context}: unknown IR ref kind")
    node_id = integer(value.get("node_id"), f"{context}.node_id")
    return f".{kind} {node_id}"


def coverage_entry(value: Any, context: str) -> str:
    require(isinstance(value, dict), f"{context}: expected coverage entry")
    disposition = value.get("disposition")
    require(isinstance(disposition, dict), f"{context}: missing disposition")
    require(disposition.get("kind") == "translated", f"{context}: non-translated entry")
    references = disposition.get("ir_nodes")
    require(isinstance(references, list) and references, f"{context}: empty IR reference list")
    rendered_refs = ", ".join(
        node_ref(reference, f"{context}.ir_nodes[{index}]")
        for index, reference in enumerate(references)
    )
    return (
        "{ astNodeId := " + str(integer(value.get("ast_node_id"), f"{context}.ast_node_id"))
        + ", kind := " + lean_string(value.get("kind"), f"{context}.kind")
        + ", source := " + source_range(value.get("source"), f"{context}.source")
        + f", disposition := .translated [{rendered_refs}] }}"
    )


def parameter(value: Any, context: str) -> str:
    require(isinstance(value, dict), f"{context}: expected parameter")
    origin = string(value.get("origin"), f"{context}.origin")
    require(origin in {"function", "structured_control_input"}, f"{context}: invalid origin")
    lean_origin = ".function" if origin == "function" else ".structuredControlInput"
    return (
        "{ nodeId := " + str(integer(value.get("node_id"), f"{context}.node_id"))
        + ", name := " + lean_string(value.get("name"), f"{context}.name")
        + ", valueType := " + value_tag(value.get("value_type"), f"{context}.value_type")
        + ", origin := " + lean_origin
        + ", source := " + source_range(value.get("source"), f"{context}.source") + " }"
    )


def operation(value: Any, context: str) -> str:
    require(isinstance(value, dict), f"{context}: expected operation")
    architecture = string(value.get("architecture"), f"{context}.architecture")
    family = string(value.get("family"), f"{context}.family")
    require(architecture in ARCHITECTURES, f"{context}: unknown architecture")
    require(family in FAMILIES, f"{context}: unknown family")
    operand_nodes = value.get("operand_nodes")
    operand_types = value.get("operand_types")
    require(isinstance(operand_nodes, list) and isinstance(operand_types, list),
            f"{context}: malformed operands")
    require(len(operand_nodes) == len(operand_types), f"{context}: operand arity mismatch")
    lean_nodes = ", ".join(str(integer(item, f"{context}.operand_nodes")) for item in operand_nodes)
    lean_types = ", ".join(
        value_tag(item, f"{context}.operand_types[{index}]")
        for index, item in enumerate(operand_types)
    )
    result = value.get("result_type")
    lean_result = (
        "none" if result is None
        else f"some ({value_tag(result, f'{context}.result_type')})"
    )
    config = value.get("rvv_config")
    if config is None:
        lean_config = "none"
    else:
        require(isinstance(config, dict), f"{context}: malformed RVV config")
        lmul = string(config.get("lmul"), f"{context}.rvv_config.lmul")
        require(lmul in {"mf8", "mf4", "mf2", "m1", "m2", "m4", "m8"},
                f"{context}: invalid LMUL")
        lean_config = (
            "some { sew := " + str(integer(config.get("sew"), f"{context}.rvv_config.sew"))
            + f", lmul := .{lmul}, activeVLNode := "
            + str(integer(config.get("active_vl_node"), f"{context}.rvv_config.active_vl_node"))
            + " }"
        )
    return (
        "{ nodeId := " + str(integer(value.get("node_id"), f"{context}.node_id"))
        + f", operation := {{ architecture := .{architecture}, family := .{family}, spelling := "
        + lean_string(value.get("spelling"), f"{context}.spelling") + " }"
        + f", operandNodes := [{lean_nodes}], operandTypes := [{lean_types}]"
        + f", resultType := {lean_result}, rvvConfig := {lean_config}"
        + ", source := " + source_range(value.get("source"), f"{context}.source") + " }"
    )


def list_lines(items: list[str], indent: str) -> str:
    if not items:
        return "[]"
    return "[\n" + (",\n" + indent).join(indent + item for item in items) + "\n" + indent[:-2] + "]"


def unit_declarations(name: str, unit: Any, facade: Any, clang: Any, extractor: Any,
                      registry_id: str) -> str:
    require(isinstance(unit, dict), f"units.{name}: expected object")
    artifact = unit.get("artifact")
    function = unit.get("function")
    coverage = unit.get("coverage")
    ir = unit.get("ir")
    control = unit.get("control")
    for value, label in ((artifact, "artifact"), (function, "function"),
                         (coverage, "coverage"), (ir, "ir"), (control, "control")):
        require(isinstance(value, dict), f"units.{name}.{label}: expected object")

    entries = coverage.get("entries")
    parameters = ir.get("parameters")
    blocks = ir.get("blocks")
    require(isinstance(entries, list), f"units.{name}.coverage.entries: expected list")
    require(isinstance(parameters, list), f"units.{name}.ir.parameters: expected list")
    require(isinstance(blocks, list) and len(blocks) == 1, f"units.{name}: expected one block")
    block = blocks[0]
    operations = block.get("operations")
    successors = block.get("successors")
    require(isinstance(operations, list) and successors == [], f"units.{name}: malformed block")

    rendered_entries = [
        coverage_entry(entry, f"units.{name}.coverage.entries[{index}]")
        for index, entry in enumerate(entries)
    ]
    rendered_parameters = [
        parameter(item, f"units.{name}.ir.parameters[{index}]")
        for index, item in enumerate(parameters)
    ]
    rendered_operations = [
        operation(item, f"units.{name}.ir.operations[{index}]")
        for index, item in enumerate(operations)
    ]

    prefix = "source" if name == "neon" else "target"
    function_source = source_range(function.get("source"), f"units.{name}.function.source")
    require(ir.get("function_source") == function.get("source"), f"units.{name}: function range drift")
    require(ir.get("name") == function.get("name"), f"units.{name}: function name drift")
    expected = integer(coverage.get("expected_node_count"), f"units.{name}.coverage.expected_node_count")
    require(expected == len(entries), f"units.{name}: coverage count mismatch")
    sha = digest(artifact.get("sha256"), f"units.{name}.artifact.sha256")

    control_kind = string(control.get("kind"), f"units.{name}.control.kind")
    total = integer(control.get("total"), f"units.{name}.control.total")
    require(control_kind in {"fixed", "positive_strip_mine"}, f"units.{name}: bad control")
    lean_control = f".fixed {total}" if control_kind == "fixed" else f".positiveStripMine {total}"

    facade_artifact = (
        "{ role := .header, path := " + lean_string(facade.get("path"), "facade.path")
        + ", byteLength := " + str(integer(facade.get("byte_length"), "facade.byte_length"))
        + ", sha256 := { hex := " + digest(facade.get("sha256"), "facade.sha256") + " } }"
    )
    build = (
        "{ frontendName := " + lean_string(clang.get("name"), "clang.name")
        + ", frontendVersion := " + lean_string(clang.get("version"), "clang.version")
        + ", targetTriple := " + lean_string(clang.get("target_triple"), "clang.target_triple")
        + ", languageStandard := " + lean_string(clang.get("language_standard"), "clang.language_standard")
        + ", abi := \"parse-facade-only\", endianness := .little, defines := []"
        + ", includePaths := [" + lean_string(str(Path(string(facade.get("path"), "facade.path")).parent), "facade.include")
        + "], compilerFlags := [\"-Werror\", \"-fno-color-diagnostics\"] }"
    )

    return f"""
def {prefix}Envelope : ArtifactEnvelope :=
  {{ schemaVersion := 1
    operationRegistryId := {lean_string(registry_id, 'operation_registry_id')}
    translationUnit :=
      {{ role := .translationUnit
        path := {lean_string(artifact.get('path'), f'units.{name}.artifact.path')}
        byteLength := {integer(artifact.get('byte_length'), f'units.{name}.artifact.byte_length')}
        sha256 := {{ hex := {sha} }} }}
    preprocessedUnit :=
      {{ role := .preprocessedUnit
        path := {lean_string(artifact.get('preprocessed_path'), f'units.{name}.artifact.preprocessed_path')}
        byteLength := {integer(artifact.get('preprocessed_byte_length'), f'units.{name}.artifact.preprocessed_byte_length')}
        sha256 := {{ hex := {digest(artifact.get('preprocessed_sha256'), f'units.{name}.artifact.preprocessed_sha256')} }} }}
    headers := [{facade_artifact}]
    build := {build}
    extractorName := {lean_string(extractor.get('path'), 'extractor.path')}
    extractorVersion := {digest(extractor.get('sha256'), 'extractor.sha256')}
    coverage :=
      {{ translationUnitSha256 := {{ hex := {sha} }}
        functionName := {lean_string(function.get('name'), f'units.{name}.function.name')}
        functionSource := {function_source}
        expectedNodeCount := {expected}
        entries := {list_lines(rendered_entries, '          ')} }} }}

def {prefix}IR : KernelIR :=
  {{ name := {lean_string(ir.get('name'), f'units.{name}.ir.name')}
    translationUnitSha256 := {{ hex := {digest(ir.get('translation_unit_sha256'), f'units.{name}.ir.sha256')} }}
    functionSource := {function_source}
    parameters := {list_lines(rendered_parameters, '      ')}
    entryBlock := {integer(ir.get('entry_block'), f'units.{name}.ir.entry_block')}
    blocks :=
      [{{ blockId := {integer(block.get('block_id'), f'units.{name}.ir.block_id')}
         operations := {list_lines(rendered_operations, '           ')}
         successors := []
         source := {source_range(block.get('source'), f'units.{name}.ir.block.source')} }}] }}

def {prefix}Control : ControlMode := {lean_control}
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        require(manifest.get("artifact_kind") == "saltyrn.s8-clamp16.semantic-ir", "wrong artifact kind")
        require(integer(manifest.get("schema_version"), "schema_version") == 1, "unsupported schema")
        units = manifest.get("units")
        require(isinstance(units, dict) and set(units) == {"neon", "rvv"}, "expected neon and rvv units")
        facade = manifest.get("facade")
        clang = manifest.get("clang")
        extractor = manifest.get("extractor")
        require(isinstance(facade, dict) and isinstance(clang, dict) and isinstance(extractor, dict),
                "missing provenance")
        text = """import Neon2LeanDemo.Production.All

namespace Neon2LeanDemo.S8Clamp16.Generated

open Neon2LeanDemo.Production
"""
        registry_id = string(manifest.get("operation_registry_id"), "operation_registry_id")
        require(registry_id, "operation_registry_id must not be empty")
        text += unit_declarations("neon", units["neon"], facade, clang, extractor, registry_id)
        text += unit_declarations("rvv", units["rvv"], facade, clang, extractor, registry_id)
        text += "\nend Neon2LeanDemo.S8Clamp16.Generated\n"
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text, encoding="utf-8")
    except (EmitError, OSError, json.JSONDecodeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
