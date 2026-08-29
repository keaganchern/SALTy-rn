from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess

import pytest

from src.workflow.verification.intrinsic_dashboard.registry_status import (
    collect_registry_implementations,
)
from src.workflow.verification.intrinsic_dashboard.scanner import (
    LEXICAL_METHOD,
    LexicalInventory,
    pinned_submodule_commit,
)
from src.workflow.verification.intrinsic_dashboard.state import build_dashboard_state


ROOT = Path(__file__).resolve().parents[3]
WEB = ROOT / "src/workflow/verification/intrinsic_dashboard/web"


NODE_NORMALIZER = r"""
const fs = require("fs");
const vm = require("vm");
const elements = new Map();
function element(selector) {
  if (!elements.has(selector)) {
    elements.set(selector, {
      addEventListener() {}, removeAttribute() {}, scrollIntoView() {},
      className: "", textContent: "", innerHTML: "", hidden: false,
      disabled: false, title: "", value: "",
    });
  }
  return elements.get(selector);
}
const context = {
  AbortController,
  Date,
  Intl,
  console,
  document: {
    querySelector: element,
    addEventListener() {},
    visibilityState: "hidden",
  },
  fetch() { return new Promise(() => {}); },
  window: {
    addEventListener() {},
    clearTimeout() {},
    setTimeout() { return 0; },
  },
};
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[1], "utf8"), context);
context.payload = JSON.parse(process.argv[2]);
const normalized = vm.runInContext("normalizeState(payload)", context);
context.normalized = normalized;
const result = vm.runInContext(process.argv[3], context);
process.stdout.write(JSON.stringify(result));
"""


def _evaluate(payload: dict[str, object], expression: str) -> object:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node.js is required for the frontend schema test")
    complete_payload = {"metadata": {"test": True}, **payload}
    completed = subprocess.run(
        [
            node,
            "-e",
            NODE_NORMALIZER,
            str(WEB / "app.js"),
            json.dumps(complete_payload),
            expression,
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    return json.loads(completed.stdout)


def _normalize(payload: dict[str, object]) -> dict[str, object]:
    result = _evaluate(payload, "normalized")
    assert isinstance(result, dict)
    return result


def _variant(reviewed: bool = False) -> dict[str, object]:
    return {
        "subject_id": "neon:vaddq_s8@i8x16",
        "profile": "i8x16",
        "signature": "i8x16(i8x16,i8x16)",
        "category": "binary",
        "lean_target": "SALT.Intrinsics.Neon.vaddq_s8",
        "lowering_operation": "add",
        "descriptor_paths": ["src/workflow/verification/lean_backend/registry.py"],
        "implementation_paths": ["src/verification_bw/lean/SALT/Intrinsics/Neon.lean"],
        "supported_cases": ["s8-demo"],
        "source_sha256": "a" * 64,
        "semantics_sha256": "b" * 64,
        "review_state": "reviewed" if reviewed else "not-reviewed",
        "reviewer": "Independent reviewer" if reviewed else None,
        "reviewed_at": "2026-08-23T12:00:00Z" if reviewed else None,
        "evidence": [f"tests/evidence.md@sha256:{'c' * 64}"] if reviewed else [],
    }


def _intrinsic(reviewed: bool = False) -> dict[str, object]:
    variant = _variant(reviewed)
    return {
        "id": "neon:vaddq_s8",
        "architecture": "neon",
        "spelling": "vaddq_s8",
        "variant_count": 1,
        "reviewed_variants": 1 if reviewed else 0,
        "stale_variants": 0,
        "subject_ids": [variant["subject_id"]],
        "signatures": [variant["signature"]],
        "signature": variant["signature"],
        "category": "binary",
        "implementation_paths": variant["implementation_paths"],
        "supported_cases": ["s8-demo"],
        "coverage_scope": "case-scoped",
        "status": {
            "generated": True,
            "automated": True,
            "reviewed": reviewed,
            "stale": False,
        },
        "related_kernel_families": ["s8-demo"],
        "variant_summaries": [variant],
        "related_programs": ["kernels/source/s8-demo.c"],
    }


def _kernel_with_proof_check(include_attestation: bool) -> dict[str, object]:
    binding = "c" * 64
    return {
        "kernel_family": "s8-demo",
        "program_id": "s8-demo",
        "source_path": "kernels/source/s8-demo.c",
        "artifact_sha256": "d" * 64,
        "review_subject_sha256": "a" * 64,
        "author": "Backend maintainers",
        "claim_scope": "selected-local-block",
        "neon": {"approved": 1, "total": 1},
        "rvv": {"approved": 1, "total": 1},
        "neon_mapping": {"mapped": 1, "total": 1},
        "rvv_mapping": {"mapped": 1, "total": 1},
        "generated_model_fresh": True,
        "spec_generated": True,
        "proof_generated": True,
        "lean_check": "passed",
        "proof_check_sha256": binding if include_attestation else None,
        "proof_check": (
            {
                "target": "SALT.Generated.S8Demo.Proof",
                "project_sha256": "e" * 64,
                "policy_sha256": "f" * 64,
                "toolchain": "leanprover/lean4:v4.19.0",
                "status": "passed",
                "checked_at": "2026-08-23T12:00:00Z",
                "binding_sha256": binding,
            }
            if include_attestation
            else None
        ),
        "final_reviewed": False,
        "final_review_stale": False,
        "complete_c_function_verified": False,
        "final_review": None,
    }


def test_frontend_sorts_passing_kernel_proofs_first() -> None:
    unchecked = _kernel_with_proof_check(False)
    unchecked["program_id"] = "a-unchecked"
    unchecked["lean_check"] = "not-run"
    checked = _kernel_with_proof_check(True)
    checked["program_id"] = "z-checked"
    result = _normalize(
        {
            "schema_version": 2,
            "revision": "test",
            "generated_at": "2026-08-23T12:00:00Z",
            "agents": [],
            "intrinsics": {"neon": [], "rvv": []},
            "kernel_files": [unchecked, checked],
        }
    )
    assert [item["programId"] for item in result["files"]] == [
        "z-checked",
        "a-unchecked",
    ]


def test_frontend_consumes_only_the_authoritative_projection() -> None:
    script = (WEB / "app.js").read_text(encoding="utf-8")

    assert "raw.schema_version === 2" in script
    assert "asObject(raw.intrinsics)" in script
    assert "asArray(raw.kernel_files)" in script
    assert 'const fields = ["generated", "automated", "reviewed", "stale"]' in script
    assert "statusFlags.reviewed === allVariantsReviewed" in script
    assert "reviewedVariants === countedReviewed" in script
    assert "variant_summaries" in script
    assert "variant.reviewState" in script
    assert '"Case-scoped"' in script

    for legacy_field in (
        "workflow_status",
        "pending_review",
        "file_unlocks",
        "raw.ledger",
        "const neonRecords = raw.neon",
        "const fileRecords = raw.files",
    ):
        assert legacy_field not in script


def test_elementwise_frontend_uses_exact_schema_v3_artifact_graph_fields() -> None:
    script = (WEB / "elementwise.js").read_text(encoding="utf-8")
    html = (WEB / "index.html").read_text(encoding="utf-8")

    assert "payload.schema_version !== 3" in script
    for artifact in (
        "manifest",
        "external_condition",
        "models",
        "spec",
        "cross_phase_audit",
        "counterexample",
        "proof_task",
        "result",
    ):
        assert f'"{artifact}"' in script
    assert "input condition blocked" in script
    assert "checked counterexample" in script
    assert "program.input_condition" in script
    assert "program.cross_phase" in script
    assert "condition.scope" in script
    assert "phase.trial_count" in script
    assert "program.counterexample" in script
    assert "payload.capabilities" in script
    assert "capability.defined" in script
    assert "capability.lean_checked" in script
    assert "capability.independently_reviewed" in script
    assert "capability.review_sha256" in script
    assert "capability.id" in script
    assert "capability.function_type" in script
    assert "capability.used" in script
    assert "reviewed_registry_intrinsic_variants" in script
    assert "reviewed_used_intrinsic_variants" in script
    assert "Reusable intrinsic pieces" in html
    for witness_field in (
        "counterexample.claim",
        "counterexample.parameters",
        "counterexample.inputs",
        "counterexample.left_output",
        "counterexample.right_output",
    ):
        assert witness_field in script
    assert "Legacy proof prototypes" in html
    assert "not the authority for element-wise compiler status" in html


def test_group_approval_requires_exact_aggregate_status_and_variant_counts() -> None:
    approved = _intrinsic(reviewed=True)
    state = _normalize(
        {
            "schema_version": 2,
            "revision": "test",
            "generated_at": "2026-08-23T12:00:00Z",
            "agents": [],
            "intrinsics": {"neon": [approved], "rvv": []},
            "kernel_files": [],
        }
    )
    assert state["neon"][0]["status"] == "approved"

    malformed = _intrinsic(reviewed=True)
    malformed["reviewed_variants"] = 0
    malformed["approved"] = True
    malformed["workflow-status"] = "approved"
    state = _normalize(
        {
            "schema_version": 2,
            "revision": "test",
            "generated_at": "2026-08-23T12:00:00Z",
            "agents": [],
            "intrinsics": {"neon": [malformed], "rvv": []},
            "kernel_files": [],
        }
    )
    assert state["neon"][0]["status"] == "missing"
    assert state["neon"][0]["statusLabel"] == "Invalid data"


def test_duplicate_variant_summary_cannot_satisfy_two_declared_subjects() -> None:
    malformed = _intrinsic(reviewed=True)
    first = _variant(reviewed=True)
    second_subject = "neon:vaddq_s8@second-profile"
    malformed["variant_count"] = 2
    malformed["reviewed_variants"] = 2
    malformed["subject_ids"] = [first["subject_id"], second_subject]
    malformed["variant_summaries"] = [first, dict(first)]

    state = _normalize(
        {
            "schema_version": 2,
            "revision": "test",
            "generated_at": "2026-08-23T12:00:00Z",
            "agents": [],
            "intrinsics": {"neon": [malformed], "rvv": []},
            "kernel_files": [],
        }
    )

    assert state["neon"][0]["status"] == "missing"
    assert state["neon"][0]["statusLabel"] == "Invalid data"


def test_legacy_top_level_arrays_are_not_accepted() -> None:
    state = _normalize(
        {
            "schema_version": 2,
            "revision": "test",
            "generated_at": "2026-08-23T12:00:00Z",
            "agents": [],
            "neon": [_intrinsic(reviewed=True)],
            "files": [{"status": "approved"}],
        }
    )
    assert state["neon"] == []
    assert state["rvv"] == []
    assert state["files"] == []
    assert state["valid"] is False


def test_incompatible_global_schema_is_not_treated_as_a_live_empty_state() -> None:
    state = _normalize(
        {
            "schema_version": 99,
            "revision": "test",
            "generated_at": "2026-08-23T12:00:00Z",
            "agents": [],
            "intrinsics": {"neon": [], "rvv": []},
            "kernel_files": [],
        }
    )

    assert state["valid"] is False
    assert state["error"] == "incompatible or incomplete API schema"


def test_passed_string_without_proof_check_attestation_fails_closed() -> None:
    payload = {
        "schema_version": 2,
        "revision": "test",
        "generated_at": "2026-08-23T12:00:00Z",
        "agents": [],
        "intrinsics": {"neon": [], "rvv": []},
        "kernel_files": [_kernel_with_proof_check(False)],
    }
    without_attestation = _normalize(payload)["files"][0]
    assert without_attestation["schemaValid"] is False
    assert without_attestation["leanCheck"] == "not-run"
    assert without_attestation["status"] == "missing"

    payload["kernel_files"] = [_kernel_with_proof_check(True)]
    with_attestation = _normalize(payload)["files"][0]
    assert with_attestation["schemaValid"] is True
    assert with_attestation["leanCheck"] == "passed"
    assert with_attestation["status"] == "pending"


def test_stale_generated_model_locks_scope_review() -> None:
    row = _kernel_with_proof_check(True)
    row["generated_model_fresh"] = False
    normalized = _normalize(
        {
            "schema_version": 2,
            "revision": "test",
            "generated_at": "2026-08-23T12:00:00Z",
            "agents": [],
            "intrinsics": {"neon": [], "rvv": []},
            "kernel_files": [row],
        }
    )["files"][0]

    assert normalized["schemaValid"] is True
    assert normalized["status"] == "generated"
    assert "Fresh generated model" in normalized["missing"]


def test_current_final_review_must_bind_the_projected_review_subject() -> None:
    row = _kernel_with_proof_check(True)
    row["final_reviewed"] = True
    row["final_review"] = {
        "status_sha256": "0" * 64,
        "author": row["author"],
        "reviewer": "Independent reviewer",
        "reviewed_at": "2026-08-23T12:00:00Z",
        "evidence": [f"notes/review.md@sha256:{'1' * 64}"],
        "note": "reviewed",
    }
    normalized = _normalize(
        {
            "schema_version": 2,
            "revision": "test",
            "generated_at": "2026-08-23T12:00:00Z",
            "agents": [],
            "intrinsics": {"neon": [], "rvv": []},
            "kernel_files": [row],
        }
    )["files"][0]

    assert normalized["schemaValid"] is False
    assert normalized["finalReviewed"] is False

    row["final_review"]["status_sha256"] = row["review_subject_sha256"]
    current = _normalize(
        {
            "schema_version": 2,
            "revision": "test",
            "generated_at": "2026-08-23T12:00:00Z",
            "agents": [],
            "intrinsics": {"neon": [], "rvv": []},
            "kernel_files": [row],
        }
    )["files"][0]
    assert current["schemaValid"] is True
    assert current["status"] == "approved"


def test_current_backend_projection_is_accepted_without_synthesized_approval(
    tmp_path: Path,
) -> None:
    inventory = LexicalInventory(
        pinned_commit=pinned_submodule_commit(ROOT),
        method=LEXICAL_METHOD,
        manifests=(),
        programs=(),
        usages=(),
    )
    state = build_dashboard_state(
        ROOT,
        inventory=inventory,
        registry_records=collect_registry_implementations(ROOT),
        review_ledger_path=tmp_path / "no-reviews.json",
        activity_directory=tmp_path / "activity",
    )

    normalized = _normalize(state)

    assert normalized["neon"]
    assert normalized["rvv"]
    assert len(normalized["files"]) == 40
    assert all(row["statusLabel"] == "" for row in normalized["neon"])
    assert all(row["statusLabel"] == "" for row in normalized["rvv"])
    assert all(row["status"] != "approved" for row in normalized["neon"])
    assert all(row["status"] != "approved" for row in normalized["rvv"])
    assert all(row["schemaValid"] for row in normalized["files"])


def test_kernel_table_names_and_displays_explicit_claim_scopes() -> None:
    page = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "app.js").read_text(encoding="utf-8")

    assert "Legacy proof prototypes" in page
    assert "not the authority for element-wise compiler status" in page
    assert "Scope review" in page
    assert "File unlocks" not in page
    assert "claim_scope" in script
    assert "selected-local-block" in script
    assert "arbitrary-length-value" in script
    assert "complete_c_function_verified" in script
    assert "C verified" not in page
    assert "C verified" not in script


def test_kernel_counts_separate_arbitrary_length_from_local_blocks() -> None:
    rows = []
    for index in range(5):
        row = _kernel_with_proof_check(True)
        row["program_id"] = f"case-{index}"
        if index == 0:
            row["claim_scope"] = "arbitrary-length-value"
        rows.append(row)
    payload = {
        "schema_version": 2,
        "revision": "test",
        "generated_at": "2026-08-23T12:00:00Z",
        "agents": [],
        "intrinsics": {"neon": [], "rvv": []},
        "kernel_files": rows,
    }

    assert _evaluate(payload, "proofLayerCounts(normalized.files)") == {
        "total": 5,
        "local": 5,
        "arbitrary": 1,
        "completeC": 0,
    }

    rows[0]["lean_check"] = "not-run"
    rows[0]["proof_check_sha256"] = None
    rows[0]["proof_check"] = None
    assert _evaluate(payload, "proofLayerCounts(normalized.files)") == {
        "total": 5,
        "local": 4,
        "arbitrary": 0,
        "completeC": 0,
    }

    failed = _kernel_with_proof_check(True)
    failed["program_id"] = "case-0"
    failed["claim_scope"] = "arbitrary-length-value"
    failed["lean_check"] = "failed"
    failed["proof_check"]["status"] = "failed"
    rows[0] = failed
    assert _evaluate(payload, "proofLayerCounts(normalized.files)") == {
        "total": 5,
        "local": 4,
        "arbitrary": 0,
        "completeC": 0,
    }


def test_related_programs_remain_the_last_intrinsic_column() -> None:
    page = (WEB / "index.html").read_text(encoding="utf-8")
    neon_header = page.split('<tbody id="neon-body">', 1)[0]
    rvv_section = page.split('<tbody id="neon-body">', 1)[1]
    rvv_header = rvv_section.split('<tbody id="rvv-body">', 1)[0]

    assert neon_header.rfind("Local SALTyRN programs") > neon_header.rfind("Review")
    assert rvv_header.rfind("Local SALTyRN programs") > rvv_header.rfind("Review")
    assert "data-disclosure-key" in (WEB / "app.js").read_text(encoding="utf-8")
    assert "Signature / profile" not in page


def test_kernel_gate_labels_separate_semantic_review_from_lean_check() -> None:
    page = (WEB / "index.html").read_text(encoding="utf-8")
    script = (WEB / "app.js").read_text(encoding="utf-8")

    assert "Neon mapping / review" in page
    assert "RVV mapping / review" in page
    assert "Contract / spec" in page
    assert "Lean proof file" in page
    assert "Lean theorem check" in page
    assert "Review pending" in script
    assert "remaining" not in script
    assert "Unscoped" not in script
    assert "Target missing" in script
    assert "No RVV calls" in script
    assert "Mapped" in script
    assert "Reviewed" in script


def test_kernel_table_keeps_the_requested_eight_columns() -> None:
    page = (WEB / "index.html").read_text(encoding="utf-8")
    table = page.split('<table class="files-table">', 1)[1].split("</thead>", 1)[0]

    assert table.count('<th scope="col">') == 8


def test_polling_skips_table_replacement_when_verified_content_is_unchanged() -> None:
    script = (WEB / "app.js").read_text(encoding="utf-8")
    payload = {
        "schema_version": 2,
        "revision": "test",
        "generated_at": "2026-08-23T12:00:00Z",
        "agents": [{"id": "one", "status": "running"}],
        "intrinsics": {"neon": [], "rvv": []},
        "kernel_files": [],
    }
    before = _evaluate(payload, "tableStateRenderKey(normalized)")
    payload["agents"] = [{"id": "one", "status": "completed"}]
    after = _evaluate(payload, "tableStateRenderKey(normalized)")

    assert before == after
    assert "function tableStateRenderKey(state)" in script
    assert (
        "const shouldRenderTables = nextTableRenderKey !== app.tableRenderKey" in script
    )
    assert "captureTableInteraction" in script
    assert "restoreTableInteraction" in script
    assert "if (!normalized.valid) throw new Error(normalized.error)" in script
    assert "Showing the last verified response." in script
