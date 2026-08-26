from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from src.workflow.verification.intrinsic_dashboard.activity import (
    ActivityRecord,
    save_activity,
)
from src.workflow.verification.intrinsic_dashboard.audit import (
    approve_intrinsic,
    file_sha256,
)
from src.workflow.verification.intrinsic_dashboard.checks import PROOF_TARGETS
from src.workflow.verification.intrinsic_dashboard.freshness import GENERATED_CASES
from src.workflow.verification.intrinsic_dashboard.model import (
    SCHEMA_VERSION,
    AuditLedger,
    ClaimScope,
    LeanCheck,
    ProofCheckAttestation,
    ReviewChecklist,
)
from src.workflow.verification.intrinsic_dashboard.registry_status import (
    collect_registry_implementations,
)
from src.workflow.verification.intrinsic_dashboard.scanner import (
    IntrinsicUsage,
    LEXICAL_METHOD,
    LexicalInventory,
    MicrokernelProgram,
    pinned_submodule_commit,
)
from src.workflow.verification.intrinsic_dashboard.state import (
    DEFAULT_REVIEW_LEDGER_RELATIVE_PATH,
    PROFILE,
    DashboardStateError,
    build_current_ledger,
    build_dashboard_state,
    create_state_provider,
    load_kernel_families,
)


ROOT = Path(__file__).resolve().parents[3]
CATALOG = ROOT / "kernels/xnnpack-kernel-families.csv"


@pytest.fixture(scope="module")
def empty_inventory() -> LexicalInventory:
    return LexicalInventory(
        pinned_commit=pinned_submodule_commit(ROOT),
        method=LEXICAL_METHOD,
        manifests=(),
        programs=(),
        usages=(),
    )


@pytest.fixture(scope="module")
def registry_records() -> dict[str, dict[str, object]]:
    return collect_registry_implementations(ROOT)


@pytest.fixture(scope="module")
def current_build(
    empty_inventory: LexicalInventory,
    registry_records: dict[str, dict[str, object]],
):
    return build_current_ledger(
        ROOT,
        inventory=empty_inventory,
        registry_records=registry_records,
        model_freshness={case_id: True for case_id in GENERATED_CASES},
        model_freshness_sha256="f" * 64,
    )


def _checklist() -> ReviewChecklist:
    evidence_path = "tests/verification/intrinsic_dashboard/test_state.py"
    return ReviewChecklist(
        identity_signature=True,
        operand_order_types=True,
        value_semantics=True,
        fused_rounding_saturation=True,
        architectural_state=True,
        mutation_tests=True,
        evidence=(f"{evidence_path}@sha256:{file_sha256(ROOT / evidence_path)}",),
    )


def _proof_check(
    *,
    program_id: str = "qs8-vcvt",
    project_sha256: str = "a" * 64,
    checked_at: str = "2026-08-23T12:00:00Z",
) -> ProofCheckAttestation:
    return ProofCheckAttestation(
        target=PROOF_TARGETS.get(program_id, f"SALT.Generated.{program_id}.Proof"),
        project_sha256=project_sha256,
        policy_sha256="c" * 64,
        toolchain="leanprover/lean4:v4.29.0",
        status=LeanCheck.PASSED,
        checked_at=checked_at,
    )


def _write_catalog(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="ascii", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=("kernel", "type"))
        writer.writeheader()
        writer.writerows(rows)


def _catalog_rows() -> list[dict[str, str]]:
    with CATALOG.open("r", encoding="ascii", newline="") as stream:
        return list(csv.DictReader(stream))


def test_family_catalog_is_exactly_the_shared_107_rows_and_nine_types() -> None:
    families = load_kernel_families(CATALOG)

    assert len(families) == 107
    assert len({family.name for family in families}) == 107
    assert {family.category for family in families} == {
        "convolution",
        "elementwise-binary",
        "elementwise-conversion",
        "elementwise-special",
        "elementwise-unary",
        "gemm",
        "interpolation",
        "pack",
        "pooling",
    }


def test_family_catalog_rejects_duplicates_and_type_count_rewriting(
    tmp_path: Path,
) -> None:
    rows = _catalog_rows()
    duplicate_path = tmp_path / "duplicate.csv"
    rows[-1]["kernel"] = rows[0]["kernel"]
    _write_catalog(duplicate_path, rows)
    with pytest.raises(DashboardStateError, match="duplicate"):
        load_kernel_families(duplicate_path)

    rows = _catalog_rows()
    changed_type_path = tmp_path / "changed-type.csv"
    rows[0]["type"] = "pooling"
    _write_catalog(changed_type_path, rows)
    with pytest.raises(DashboardStateError, match="type counts changed"):
        load_kernel_families(changed_type_path)


def test_family_catalog_rejects_header_and_row_count_changes(tmp_path: Path) -> None:
    bad_header = tmp_path / "bad-header.csv"
    bad_header.write_text("family,type\na,gemm\n", encoding="ascii")
    with pytest.raises(DashboardStateError, match="header"):
        load_kernel_families(bad_header)

    short = tmp_path / "short.csv"
    _write_catalog(short, _catalog_rows()[:-1])
    with pytest.raises(DashboardStateError, match="exactly 107"):
        load_kernel_families(short)


def test_current_state_unions_local_calls_and_registry_without_fake_review(
    current_build,
) -> None:
    ledger, extras = current_build
    subject_ids = [intrinsic.subject_id for intrinsic in ledger.intrinsics]
    spelling_identities = {
        (intrinsic.architecture.value, intrinsic.spelling)
        for intrinsic in ledger.intrinsics
    }

    assert len(subject_ids) == len(set(subject_ids))
    assert len(subject_ids) > len(spelling_identities)
    assert all(
        intrinsic.profile == PROFILE
        for intrinsic in ledger.intrinsics
        if not intrinsic.generated
    )
    assert all(
        len(intrinsic.profile) == 64
        for intrinsic in ledger.intrinsics
        if intrinsic.generated
    )
    assert len(ledger.kernel_files) == 40
    assert all(not intrinsic.status.reviewed for intrinsic in ledger.intrinsics)
    assert len(extras["parent_git_head"]) in {40, 64}
    assert type(extras["worktree_dirty"]) is bool
    assert len(extras["worktree_status_sha256"]) == 64
    assert extras["metadata"]["repository"] == {
        "head": extras["parent_git_head"],
        "worktree_dirty": extras["worktree_dirty"],
        "worktree_status_sha256": extras["worktree_status_sha256"],
    }
    assert ("+dirty." in extras["revision"]) is extras["worktree_dirty"]

    configured = next(
        intrinsic
        for intrinsic in ledger.intrinsics
        if intrinsic.architecture.value == "neon" and intrinsic.spelling == "vld1q_s8"
    )
    assert configured.generated and configured.automated
    assert configured.semantics_sha256 is not None
    assert configured.source_sha256 != configured.semantics_sha256
    assert configured.review is None

    missing = next(
        intrinsic
        for intrinsic in ledger.intrinsics
        if intrinsic.architecture.value == "neon" and intrinsic.spelling == "vaddq_f32"
    )
    assert not missing.generated and not missing.automated
    assert missing.semantics_path is None
    assert missing.semantics_sha256 is None

    projected = extras["intrinsics"]
    neon_row = next(row for row in projected["neon"] if row["spelling"] == "vld1q_s8")
    assert neon_row["signature"]
    assert neon_row["category"]
    assert neon_row["variant_count"] == 1
    assert neon_row["reviewed_variants"] == 0
    assert isinstance(neon_row["related_programs"], list)
    assert all(isinstance(program, str) for program in neon_row["related_programs"])


def test_intrinsic_rows_and_related_programs_are_local_only(
    empty_inventory: LexicalInventory,
    registry_records: dict[str, dict[str, object]],
) -> None:
    xnnpack_only = "v_xnnpack_reference_only"
    inventory = LexicalInventory(
        pinned_commit=empty_inventory.pinned_commit,
        method=empty_inventory.method,
        manifests=("cmake/gen/neon_microkernels.cmake",),
        programs=(
            MicrokernelProgram(
                architecture="neon",
                production=True,
                family="f32-vbinary",
                path="src/f32-vbinary/gen/reference-only.c",
                manifest_path="cmake/gen/neon_microkernels.cmake",
            ),
        ),
        usages=(
            IntrinsicUsage(
                architecture="neon",
                operator=xnnpack_only,
                family="f32-vbinary",
                program_path="src/f32-vbinary/gen/reference-only.c",
                production=True,
                occurrences=1,
            ),
        ),
    )

    ledger, extras = build_current_ledger(
        ROOT,
        inventory=inventory,
        registry_records=registry_records,
        model_freshness={case_id: True for case_id in GENERATED_CASES},
        model_freshness_sha256="f" * 64,
    )

    assert all(item.spelling != xnnpack_only for item in ledger.intrinsics)
    assert all(
        path.startswith("kernels/")
        for architecture in ("neon", "rvv")
        for row in extras["intrinsics"][architecture]
        for path in row["related_programs"]
    )
    assert "40 local SALTyRN" in extras["metadata"]["scan_scope"]
    assert (
        len(extras["intrinsics"]["neon"])
        == extras["metadata"]["local"]["candidate_spellings"]["neon"]
    )
    assert (
        len(extras["intrinsics"]["rvv"])
        == extras["metadata"]["local"]["candidate_spellings"]["rvv"]
    )


def test_registry_descriptors_must_bind_unique_local_calls(
    empty_inventory: LexicalInventory,
    registry_records: dict[str, dict[str, object]],
) -> None:
    unsupported = json.loads(json.dumps(registry_records))
    unsupported_record = next(iter(unsupported.values()))
    unsupported_record["supported_cases"] = ["not-a-local-program"]
    with pytest.raises(DashboardStateError, match="not used by its local cases"):
        build_current_ledger(
            ROOT,
            inventory=empty_inventory,
            registry_records=unsupported,
        )

    duplicate = json.loads(json.dumps(registry_records))
    _original_key, original = next(iter(duplicate.items()))
    duplicate_profile = "d" * 64
    duplicate_key = f"{original['architecture']}:{original['name']}@{duplicate_profile}"
    copied = json.loads(json.dumps(original))
    copied["profile"] = duplicate_profile
    copied["variant_sha256"] = duplicate_profile
    copied["subject_id"] = duplicate_key
    duplicate[duplicate_key] = copied
    with pytest.raises(DashboardStateError, match="multiple registry descriptors"):
        build_current_ledger(
            ROOT,
            inventory=empty_inventory,
            registry_records=duplicate,
        )


def test_same_spelling_variants_are_reviewed_and_counted_independently(
    empty_inventory: LexicalInventory,
    registry_records: dict[str, dict[str, object]],
    current_build,
) -> None:
    ledger, extras = current_build
    spelling = "__riscv_vnclip_wx_i16m4"
    variant_records = [
        record for record in registry_records.values() if record["name"] == spelling
    ]
    variants = [
        intrinsic
        for intrinsic in ledger.intrinsics
        if intrinsic.architecture.value == "rvv" and intrinsic.spelling == spelling
    ]

    assert len(variant_records) == len(variants) == 4
    assert len({intrinsic.profile for intrinsic in variants}) == 4
    assert {tuple(record["supported_cases"]) for record in variant_records} == {
        ("qs8-vadd-minmax",),
        ("qs8-vcvt",),
        ("qs8-vlrelu",),
        ("qu8-vadd-minmax",),
    }
    grouped = next(
        row for row in extras["intrinsics"]["rvv"] if row["spelling"] == spelling
    )
    assert grouped["variant_count"] == 4
    assert grouped["reviewed_variants"] == 0
    assert not grouped["status"]["reviewed"]

    qu8_subject = next(
        str(record["subject_id"])
        for record in variant_records
        if record["supported_cases"] == ["qu8-vadd-minmax"]
    )
    approved = approve_intrinsic(
        next(item for item in variants if item.subject_id == qu8_subject),
        reviewer="Independent test reviewer",
        checklist=_checklist(),
        reviewed_at="2026-08-23T12:00:00Z",
    )
    rescanned, rescanned_extras = build_current_ledger(
        ROOT,
        inventory=empty_inventory,
        registry_records=registry_records,
        previous_ledger=AuditLedger(intrinsics=(approved,)),
        trusted_reviewer_ids=frozenset({"Independent test reviewer"}),
    )
    rescanned_group = next(
        row
        for row in rescanned_extras["intrinsics"]["rvv"]
        if row["spelling"] == spelling
    )
    by_program = {status.program_id: status for status in rescanned.kernel_files}

    assert rescanned_group["reviewed_variants"] == 1
    assert rescanned_group["variant_count"] == 4
    assert not rescanned_group["status"]["reviewed"]
    assert by_program["qu8-vadd-minmax"].rvv.approved == 1
    assert by_program["qs8-vadd-minmax"].rvv.approved == 0
    assert by_program["qs8-vcvt"].rvv.approved == 0
    assert by_program["qs8-vlrelu"].rvv.approved == 0


def test_kernel_rows_use_explicit_aliases_and_real_artifact_gates(
    current_build,
) -> None:
    ledger, extras = current_build
    by_program = {status.program_id: status for status in ledger.kernel_files}

    assert by_program["f32-vmax"].kernel_family == "f32-vbinary"
    assert by_program["qs8-vadd-minmax"].kernel_family == "qs8-vadd"
    assert by_program["f32-argmaxpool"].kernel_family == "f32-argmaxpool"

    assert by_program["qs8-vcvt"].spec_generated
    assert by_program["qs8-vcvt"].proof_generated
    assert by_program["qs8-vcvt"].generated_model_fresh
    assert by_program["qs8-vcvt"].claim_scope is ClaimScope.ARBITRARY_LENGTH_VALUE
    assert not by_program["qs8-vcvt"].complete_c_function_verified
    assert by_program["s8-vclamp"].spec_generated
    assert by_program["s8-vclamp"].proof_generated
    assert by_program["s8-vclamp"].claim_scope is ClaimScope.ARBITRARY_LENGTH_VALUE
    assert not by_program["s8-vclamp"].complete_c_function_verified
    assert by_program["qs8-vlrelu"].spec_generated
    assert by_program["qs8-vlrelu"].proof_generated
    assert (
        by_program["qs8-vlrelu"].claim_scope
        is ClaimScope.ARBITRARY_LENGTH_VALUE
    )
    assert not by_program["qs8-vlrelu"].complete_c_function_verified
    assert by_program["qs8-vadd-minmax"].spec_generated
    assert by_program["qs8-vadd-minmax"].proof_generated
    assert by_program["f32-vmax"].claim_scope is ClaimScope.LEXICAL_INVENTORY
    assert all(
        status.claim_scope is not ClaimScope.COMPLETE_C_FUNCTION
        for status in ledger.kernel_files
    )
    assert all(status.lean_check is LeanCheck.NOT_RUN for status in ledger.kernel_files)

    assert all(status.neon.approved == 0 for status in ledger.kernel_files)
    assert all(status.rvv.approved == 0 for status in ledger.kernel_files)
    assert by_program["qd8-f32-qc8w-gemm-minmax"].rvv.total == 0
    assert len(by_program["qs8-vcvt"].artifact_sha256) == 64

    projected = {row["program_id"]: row for row in extras["kernel_files"]}
    binding = projected["qs8-vcvt"]["artifact_binding"]
    assert projected["qs8-vcvt"]["neon_mapping"] == {"mapped": 14, "total": 14}
    assert projected["qs8-vcvt"]["rvv_mapping"] == {"mapped": 11, "total": 11}
    assert projected["s8-vclamp"]["neon_mapping"] == {"mapped": 16, "total": 16}
    assert projected["s8-vclamp"]["rvv_mapping"] == {"mapped": 5, "total": 5}
    assert all(
        row[f"{architecture}_mapping"]["mapped"]
        == row[f"{architecture}_mapping"]["total"]
        for row in projected.values()
        if row["proof_generated"]
        for architecture in ("neon", "rvv")
    )
    assert binding["source"]["sha256"]
    assert binding["target"]["sha256"]
    assert binding["contract"]["sha256"]
    assert binding["models"]["path"].endswith("/QS8VCvt/Models.lean")
    assert binding["models"]["sha256"] == file_sha256(ROOT / binding["models"]["path"])
    assert binding["generated_model_fresh"] is True
    assert binding["proof"]["sha256"]
    assert binding["proof_check"] is None
    assert projected["qs8-vcvt"]["claim_scope"] == "arbitrary-length-value"
    s8_binding = projected["s8-vclamp"]["artifact_binding"]
    assert s8_binding["contract"]["path"].endswith("/S8VClamp/Contract.lean")
    assert s8_binding["proof"]["path"].endswith("/S8VClamp/AllLengths.lean")
    assert projected["s8-vclamp"]["claim_scope"] == "arbitrary-length-value"
    vlrelu_binding = projected["qs8-vlrelu"]["artifact_binding"]
    assert vlrelu_binding["obligation"]["path"].endswith(
        "/QS8VLReLU/Obligation.lean"
    )
    assert vlrelu_binding["obligation"]["sha256"] == file_sha256(
        ROOT / vlrelu_binding["obligation"]["path"]
    )
    assert vlrelu_binding["proof"]["path"].endswith(
        "/QS8VLReLU/CandidateProof.lean"
    )
    assert projected["qs8-vlrelu"]["claim_scope"] == "arbitrary-length-value"
    qu8_binding = projected["qu8-vadd-minmax"]["artifact_binding"]
    assert qu8_binding["obligation"]["path"].endswith(
        "/QU8VAddMinmax/Obligation.lean"
    )
    assert qu8_binding["obligation"]["sha256"] == file_sha256(
        ROOT / qu8_binding["obligation"]["path"]
    )
    assert qu8_binding["proof"]["path"].endswith(
        "/QU8VAddMinmax/CandidateProof.lean"
    )
    assert projected["qu8-vadd-minmax"]["claim_scope"] == "arbitrary-length-value"
    assert not projected["qs8-vcvt"]["complete_c_function_verified"]


def test_same_spelling_does_not_unlock_an_unconfigured_local_case(
    empty_inventory: LexicalInventory,
    registry_records: dict[str, dict[str, object]],
    current_build,
) -> None:
    ledger, _ = current_build
    vld1q = next(
        item
        for item in ledger.intrinsics
        if item.architecture.value == "neon" and item.spelling == "vld1q_s8"
    )
    approved = approve_intrinsic(
        vld1q,
        reviewer="Independent test reviewer",
        checklist=_checklist(),
        reviewed_at="2026-08-23T12:00:00Z",
    )
    rescanned, extras = build_current_ledger(
        ROOT,
        inventory=empty_inventory,
        registry_records=registry_records,
        previous_ledger=AuditLedger(intrinsics=(approved,)),
        trusted_reviewer_ids=frozenset({"Independent test reviewer"}),
    )
    by_program = {status.program_id: status for status in rescanned.kernel_files}

    assert by_program["s8-vclamp"].neon.approved == 1
    assert by_program["qs8-rsum"].neon.approved == 0
    rsum = next(
        row for row in extras["kernel_files"] if row["program_id"] == "qs8-rsum"
    )
    dependency = next(
        item
        for item in rsum["artifact_binding"]["neon_dependencies"]
        if item["subject_id"].startswith("neon:vld1q_s8@")
    )
    assert dependency["subject_id"] == ("neon:vld1q_s8@local-lexical-qs8-rsum-v1")
    assert dependency["semantics_sha256"] is None


def test_persisted_review_from_untrusted_reviewer_fails_closed(
    empty_inventory: LexicalInventory,
    registry_records: dict[str, dict[str, object]],
    current_build,
) -> None:
    ledger, _ = current_build
    vld1q = next(
        item
        for item in ledger.intrinsics
        if item.architecture.value == "neon" and item.spelling == "vld1q_s8"
    )
    approved = approve_intrinsic(
        vld1q,
        reviewer="Independent test reviewer",
        checklist=_checklist(),
        reviewed_at="2026-08-23T12:00:00Z",
    )

    with pytest.raises(DashboardStateError, match="absent from the tracked authority"):
        build_current_ledger(
            ROOT,
            inventory=empty_inventory,
            registry_records=registry_records,
            previous_ledger=AuditLedger(intrinsics=(approved,)),
            trusted_reviewer_ids=frozenset({"Different reviewer"}),
        )


def test_persisted_review_with_forged_evidence_digest_fails_closed(
    empty_inventory: LexicalInventory,
    registry_records: dict[str, dict[str, object]],
    current_build,
) -> None:
    ledger, _ = current_build
    vld1q = next(
        item
        for item in ledger.intrinsics
        if item.architecture.value == "neon" and item.spelling == "vld1q_s8"
    )
    evidence_path = "tests/verification/intrinsic_dashboard/test_state.py"
    forged = ReviewChecklist(
        identity_signature=True,
        operand_order_types=True,
        value_semantics=True,
        fused_rounding_saturation=True,
        architectural_state=True,
        mutation_tests=True,
        evidence=(f"{evidence_path}@sha256:{'0' * 64}",),
    )
    approved = approve_intrinsic(
        vld1q,
        reviewer="Independent test reviewer",
        checklist=forged,
        reviewed_at="2026-08-23T12:00:00Z",
    )

    with pytest.raises(DashboardStateError, match="evidence content changed"):
        build_current_ledger(
            ROOT,
            inventory=empty_inventory,
            registry_records=registry_records,
            previous_ledger=AuditLedger(intrinsics=(approved,)),
            trusted_reviewer_ids=frozenset({"Independent test reviewer"}),
        )


def test_kernel_artifact_binds_exact_review_attestation_not_only_count(
    empty_inventory: LexicalInventory,
    registry_records: dict[str, dict[str, object]],
    current_build,
) -> None:
    ledger, _ = current_build
    vld1q = next(
        item
        for item in ledger.intrinsics
        if item.architecture.value == "neon" and item.spelling == "vld1q_s8"
    )
    first_review = approve_intrinsic(
        vld1q,
        reviewer="Independent reviewer A",
        checklist=_checklist(),
        reviewed_at="2026-08-23T12:00:00Z",
        note="first attestation",
    )
    second_review = approve_intrinsic(
        vld1q,
        reviewer="Independent reviewer B",
        checklist=_checklist(),
        reviewed_at="2026-08-23T12:01:00Z",
        note="replacement attestation",
    )

    first, _ = build_current_ledger(
        ROOT,
        inventory=empty_inventory,
        registry_records=registry_records,
        previous_ledger=AuditLedger(intrinsics=(first_review,)),
        trusted_reviewer_ids=frozenset({"Independent reviewer A"}),
    )
    second, _ = build_current_ledger(
        ROOT,
        inventory=empty_inventory,
        registry_records=registry_records,
        previous_ledger=AuditLedger(intrinsics=(second_review,)),
        trusted_reviewer_ids=frozenset({"Independent reviewer B"}),
    )
    first_status = next(
        item for item in first.kernel_files if item.program_id == "s8-vclamp"
    )
    second_status = next(
        item for item in second.kernel_files if item.program_id == "s8-vclamp"
    )

    assert first_status.neon.approved == second_status.neon.approved == 1
    assert first_status.artifact_sha256 != second_status.artifact_sha256


def test_changed_descriptor_hash_makes_review_stale_and_removes_numerator(
    empty_inventory: LexicalInventory,
    registry_records: dict[str, dict[str, object]],
    current_build,
) -> None:
    ledger, _ = current_build
    vld1q = next(
        item
        for item in ledger.intrinsics
        if item.architecture.value == "neon" and item.spelling == "vld1q_s8"
    )
    approved = approve_intrinsic(
        vld1q,
        reviewer="Independent test reviewer",
        checklist=_checklist(),
        reviewed_at="2026-08-23T12:00:00Z",
    )
    changed_registry = {key: dict(value) for key, value in registry_records.items()}
    changed_registry[vld1q.subject_id]["source_sha256"] = canonical_digest = (
        "0" * 64 if vld1q.source_sha256 != "0" * 64 else "1" * 64
    )
    assert canonical_digest != vld1q.source_sha256

    rescanned, _ = build_current_ledger(
        ROOT,
        inventory=empty_inventory,
        registry_records=changed_registry,
        previous_ledger=AuditLedger(intrinsics=(approved,)),
        trusted_reviewer_ids=frozenset({"Independent test reviewer"}),
    )
    current_vld1q = next(
        item
        for item in rescanned.intrinsics
        if item.architecture.value == "neon" and item.spelling == "vld1q_s8"
    )
    s8 = next(
        status for status in rescanned.kernel_files if status.program_id == "s8-vclamp"
    )
    assert current_vld1q.status.stale
    assert not current_vld1q.status.reviewed
    assert s8.neon.approved == 0


def test_lean_check_is_explicit_and_never_inferred_from_proof_presence(
    empty_inventory: LexicalInventory,
    registry_records: dict[str, dict[str, object]],
    current_build,
) -> None:
    proof_check = _proof_check()
    ledger, extras = build_current_ledger(
        ROOT,
        inventory=empty_inventory,
        registry_records=registry_records,
        lean_checks={"qs8-vcvt": proof_check},
    )
    by_program = {status.program_id: status for status in ledger.kernel_files}
    baseline = {status.program_id: status for status in current_build[0].kernel_files}
    projected = {row["program_id"]: row for row in extras["kernel_files"]}

    assert by_program["qs8-vcvt"].lean_check is LeanCheck.PASSED
    assert by_program["qs8-vcvt"].proof_check == proof_check
    assert by_program["qs8-vcvt"].artifact_sha256 != (
        baseline["qs8-vcvt"].artifact_sha256
    )
    assert projected["qs8-vcvt"]["artifact_binding"]["proof_check"] == (
        proof_check.to_dict()
    )
    assert projected["qs8-vcvt"]["proof_check_sha256"] == (proof_check.binding_sha256)
    assert by_program["s8-vclamp"].lean_check is LeanCheck.NOT_RUN

    changed_project, _ = build_current_ledger(
        ROOT,
        inventory=empty_inventory,
        registry_records=registry_records,
        lean_checks={
            "qs8-vcvt": _proof_check(project_sha256="b" * 64),
        },
    )
    changed_status = next(
        status
        for status in changed_project.kernel_files
        if status.program_id == "qs8-vcvt"
    )
    assert changed_status.artifact_sha256 != by_program["qs8-vcvt"].artifact_sha256

    with pytest.raises(DashboardStateError, match="unknown local programs"):
        build_current_ledger(
            ROOT,
            inventory=empty_inventory,
            registry_records=registry_records,
            lean_checks={"not-a-program": _proof_check(program_id="not-a-program")},
        )
    with pytest.raises(DashboardStateError, match="without a proof artifact"):
        build_current_ledger(
            ROOT,
            inventory=empty_inventory,
            registry_records=registry_records,
            lean_checks={"f32-vmax": _proof_check(program_id="f32-vmax")},
        )
    with pytest.raises(DashboardStateError, match="proof-check attestations"):
        build_current_ledger(
            ROOT,
            inventory=empty_inventory,
            registry_records=registry_records,
            lean_checks={"qs8-vcvt": LeanCheck.PASSED},  # type: ignore[dict-item]
        )
    wrong_target = ProofCheckAttestation(
        target="SALT.Generated.Wrong.Proof",
        project_sha256="a" * 64,
        policy_sha256="c" * 64,
        toolchain="leanprover/lean4:v4.29.0",
        status=LeanCheck.PASSED,
        checked_at="2026-08-23T12:00:00Z",
    )
    with pytest.raises(DashboardStateError, match="configured proof module"):
        build_current_ledger(
            ROOT,
            inventory=empty_inventory,
            registry_records=registry_records,
            lean_checks={"qs8-vcvt": wrong_target},
        )


def test_dashboard_state_is_json_serializable_and_reads_agent_activity(
    tmp_path: Path,
    empty_inventory: LexicalInventory,
    registry_records: dict[str, dict[str, object]],
) -> None:
    activity = tmp_path / "activity"
    save_activity(
        activity,
        ActivityRecord(
            agent_id="reviewer-1",
            name="Reviewer 1",
            status="running",
            task="Audit exact intrinsic semantics",
            current_item="neon:vmaxq_s8",
            completed=1,
            total=3,
        ),
    )
    state = build_dashboard_state(
        ROOT,
        inventory=empty_inventory,
        registry_records=registry_records,
        activity_directory=activity,
        review_ledger_path=tmp_path / "reviews-does-not-exist.json",
    )

    assert state["generated_at"].endswith("Z")
    assert state["agents"][0]["id"] == "reviewer-1"
    assert state["metadata"]["scan_method"] == LEXICAL_METHOD
    assert state["metadata"]["limitations"]
    assert SCHEMA_VERSION == 2
    assert state["schema_version"] == SCHEMA_VERSION
    assert set(state["metadata"]["repository"]) == {
        "head",
        "worktree_dirty",
        "worktree_status_sha256",
    }
    assert state["intrinsics"]["neon"]
    assert state["kernel_files"]
    assert "ledger" not in state
    assert "file_unlocks" not in state
    json.dumps(state, ensure_ascii=True)


def test_local_provider_does_not_scan_xnnpack_and_rebuilds_live_state(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    def unexpected_rescan(*_args, **_kwargs):
        raise AssertionError("local dashboard attempted an XNNPACK source scan")

    monkeypatch.setattr(
        "src.workflow.verification.intrinsic_dashboard.scanner.scan_pinned_xnnpack",
        unexpected_rescan,
    )
    provider = create_state_provider(
        ROOT,
        review_ledger_path=tmp_path / DEFAULT_REVIEW_LEDGER_RELATIVE_PATH,
        activity_directory=tmp_path / "activity",
    )
    first = provider()
    save_activity(
        tmp_path / "activity",
        ActivityRecord(
            agent_id="agent-live",
            name="Live agent",
            status="running",
            task="Add one mapping",
            completed=0,
            total=1,
        ),
    )
    second = provider()
    current_ledger = provider.current_ledger()

    assert first["agents"] == []
    assert first["metadata"]["generated_models"] == {
        "fresh": 5,
        "total": 5,
        "method": "deterministic-in-memory-regeneration-and-byte-comparison",
        "binding_sha256": provider._generation_watch_sha256,
    }
    selected_rows = [
        row
        for row in first["kernel_files"]
        if row["claim_scope"] == "selected-local-block"
    ]
    arbitrary_length_rows = [
        row
        for row in first["kernel_files"]
        if row["claim_scope"] == "arbitrary-length-value"
    ]
    assert len(selected_rows) == 1
    assert all(row["generated_model_fresh"] for row in selected_rows)
    assert {row["program_id"] for row in arbitrary_length_rows} == {
        "s8-vclamp",
        "qs8-vcvt",
        "qs8-vlrelu",
        "qu8-vadd-minmax",
    }
    assert all(row["generated_model_fresh"] for row in arbitrary_length_rows)
    assert second["agents"][0]["id"] == "agent-live"
    assert first["revision"] == second["revision"]
    assert len(current_ledger.kernel_files) == 40


def test_cache_provider_invalidates_generated_model_freshness(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    empty_inventory: LexicalInventory,
) -> None:
    watched = {"digest": "a" * 64}
    check_calls = []

    def watch_digest(*_args, **_kwargs):
        return watched["digest"]

    def check_models(*_args, **_kwargs):
        check_calls.append(watched["digest"])
        fresh = watched["digest"] == "a" * 64
        return {case_id: fresh for case_id in GENERATED_CASES}

    monkeypatch.setattr(
        "src.workflow.verification.intrinsic_dashboard.state.generation_watch_digest",
        watch_digest,
    )
    monkeypatch.setattr(
        "src.workflow.verification.intrinsic_dashboard.state.check_generated_models",
        check_models,
    )
    provider = create_state_provider(
        ROOT,
        inventory=empty_inventory,
        review_ledger_path=tmp_path / DEFAULT_REVIEW_LEDGER_RELATIVE_PATH,
        activity_directory=tmp_path / "activity",
    )

    fresh = provider()
    watched["digest"] = "b" * 64
    stale = provider()

    assert check_calls == ["a" * 64, "b" * 64]
    assert fresh["metadata"]["generated_models"]["fresh"] == 5
    assert stale["metadata"]["generated_models"]["fresh"] == 0
    assert fresh["metadata"]["generated_models"]["binding_sha256"] == "a" * 64
    assert stale["metadata"]["generated_models"]["binding_sha256"] == "b" * 64
    stale_selected = [
        row
        for row in stale["kernel_files"]
        if row["claim_scope"] == "selected-local-block"
    ]
    assert all(not row["generated_model_fresh"] for row in stale_selected)


def test_generated_model_binding_digest_changes_kernel_artifact(
    empty_inventory: LexicalInventory,
    registry_records: dict[str, dict[str, object]],
) -> None:
    freshness = {case_id: True for case_id in GENERATED_CASES}
    first, _ = build_current_ledger(
        ROOT,
        inventory=empty_inventory,
        registry_records=registry_records,
        model_freshness=freshness,
        model_freshness_sha256="a" * 64,
    )
    second, _ = build_current_ledger(
        ROOT,
        inventory=empty_inventory,
        registry_records=registry_records,
        model_freshness=freshness,
        model_freshness_sha256="b" * 64,
    )
    first_status = next(
        item for item in first.kernel_files if item.program_id == "qs8-vcvt"
    )
    second_status = next(
        item for item in second.kernel_files if item.program_id == "qs8-vcvt"
    )

    assert first_status.artifact_sha256 != second_status.artifact_sha256
