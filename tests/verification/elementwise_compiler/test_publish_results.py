from __future__ import annotations

import json
from pathlib import Path

from workflow.verification.elementwise_compiler.publish_results import (
    publish_curated_results,
)


ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "verification/elementwise-results"


def test_checked_in_projection_has_exact_terminal_outcomes() -> None:
    report = json.loads((RESULTS / "CorpusReport.json").read_text(encoding="utf-8"))
    files = [path for path in (RESULTS / "programs").glob("*/*") if path.is_file()]

    assert len(files) == 170
    assert report["scalar_outcome_counts"] == {
        "counterexample": 10,
        "external-condition-missing": 7,
        "verified(value)": 2,
    }
    assert report["status_counts"]["layout-unrecognized"] == 1
    assert not any(path.name == "Capabilities" for path in RESULTS.rglob("*"))


def test_publisher_reproduces_checked_in_projection(tmp_path: Path) -> None:
    published = tmp_path / "results"
    result = publish_curated_results(
        RESULTS,
        published,
    )

    assert result["program_file_count"] == 170
    assert (published / "CorpusReport.json").read_bytes() == (
        RESULTS / "CorpusReport.json"
    ).read_bytes()
    assert (published / "CapabilityRegistry.json").read_bytes() == (
        RESULTS / "CapabilityRegistry.json"
    ).read_bytes()
