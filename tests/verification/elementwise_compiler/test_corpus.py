from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.corpus import (
    compile_corpus,
    discover_candidates,
)
from workflow.verification.elementwise_compiler.schema import canonical_sha256


ROOT = Path(__file__).resolve().parents[3]
pytestmark = pytest.mark.skipif(shutil.which("clang") is None, reason="Clang required")


def _tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        digest.update(path.relative_to(root).as_posix().encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def test_discovery_finds_twenty_elementwise_pairs_and_nineteen_scalar_layouts() -> None:
    candidates = discover_candidates(ROOT)

    assert len(candidates) == 20
    assert sum(not candidate.grouped_layout for candidate in candidates) == 19
    assert sum(candidate.grouped_layout for candidate in candidates) == 1
    assert all(len(candidate.outputs) == 1 for candidate in candidates)


def test_corpus_report_is_deterministic_and_tracks_real_blockers(tmp_path: Path) -> None:
    output = tmp_path / "corpus"
    first = compile_corpus(ROOT, output)
    digest = _tree_digest(output)
    shutil.rmtree(output)
    second = compile_corpus(ROOT, output)

    assert _tree_digest(output) == digest
    assert first == second
    assert first["discovered_elementwise"] == 20
    assert first["scalar_layout_scope"] == 19
    assert first["status_counts"] == {
        "counterexample": 1,
        "external-condition-missing": 7,
        "layout-unrecognized": 1,
        "spec-generated": 11,
    }
    assert first["external_condition_counts"] == {
        "not-required": 12,
        "required-missing": 8,
    }
    assert first["counterexample_count"] == 1
    assert first["schema_version"] == 2
    registry_path = output / first["intrinsic_registry"]["path"]
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    unsigned_registry = dict(registry)
    registry_sha256 = unsigned_registry.pop("registry_sha256")
    assert registry_sha256 == canonical_sha256(unsigned_registry)
    assert first["intrinsic_registry"]["sha256"] == registry_sha256
    assert len(registry["variants"]) == 184
    assert all(set(item) == {"capability"} for item in registry["variants"])
    assert all(
        program["entry_contract_preflight"] == "equal"
        for program in first["programs"]
    )
    generated = [
        program
        for program in first["programs"]
        if program["artifact_index"] is not None
    ]
    assert len(generated) == 19
    assert all(program["artifact_index"] for program in generated)
    assert all(program["manifest_sha256"] for program in generated)
    counterexample = next(
        program for program in first["programs"] if program["status"] == "counterexample"
    )
    assert counterexample["cross_phase_status"] == "lean-checked-counterexample"
    assert counterexample["counterexample"]["left_output"] != counterexample["counterexample"]["right_output"]
    assert json.loads((output / "CorpusReport.json").read_text())["report_sha256"]


def test_corpus_compiler_has_no_program_allowlist() -> None:
    source = (
        ROOT / "src/workflow/verification/elementwise_compiler/corpus.py"
    ).read_text(encoding="utf-8")

    for forbidden in (
        "f32-vmax",
        "qs8-vcvt",
        "qs8-vadd-minmax",
        "qu8-vadd-minmax",
        "s8-vclamp",
        "supported_cases",
    ):
        assert forbidden not in source
