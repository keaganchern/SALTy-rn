from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.corpus import compile_corpus
from workflow.verification.elementwise_compiler.compiler import CompilerRequest, compile_pair
from workflow.verification.elementwise_compiler.proof import (
    check_proof,
    prepare_proof_task,
)
from workflow.verification.elementwise_compiler.schema import canonical_json, canonical_sha256
from workflow.verification.intrinsic_dashboard.elementwise_graph import (
    build_elementwise_graph,
)


ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(
    shutil.which("clang") is None, reason="system clang required"
)


def _append_standalone_vmax(output: Path) -> dict[str, object]:
    program_root = output / "programs/heldout-vmax"
    facade = ROOT / "src/workflow/verification/lean_backend/facade/s8_vmax_example.h"
    compilation = compile_pair(
        CompilerRequest(
            ROOT,
            ROOT / "examples/s8-vmax-to-lean/neon.c",
            ROOT / "examples/s8-vmax-to-lean/rvv.c",
            "test_neon",
            "test_rvv",
            facade,
            facade,
            "aarch64-none-elf",
            "riscv64-none-elf",
            "SALT.Generated.DashboardHeldoutVMax",
            program_root,
        )
    )
    record: dict[str, object] = {
        "program_id": "heldout-vmax",
        "status": "spec-generated",
        "status_layer": "typed-generated",
        "detail": "standalone held-out fixture",
        "artifact_index": "programs/heldout-vmax/ArtifactIndex.json",
        "manifest_sha256": compilation.manifest.sha256,
        "layout_preflight": "scalar-lane",
        "schedule_preflight": "fixed-no-tail/rvv-strip-mine",
        "entry_contract_preflight": "match",
        "missing_intrinsics": [],
    }
    report_path = output / "CorpusReport.json"
    report = json.loads(report_path.read_text(encoding="utf-8"))
    report.pop("report_sha256")
    report["programs"].append(record)
    report["report_sha256"] = canonical_sha256(report)
    report_path.write_text(canonical_json(report, pretty=True), encoding="utf-8")
    return record


def test_graph_is_derived_from_the_twenty_discovered_programs(tmp_path: Path) -> None:
    output = tmp_path / "corpus"
    compile_corpus(ROOT, output)

    graph = build_elementwise_graph(output)

    assert graph["available"] is True
    assert graph["summary"]["discovered_elementwise"] == 20
    assert graph["summary"]["scalar_layout_scope"] == 19
    assert graph["summary"]["grouped_layout_deferred"] == 1
    assert graph["summary"]["status_counts"] == {
        "counterexample": 1,
        "external-condition-missing": 4,
        "intrinsic-missing": 14,
        "layout-unrecognized": 1,
    }
    generated = [
        item for item in graph["programs"] if item["artifacts"]["manifest"]
    ]
    assert len(generated) == 5
    assert all(item["artifacts"]["manifest"] for item in generated)
    assert sum(item["claim"]["value"] == "blocked" for item in generated) == 4
    assert sum(item["claim"]["value"] == "failed" for item in generated) == 1
    assert all(item["claim"]["c"] == "not-established" for item in generated)
    assert all(item["claim"]["isa"] == "not-established" for item in generated)

    source = (
        ROOT / "src/workflow/verification/intrinsic_dashboard/elementwise_graph.py"
    ).read_text(encoding="utf-8")
    assert "supported_cases" not in source
    assert "qs8-vcvt" not in source


def test_changed_child_artifact_propagates_to_stale_program(tmp_path: Path) -> None:
    output = tmp_path / "corpus"
    report = compile_corpus(ROOT, output)
    generated = next(item for item in report["programs"] if item["artifact_index"])
    index_path = output / generated["artifact_index"]
    index = json.loads(index_path.read_text(encoding="utf-8"))
    spec_path = index_path.parent / index["spec"]["path"]
    spec_path.write_text(
        spec_path.read_text(encoding="utf-8") + "\n-- changed\n", encoding="utf-8"
    )

    graph = build_elementwise_graph(output)
    node = next(
        item
        for item in graph["programs"]
        if item["program_id"] == generated["program_id"]
    )
    assert node["status"] == "stale-artifact"
    assert node["status_layer"] == "artifact-integrity"
    assert node["stale"] is True
    assert all(value is False for value in node["artifacts"].values())


def test_missing_report_is_explicitly_unavailable(tmp_path: Path) -> None:
    graph = build_elementwise_graph(tmp_path)
    assert graph["available"] is False
    assert graph["programs"] == []


@pytest.mark.skipif(shutil.which("lean") is None, reason="Lean required")
def test_frozen_task_and_checked_result_change_program_state(tmp_path: Path) -> None:
    output = tmp_path / "corpus"
    compile_corpus(ROOT, output)
    generated = _append_standalone_vmax(output)
    program_root = (output / generated["artifact_index"]).parent

    prepare_proof_task(ROOT, program_root)
    ready = build_elementwise_graph(output)
    node = next(
        item
        for item in ready["programs"]
        if item["program_id"] == generated["program_id"]
    )
    assert node["status"] == "proof-ready"
    assert node["artifacts"]["proof_task"] is True
    assert node["claim"]["value"] == "ready"

    check_proof(ROOT, program_root)
    checked = build_elementwise_graph(output)
    node = next(
        item
        for item in checked["programs"]
        if item["program_id"] == generated["program_id"]
    )
    assert node["status"] == "proof-search-failed"
    assert node["artifacts"]["result"] is True
    assert node["claim"]["value"] == "failed"
