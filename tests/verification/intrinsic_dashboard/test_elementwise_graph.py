from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.corpus import compile_corpus
from workflow.verification.intrinsic_dashboard.elementwise_graph import (
    build_elementwise_graph,
)


ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(shutil.which("clang") is None, reason="system clang required")


def test_graph_is_derived_from_the_twenty_discovered_programs(tmp_path: Path) -> None:
    output = tmp_path / "corpus"
    compile_corpus(ROOT, output)

    graph = build_elementwise_graph(output)

    assert graph["available"] is True
    assert graph["summary"]["discovered_elementwise"] == 20
    assert graph["summary"]["scalar_layout_scope"] == 19
    assert graph["summary"]["grouped_layout_deferred"] == 1
    assert graph["summary"]["status_counts"] == {
        "generation-failed": 1,
        "intrinsic-missing": 14,
        "layout-unrecognized": 1,
        "spec-generated": 4,
    }
    generated = [item for item in graph["programs"] if item["status"] == "spec-generated"]
    assert len(generated) == 4
    assert all(item["artifacts"]["manifest"] for item in generated)
    assert all(item["claim"] == {
        "value": "spec-generated",
        "c": "not-established",
        "isa": "not-established",
    } for item in generated)

    source = (ROOT / "src/workflow/verification/intrinsic_dashboard/elementwise_graph.py").read_text(
        encoding="utf-8"
    )
    assert "supported_cases" not in source
    assert "qs8-vcvt" not in source


def test_changed_child_artifact_propagates_to_stale_program(tmp_path: Path) -> None:
    output = tmp_path / "corpus"
    report = compile_corpus(ROOT, output)
    generated = next(item for item in report["programs"] if item["status"] == "spec-generated")
    index_path = output / generated["artifact_index"]
    index = json.loads(index_path.read_text(encoding="utf-8"))
    spec_path = index_path.parent / index["spec"]["path"]
    spec_path.write_text(spec_path.read_text(encoding="utf-8") + "\n-- changed\n", encoding="utf-8")

    graph = build_elementwise_graph(output)
    node = next(item for item in graph["programs"] if item["program_id"] == generated["program_id"])
    assert node["status"] == "stale-artifact"
    assert node["status_layer"] == "artifact-integrity"
    assert node["stale"] is True
    assert all(value is False for value in node["artifacts"].values())


def test_missing_report_is_explicitly_unavailable(tmp_path: Path) -> None:
    graph = build_elementwise_graph(tmp_path)
    assert graph["available"] is False
    assert graph["programs"] == []
