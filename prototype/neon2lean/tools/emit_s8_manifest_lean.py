#!/usr/bin/env python3
"""Emit Lean ArtifactEnvelope claims from an s8-vclamp AST audit manifest."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
from typing import Any


class EmitError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise EmitError(message)


def lean_string(value: Any) -> str:
    require(type(value) is str, f"expected string, got {type(value).__name__}")
    return json.dumps(value, ensure_ascii=True)


def lean_nat(value: Any, context: str) -> str:
    require(type(value) is int and value >= 0, f"{context}: expected a nonnegative integer")
    return str(value)


def repository_path(value: Any, context: str) -> str:
    require(type(value) is str, f"{context}: expected a string")
    path = Path(value)
    require(not path.is_absolute(), f"{context}: absolute paths are not portable")
    require(".." not in path.parts, f"{context}: parent traversal is not allowed")
    require(
        not value.startswith("upstream-main/"),
        f"{context}: wrapper-worktree paths are not repository relative",
    )
    return value


def target_triple(version: str) -> str:
    match = re.search(r"^Target:\s*(.+)$", version, flags=re.MULTILINE)
    return match.group(1).strip() if match else "unknown"


def render_entries(entries: list[dict[str, Any]]) -> str:
    rendered = []
    for entry in entries:
        source = entry["source"]
        source_path = repository_path(source["path"], "coverage source path")
        disposition = entry["disposition"]
        require(
            disposition["kind"] == "justified_exclusion",
            "audit manifests must not claim semantic translation",
        )
        rendered.append(
            "  { astNodeId := "
            + lean_nat(entry["ast_node_id"], "coverage ast_node_id")
            + "\n"
            + "    kind := "
            + lean_string(entry["kind"])
            + "\n"
            + "    source :=\n"
            + "      { path := "
            + lean_string(source_path)
            + "\n"
            + "        beginOffset := "
            + lean_nat(source["begin_offset"], "coverage begin_offset")
            + "\n"
            + "        endOffset := "
            + lean_nat(source["end_offset"], "coverage end_offset")
            + " }\n"
            + "    disposition := .justifiedExclusion "
            + lean_string(disposition["rule_id"])
            + " "
            + lean_string(disposition["reason"])
            + " }"
        )
    return "[\n" + ",\n".join(rendered) + "\n]"


def render_unit(
    role: str,
    unit: dict[str, Any],
    manifest: dict[str, Any],
) -> str:
    title = role.capitalize()
    prefix = role
    coverage = unit["ast_coverage"]
    entries = coverage["entries"]
    semantic_nodes = coverage["semantic_nodes"]
    lean_nat(semantic_nodes, f"{role}: semantic_nodes")
    require(
        len(entries) == semantic_nodes,
        f"{role}: entry count does not match semantic node count",
    )
    facade = manifest["parse_facade"]
    clang = manifest["clang"]
    function = unit["function"]
    body_range = function["body_range"]
    flags = unit["clang_command"][1:-1]
    require(all(type(flag) is str for flag in flags), f"{role}: compiler flags must be strings")
    require(
        all(not Path(flag).is_absolute() for flag in flags),
        f"{role}: compiler flags contain an absolute path",
    )
    unit_path = repository_path(unit["path"], f"{role}: path")
    facade_path = repository_path(facade["path"], "parse facade path")
    flags_text = "[" + ", ".join(lean_string(flag) for flag in flags) + "]"
    return f"""def {prefix}TranslationUnit : SourceArtifact :=
  {{ role := .translationUnit
    path := {lean_string(unit_path)}
    byteLength := {lean_nat(unit['byte_length'], f'{role}: byte_length')}
    sha256 := {{ hex := {lean_string(unit['sha256'])} }} }}

def {prefix}PreprocessedUnit : SourceArtifact :=
  {{ role := .preprocessedUnit
    path := {lean_string('<preprocessed:' + unit_path + '>')}
    byteLength := {lean_nat(unit['preprocessed_unit']['byte_length'], f'{role}: preprocessed byte_length')}
    sha256 := {{ hex := {lean_string(unit['preprocessed_unit']['sha256'])} }} }}

def {prefix}ParseFacade : SourceArtifact :=
  {{ role := .header
    path := {lean_string(facade_path)}
    byteLength := {lean_nat(facade['byte_length'], 'parse facade byte_length')}
    sha256 := {{ hex := {lean_string(facade['sha256'])} }} }}

def {prefix}BuildProvenance : BuildProvenance :=
  {{ frontendName := {lean_string(Path(clang['executable']).name)}
    frontendVersion := {lean_string(clang['version'])}
    targetTriple := {lean_string(target_triple(clang['version']))}
    languageStandard := "c11"
    abi := "parse-facade LP64; not an authoritative XNNPACK build"
    endianness := .little
    defines := []
    includePaths := []
    compilerFlags := {flags_text} }}

def {prefix}CoverageEntries : List CoverageEntry :=
{render_entries(entries)}

def {prefix}Coverage : CoverageManifest :=
  {{ translationUnitSha256 := {prefix}TranslationUnit.sha256
    functionName := {lean_string(function['name'])}
    functionSource :=
      {{ path := {lean_string(unit_path)}
        beginOffset := {lean_nat(body_range['begin']['offset'], f'{role}: function begin')}
        endOffset := {lean_nat(body_range['end_exclusive']['offset'], f'{role}: function end')} }}
    expectedNodeCount := {lean_nat(semantic_nodes, f'{role}: semantic_nodes')}
    entries := {prefix}CoverageEntries }}

/-- {title} audit envelope. It is internally complete but not semantic translation coverage. -/
def {prefix}Envelope : ArtifactEnvelope :=
  {{ schemaVersion := {lean_nat(manifest['schema_version'], 'schema_version')}
    operationRegistryId := "audit-only:no-semantic-registry"
    translationUnit := {prefix}TranslationUnit
    preprocessedUnit := {prefix}PreprocessedUnit
    headers := [{prefix}ParseFacade]
    build := {prefix}BuildProvenance
    extractorName := {lean_string(Path(manifest['extractor']['path']).name)}
    extractorVersion := {lean_string(manifest['extractor']['sha256'])}
    coverage := {prefix}Coverage }}
"""


def emit(manifest: dict[str, Any]) -> str:
    require(type(manifest.get("schema_version")) is int, "schema_version must be an integer")
    require(manifest.get("schema_version") == 1, "unsupported manifest schema")
    require(
        manifest.get("artifact_kind") == "saltyrn.s8-vclamp.clang-ast-audit",
        "unexpected artifact kind",
    )
    units = manifest.get("units", {})
    require(set(units) == {"source", "target"}, "manifest must contain source and target")
    repository_path(manifest["extractor"]["path"], "extractor path")
    return "\n".join(
        [
            "-- Generated by tools/emit_s8_manifest_lean.py. Do not hand-edit.",
            "import Neon2LeanDemo.Production.All",
            "",
            "namespace Neon2LeanDemo.S8VClamp.GeneratedArtifact",
            "",
            "open Neon2LeanDemo.Production",
            "",
            render_unit("source", units["source"], manifest),
            render_unit("target", units["target"], manifest),
            "end Neon2LeanDemo.S8VClamp.GeneratedArtifact",
            "",
        ]
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        output = emit(manifest)
    except (EmitError, OSError, json.JSONDecodeError, KeyError, TypeError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(output, encoding="utf-8")
    print(f"emitted Lean audit envelopes -> {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
