from __future__ import annotations

import copy

import pytest

from workflow.verification.elementwise_compiler.schema import (
    BOOL,
    SIZE_T,
    Architecture,
    ArtifactKind,
    CapabilityRef,
    ContractBinding,
    ContractExpr,
    ContractOp,
    ElementwiseSchemaError,
    EntryContract,
    GeneratedArtifact,
    LayoutInstance,
    LocalAssertionFact,
    ProgramManifest,
    ProofTask,
    Result,
    ResultStatus,
    ScheduleInstance,
    SourceArtifact,
    canonical_sha256,
)


D = "0" * 64
E = "1" * 64
F = "2" * 64


def _entry_contract() -> EntryContract:
    batch = ContractExpr.variable("batch", SIZE_T)
    nonzero = ContractExpr.make(ContractOp.NE, batch, ContractExpr.integer(0))
    aligned = ContractExpr.make(
        ContractOp.EQ,
        ContractExpr.make(ContractOp.MOD, batch, ContractExpr.sizeof("int8_t")),
        ContractExpr.integer(0),
    )
    return EntryContract.normalized((aligned, nonzero))


def _manifest() -> ProgramManifest:
    source = SourceArtifact(Architecture.NEON, "kernels/source/a.c", "left", D, "facade/a.h", E, F)
    target = SourceArtifact(Architecture.RVV, "kernels/target/b.c", "right", E, "facade/b.h", F, D)
    contract = _entry_contract()
    intrinsic = CapabilityRef("intrinsic:vmax:s8", 1, D)
    layout_capability = CapabilityRef("layout:scalar-lane", 1, E)
    schedule_capability = CapabilityRef("schedule:fixed-tail", 1, F)
    layout = LayoutInstance(
        layout_capability,
        (("input", "int8_t"), ("output", "int8_t")),
        ("input",),
        ("output",),
    )
    schedules = (
        ScheduleInstance(Architecture.NEON, schedule_capability, (("lanes", 8),), D),
        ScheduleInstance(Architecture.RVV, CapabilityRef("schedule:rvv-stripmine", 1, D), (("sew", 8),), E),
    )
    assertion = LocalAssertionFact(
        Architecture.NEON,
        "control_0001",
        ContractExpr.make(
            ContractOp.LE,
            ContractExpr.variable("batch", SIZE_T),
            ContractExpr.integer(7),
        ),
        "fixed-tail-remainder",
        F,
    )
    return ProgramManifest(
        compiler_sha256=D,
        sources=(source, target),
        contracts=ContractBinding(contract, contract),
        intrinsic_capabilities=(intrinsic,),
        layout=layout,
        schedules=schedules,
        local_assertions=(assertion,),
        consumed_effects_sha256=E,
    )


def test_contract_normalization_is_order_independent_and_typed() -> None:
    first = _entry_contract()
    second = EntryContract.normalized(tuple(reversed(first.clauses)))
    assert first == second
    assert first.sha256 == second.sha256
    with pytest.raises(ElementwiseSchemaError, match="boolean"):
        EntryContract.normalized((ContractExpr.integer(1),))


def test_contract_binding_rejects_unequal_entry_domains() -> None:
    contract = _entry_contract()
    different = EntryContract.normalized(
        (
            ContractExpr.make(
                ContractOp.NE,
                ContractExpr.variable("batch", SIZE_T),
                ContractExpr.integer(0),
            ),
        )
    )
    with pytest.raises(ElementwiseSchemaError, match="entry contracts differ"):
        ContractBinding(contract, different)


def test_manifest_round_trip_is_strict_and_content_addressed() -> None:
    manifest = _manifest()
    record = manifest.to_record()
    assert ProgramManifest.from_record(record) == manifest
    assert len(manifest.sha256) == 64

    changed = copy.deepcopy(record)
    changed["layout"]["stream_c_types"][0]["c_type"] = "uint8_t"
    with pytest.raises(ElementwiseSchemaError, match="digest disagrees"):
        ProgramManifest.from_record(changed)

    extra = copy.deepcopy(record)
    extra["supported_cases"] = ["a"]
    with pytest.raises(ElementwiseSchemaError, match="extra"):
        ProgramManifest.from_record(extra)


def test_manifest_digest_covers_every_parent_class() -> None:
    manifest = _manifest()
    records = []
    for mutation in (
        lambda value: value["sources"][0].__setitem__("source_sha256", F),
        lambda value: value["contracts"].__setitem__("shared_sha256", F),
        lambda value: value["intrinsic_capabilities"][0].__setitem__("sha256", E),
        lambda value: value["layout"]["capability"].__setitem__("sha256", F),
        lambda value: value["schedules"][0].__setitem__("control_sha256", F),
        lambda value: value.__setitem__("consumed_effects_sha256", F),
    ):
        record = manifest.unsigned_record()
        mutation(record)
        records.append(canonical_sha256(record))
    assert all(value != manifest.sha256 for value in records)
    assert len(records) == len(set(records))


def test_one_global_intrinsic_reference_can_feed_multiple_manifests() -> None:
    first = _manifest()
    second_source = SourceArtifact(
        Architecture.NEON,
        "heldout/random/source.c",
        "renamed_left",
        F,
        "facade/a.h",
        E,
        D,
    )
    second = ProgramManifest(
        compiler_sha256=first.compiler_sha256,
        sources=(second_source, first.sources[1]),
        contracts=first.contracts,
        intrinsic_capabilities=first.intrinsic_capabilities,
        layout=first.layout,
        schedules=first.schedules,
        local_assertions=first.local_assertions,
        consumed_effects_sha256=first.consumed_effects_sha256,
    )
    assert first.sha256 != second.sha256
    assert first.intrinsic_capabilities == second.intrinsic_capabilities


def _proof_task() -> ProofTask:
    manifest = _manifest()
    models = GeneratedArtifact(ArtifactKind.MODELS, "out/Models.lean", D, manifest.sha256)
    spec = GeneratedArtifact(ArtifactKind.SPEC, "out/Spec.lean", E, models.sha256)
    return ProofTask(
        manifest_sha256=manifest.sha256,
        models=models,
        spec=spec,
        proof_path="out/Proof.lean",
        module="Generated.Random.Proof",
        theorem="programs_equal",
        elaborated_type_sha256=F,
        checker_policy_sha256=D,
        toolchain_sha256=E,
    )


def test_proof_task_round_trip_and_parent_edges() -> None:
    task = _proof_task()
    assert ProofTask.from_record(task.to_record()) == task
    bad_spec = GeneratedArtifact(ArtifactKind.SPEC, "out/Spec.lean", E, F)
    with pytest.raises(ElementwiseSchemaError, match="Spec artifact"):
        ProofTask(
            manifest_sha256=task.manifest_sha256,
            models=task.models,
            spec=bad_spec,
            proof_path=task.proof_path,
            module=task.module,
            theorem=task.theorem,
            elaborated_type_sha256=task.elaborated_type_sha256,
            checker_policy_sha256=task.checker_policy_sha256,
            toolchain_sha256=task.toolchain_sha256,
        )


def test_verified_result_requires_unchanged_protected_closure() -> None:
    task = _proof_task()
    result = Result(
        status=ResultStatus.VERIFIED_VALUE,
        proof_task_sha256=task.sha256,
        proof_sha256=D,
        checker_sha256=E,
        toolchain_sha256=F,
        start_closure_sha256=D,
        end_closure_sha256=D,
        detail="Lean accepted the generated value theorem",
    )
    assert Result.from_record(result.to_record()) == result
    with pytest.raises(ElementwiseSchemaError, match="protected closure changed"):
        Result(
            status=ResultStatus.VERIFIED_VALUE,
            proof_task_sha256=task.sha256,
            proof_sha256=D,
            checker_sha256=E,
            toolchain_sha256=F,
            start_closure_sha256=D,
            end_closure_sha256=E,
            detail="invalid",
        )


def test_failure_result_can_exist_before_proof_task() -> None:
    result = Result(
        status=ResultStatus.ENTRY_CONTRACT_MISMATCH,
        proof_task_sha256=None,
        proof_sha256=None,
        checker_sha256=D,
        toolchain_sha256=E,
        start_closure_sha256=None,
        end_closure_sha256=None,
        detail="normalized entry contracts differ",
    )
    assert Result.from_record(result.to_record()) == result
