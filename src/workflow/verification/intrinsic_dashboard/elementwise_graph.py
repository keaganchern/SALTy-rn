"""Read the elementwise compiler's content-addressed artifacts for the dashboard.

The projection is deliberately derived from CorpusReport/ArtifactIndex records.
It has no program catalogue and treats a missing, changed, or unbound artifact as
stale instead of inferring progress from file presence.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping

from workflow.verification.elementwise_compiler.capabilities import (
    IntrinsicCapability,
    LayoutViewCapability,
    ScheduleFamilyCapability,
)
from workflow.verification.elementwise_compiler.reviews import IntrinsicReview
from workflow.verification.elementwise_compiler.program_reviews import (
    ProgramReviewError,
    load_program_reviews,
)
from workflow.verification.elementwise_compiler.schema import (
    ArtifactKind,
    CounterexampleWitness,
    CrossPhaseAudit,
    CrossPhaseAuditStatus,
    ExternalConditionEvidence,
    GeneratedArtifact,
    ProgramManifest,
    ProofTask,
    Result,
    ResultStatus,
    canonical_sha256,
)


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
DEFAULT_CORPUS_ROOT = REPOSITORY_ROOT / "verification/elementwise-compiler"


class ElementwiseGraphError(RuntimeError):
    """A report or artifact binding is malformed."""


def _json(path: Path) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as error:
        raise ElementwiseGraphError(f"cannot read {path.name}") from error
    if not isinstance(value, Mapping) or any(not isinstance(key, str) for key in value):
        raise ElementwiseGraphError(f"{path.name} is not a JSON object")
    return value


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _bound_path(root: Path, value: object, field: str) -> Path:
    if not isinstance(value, str) or not value:
        raise ElementwiseGraphError(f"{field} is missing")
    candidate = (root / value).resolve()
    try:
        candidate.relative_to(root.resolve())
    except ValueError as error:
        raise ElementwiseGraphError(f"{field} escapes the artifact root") from error
    return candidate


def _verify_report(root: Path) -> Mapping[str, Any]:
    report = _json(root / "CorpusReport.json")
    digest = report.get("report_sha256")
    unsigned = dict(report)
    unsigned.pop("report_sha256", None)
    if digest != canonical_sha256(unsigned):
        raise ElementwiseGraphError("CorpusReport digest disagrees with contents")
    if report.get("artifact_kind") != "elementwise-corpus-report":
        raise ElementwiseGraphError("unexpected corpus report kind")
    if not isinstance(report.get("programs"), list) or not isinstance(
        report.get("intrinsic_dependencies"), list
    ):
        raise ElementwiseGraphError("CorpusReport collections are malformed")
    return report


def _verify_intrinsic_registry(
    root: Path, binding: object
) -> tuple[tuple[IntrinsicCapability, IntrinsicReview | None], ...]:
    if not isinstance(binding, Mapping):
        raise ElementwiseGraphError("intrinsic registry binding is malformed")
    path = _bound_path(root, binding.get("path"), "intrinsic registry path")
    registry = _json(path)
    unsigned = dict(registry)
    digest = unsigned.pop("registry_sha256", None)
    if (
        registry.get("artifact_kind") != "elementwise-intrinsic-registry"
        or registry.get("schema_version") != 1
        or digest != canonical_sha256(unsigned)
        or binding.get("sha256") != digest
    ):
        raise ElementwiseGraphError("intrinsic registry digest disagrees with contents")
    raw_variants = registry.get("variants")
    if not isinstance(raw_variants, list):
        raise ElementwiseGraphError("intrinsic registry variants are malformed")
    variants: list[tuple[IntrinsicCapability, IntrinsicReview | None]] = []
    seen: set[tuple[str, str]] = set()
    for raw in raw_variants:
        if not isinstance(raw, Mapping) or set(raw) != {"capability", "review"}:
            raise ElementwiseGraphError("intrinsic registry entry is malformed")
        capability_raw = raw["capability"]
        if not isinstance(capability_raw, Mapping):
            raise ElementwiseGraphError("intrinsic registry capability is malformed")
        capability = IntrinsicCapability.from_record(capability_raw)
        review_raw = raw["review"]
        review = None
        if review_raw is not None:
            if not isinstance(review_raw, Mapping):
                raise ElementwiseGraphError("intrinsic registry review is malformed")
            review = IntrinsicReview.from_record(review_raw)
            if (
                capability.review_evidence_sha256 != review.sha256
                or capability.architecture is not review.architecture
                or capability.spelling != review.spelling
                or capability.function_type != review.function_type
                or capability.argument_count != review.argument_count
                or capability.descriptor_sha256 != review.descriptor_sha256
                or capability.implementation_sha256 != review.implementation_sha256
            ):
                raise ElementwiseGraphError("intrinsic review does not bind its capability")
        elif capability.review_evidence_sha256 is not None:
            raise ElementwiseGraphError("reviewed capability has no review record")
        identity = (capability.capability_id, capability.sha256)
        if identity in seen:
            raise ElementwiseGraphError("duplicate intrinsic registry variant")
        seen.add(identity)
        variants.append((capability, review))
    return tuple(variants)


def _verify_intrinsic_audit(
    root: Path,
    *,
    registry_variants: tuple[tuple[IntrinsicCapability, IntrinsicReview | None], ...],
    used_by_program: Mapping[tuple[str, str], set[str]],
    required: bool = False,
) -> Mapping[str, Mapping[str, Any]]:
    """Read the primary-source audit and bind every exact registry row."""

    path = root / "IntrinsicAudit.json"
    if not path.is_file():
        if required:
            raise ElementwiseGraphError(
                "schema-v2 intrinsic reviews require IntrinsicAudit.json"
            )
        return {}
    audit = _json(path)
    unsigned = dict(audit)
    digest = unsigned.pop("audit_sha256", None)
    if (
        audit.get("artifact_kind") != "elementwise-intrinsic-audit-candidates"
        or audit.get("schema_version") != 2
        or digest != canonical_sha256(unsigned)
    ):
        raise ElementwiseGraphError("intrinsic audit digest disagrees")
    raw_variants = audit.get("variants")
    if not isinstance(raw_variants, list):
        raise ElementwiseGraphError("intrinsic audit variants are malformed")
    registry = {capability.capability_id: (capability, review)
                for capability, review in registry_variants}
    if len(registry) != len(registry_variants):
        raise ElementwiseGraphError("duplicate intrinsic capability id")
    result: dict[str, Mapping[str, Any]] = {}
    required = {
        "capability_id", "audit_variant_sha256", "used", "programs",
        "architecture", "spelling", "function_type", "argument_count", "role",
        "descriptor_sha256", "implementation_sha256", "semantic_symbol",
        "immediate_constraints", "architecture_conditions", "claim_scope",
        "primary_evidence", "static_checks",
    }
    for raw in raw_variants:
        if not isinstance(raw, Mapping) or set(raw) != required:
            raise ElementwiseGraphError("intrinsic audit variant is malformed")
        identity = str(raw["capability_id"])
        bound = registry.get(identity)
        if bound is None or identity in result:
            raise ElementwiseGraphError("intrinsic audit exact identity is invalid")
        capability, review = bound
        audited_subject = {
            key: value
            for key, value in raw.items()
            if key not in {"used", "programs", "audit_variant_sha256"}
        }
        programs = sorted(used_by_program.get(
            (capability.capability_id, capability.sha256), set()
        ))
        if (
            raw["audit_variant_sha256"] != canonical_sha256(audited_subject)
            or raw["used"] != bool(programs)
            or raw["programs"] != programs
            or raw["architecture"] != capability.architecture.value
            or raw["spelling"] != capability.spelling
            or raw["function_type"] != capability.function_type
            or raw["argument_count"] != capability.argument_count
            or raw["role"] != capability.role.value
            or raw["descriptor_sha256"] != capability.descriptor_sha256
            or raw["implementation_sha256"] != capability.implementation_sha256
            or raw["semantic_symbol"] != capability.semantic_symbol
            or raw["static_checks"]
            != {
                "canonical_descriptor": "passed",
                "exact_source_signature": "passed",
                "implementation_bound": "passed",
            }
            or not isinstance(raw["architecture_conditions"], list)
            or any(
                not isinstance(item, str) or not item
                for item in raw["architecture_conditions"]
            )
            or not isinstance(raw["primary_evidence"], Mapping)
        ):
            raise ElementwiseGraphError("intrinsic audit does not bind its capability")
        if review is not None and (
            review.audit_variant_sha256 != raw["audit_variant_sha256"]
            or review.claim_scope != raw["claim_scope"]
            or list(review.architecture_conditions) != raw["architecture_conditions"]
        ):
            raise ElementwiseGraphError("intrinsic review does not bind its audit scope")
        result[identity] = raw
    if set(result) != set(registry):
        raise ElementwiseGraphError("intrinsic audit does not cover the exact registry")
    return result


def _verify_intrinsic_review_plan(
    root: Path,
    *,
    intrinsic_audit: Mapping[str, Mapping[str, Any]],
    required: bool = False,
) -> Mapping[str, str]:
    """Bind each used audit subject to one explicit semantic review family."""

    path = root / "IntrinsicReviewPlan.json"
    if not path.is_file():
        if required:
            raise ElementwiseGraphError(
                "schema-v2 intrinsic reviews require IntrinsicReviewPlan.json"
            )
        return {}
    if not intrinsic_audit:
        if required:
            raise ElementwiseGraphError(
                "schema-v2 intrinsic reviews require a verified intrinsic audit"
            )
        return {}
    plan = _json(path)
    unsigned = dict(plan)
    digest = unsigned.pop("plan_sha256", None)
    audit_record = _json(root / "IntrinsicAudit.json")
    if (
        plan.get("artifact_kind") != "elementwise-intrinsic-review-plan"
        or plan.get("schema_version") != 1
        or digest != canonical_sha256(unsigned)
        or plan.get("audit_sha256") != audit_record.get("audit_sha256")
    ):
        raise ElementwiseGraphError("intrinsic review plan digest/parent disagrees")
    raw_families = plan.get("families")
    if not isinstance(raw_families, list):
        raise ElementwiseGraphError("intrinsic review families are malformed")
    result: dict[str, str] = {}
    for raw_family in raw_families:
        if not isinstance(raw_family, Mapping) or set(raw_family) != {
            "family", "count", "subjects"
        }:
            raise ElementwiseGraphError("intrinsic review family is malformed")
        family = raw_family["family"]
        subjects = raw_family["subjects"]
        if not isinstance(family, str) or not family or not isinstance(subjects, list):
            raise ElementwiseGraphError("intrinsic review family fields are malformed")
        if raw_family["count"] != len(subjects):
            raise ElementwiseGraphError("intrinsic review family count disagrees")
        for subject in subjects:
            if not isinstance(subject, Mapping):
                raise ElementwiseGraphError("intrinsic review subject is malformed")
            identity = str(subject.get("capability_id", ""))
            audit = intrinsic_audit.get(identity)
            subject_fields = (
                "capability_id", "audit_variant_sha256", "architecture", "spelling",
                "function_type", "argument_count", "role", "descriptor_sha256",
                "implementation_sha256", "semantic_symbol", "immediate_constraints",
                "claim_scope", "architecture_conditions", "programs", "primary_evidence",
            )
            expected_subject = (
                {} if audit is None else {field: audit[field] for field in subject_fields}
            )
            if (
                audit is None
                or not audit["used"]
                or identity in result
                or dict(subject) != expected_subject
            ):
                raise ElementwiseGraphError("intrinsic review subject is not exact")
            result[identity] = family
    used = {identity for identity, row in intrinsic_audit.items() if row["used"]}
    if set(result) != used:
        raise ElementwiseGraphError("intrinsic review plan does not cover used variants")
    return result


def _parse_capability(record: Mapping[str, Any]) -> object:
    kind = record.get("artifact_kind")
    if kind == "intrinsic-capability":
        return IntrinsicCapability.from_record(record)
    if kind == "layout-view-capability":
        return LayoutViewCapability.from_record(record)
    if kind == "schedule-family-capability":
        return ScheduleFamilyCapability.from_record(record)
    raise ElementwiseGraphError(f"unsupported capability artifact {kind!r}")


def _verify_generated(
    program_root: Path, record: Mapping[str, Any]
) -> GeneratedArtifact:
    artifact = GeneratedArtifact.from_record(record)
    path = _bound_path(program_root, artifact.path, f"{artifact.kind.value} path")
    if not path.is_file() or _sha256(path) != artifact.sha256:
        raise ElementwiseGraphError(f"{artifact.kind.value} file digest mismatch")
    return artifact


def _verify_stack(corpus_root: Path, relative_index: object) -> dict[str, Any]:
    index_path = _bound_path(corpus_root, relative_index, "artifact index")
    index = _json(index_path)
    unsigned_index = dict(index)
    stack_digest = unsigned_index.pop("stack_sha256", None)
    if stack_digest != canonical_sha256(unsigned_index):
        raise ElementwiseGraphError("ArtifactIndex digest disagrees with contents")
    program_root = index_path.parent

    manifest_binding = index.get("manifest")
    if not isinstance(manifest_binding, Mapping):
        raise ElementwiseGraphError("manifest binding is malformed")
    manifest_path = _bound_path(
        program_root, manifest_binding.get("path"), "manifest path"
    )
    manifest = ProgramManifest.from_record(_json(manifest_path))
    if manifest_binding.get("sha256") != manifest.sha256:
        raise ElementwiseGraphError("manifest binding digest mismatch")

    models_record = index.get("models")
    spec_record = index.get("spec")
    if not isinstance(models_record, Mapping) or not isinstance(spec_record, Mapping):
        raise ElementwiseGraphError("Models/Spec bindings are malformed")
    models = _verify_generated(program_root, models_record)
    spec = _verify_generated(program_root, spec_record)
    if (
        models.kind is not ArtifactKind.MODELS
        or models.parent_sha256 != manifest.sha256
    ):
        raise ElementwiseGraphError("Models is not bound to the manifest")
    if spec.kind is not ArtifactKind.SPEC or spec.parent_sha256 != models.sha256:
        raise ElementwiseGraphError("Spec is not bound to Models")

    external_binding = index.get("external_condition")
    if not isinstance(external_binding, Mapping):
        raise ElementwiseGraphError("external-condition binding is malformed")
    external_path = _bound_path(
        program_root, external_binding.get("path"), "external-condition path"
    )
    external = ExternalConditionEvidence.from_record(_json(external_path))
    if (
        external_binding.get("sha256") != external.sha256
        or external_binding.get("status") != external.status.value
        or manifest.external_condition.sha256 != external.sha256
        or manifest.external_condition.status is not external.status
        or manifest.external_condition.path != external_binding.get("path")
    ):
        raise ElementwiseGraphError("external-condition binding digest mismatch")

    phase_binding = index.get("cross_phase_audit")
    if not isinstance(phase_binding, Mapping):
        raise ElementwiseGraphError("cross-phase audit binding is malformed")
    phase_path = _bound_path(
        program_root, phase_binding.get("path"), "cross-phase audit path"
    )
    phase = CrossPhaseAudit.from_record(_json(phase_path))
    if (
        phase_binding.get("sha256") != phase.sha256
        or phase_binding.get("status") != phase.status.value
        or phase.manifest_sha256 != manifest.sha256
        or phase.models_sha256 != models.sha256
        or phase.spec_sha256 != spec.sha256
    ):
        raise ElementwiseGraphError("cross-phase audit binding digest mismatch")

    counterexample: CounterexampleWitness | None = None
    counterexample_binding = index.get("counterexample")
    if counterexample_binding is not None:
        if not isinstance(counterexample_binding, Mapping):
            raise ElementwiseGraphError("counterexample binding is malformed")
        counterexample_path = _bound_path(
            program_root, counterexample_binding.get("path"), "counterexample path"
        )
        counterexample = CounterexampleWitness.from_record(_json(counterexample_path))
        lean_path = _bound_path(
            program_root, counterexample.lean_path, "counterexample Lean path"
        )
        if (
            counterexample_binding.get("sha256") != counterexample.sha256
            or counterexample_binding.get("lean_sha256") != counterexample.lean_sha256
            or not lean_path.is_file()
            or _sha256(lean_path) != counterexample.lean_sha256
            or counterexample.manifest_sha256 != manifest.sha256
            or counterexample.models_sha256 != models.sha256
            or counterexample.spec_sha256 != spec.sha256
        ):
            raise ElementwiseGraphError("counterexample binding digest mismatch")
        phase_claim = f"{index.get('namespace')}.neonPhaseFunctionsEqualClaim"
        complete_claim = f"{index.get('namespace')}.{index.get('target_claim')}"
        if counterexample.claim == phase_claim:
            if (
                phase.status is not CrossPhaseAuditStatus.COUNTEREXAMPLE
                or phase.counterexample_sha256 != counterexample.sha256
            ):
                raise ElementwiseGraphError("phase counterexample audit mismatch")
        elif counterexample.claim == complete_claim:
            if phase.status is CrossPhaseAuditStatus.COUNTEREXAMPLE:
                raise ElementwiseGraphError("program counterexample conflicts with phase audit")
        else:
            raise ElementwiseGraphError("counterexample does not refute a generated claim")
    elif phase.status is CrossPhaseAuditStatus.COUNTEREXAMPLE:
        raise ElementwiseGraphError("cross-phase audit has no counterexample")

    capability_ids: list[str] = []
    intrinsic_capabilities: list[IntrinsicCapability] = []
    bindings = index.get("capabilities")
    if not isinstance(bindings, list):
        raise ElementwiseGraphError("capability bindings are malformed")
    for binding in bindings:
        if not isinstance(binding, Mapping):
            raise ElementwiseGraphError("capability binding is malformed")
        path = _bound_path(program_root, binding.get("path"), "capability path")
        parsed = _parse_capability(_json(path))
        capability_id = getattr(parsed, "capability_id")
        capability_sha = getattr(parsed, "sha256")
        if (
            binding.get("capability_id") != capability_id
            or binding.get("sha256") != capability_sha
        ):
            raise ElementwiseGraphError("capability binding digest mismatch")
        capability_ids.append(capability_id)
        if isinstance(parsed, IntrinsicCapability):
            intrinsic_capabilities.append(parsed)

    task: ProofTask | None = None
    task_binding = index.get("proof_task")
    if task_binding is not None:
        if not isinstance(task_binding, Mapping):
            raise ElementwiseGraphError("proof-task binding is malformed")
        task_path = _bound_path(
            program_root, task_binding.get("path"), "proof-task path"
        )
        task = ProofTask.from_record(_json(task_path))
        if task_binding.get("sha256") != task.sha256:
            raise ElementwiseGraphError("proof-task binding digest mismatch")
        if (
            task.manifest_sha256 != manifest.sha256
            or task.models != models
            or task.spec != spec
        ):
            raise ElementwiseGraphError(
                "proof task is not bound to the generated stack"
            )

    result: Result | None = None
    result_binding = index.get("result")
    if result_binding is not None:
        if not isinstance(result_binding, Mapping):
            raise ElementwiseGraphError("result binding is malformed")
        result_path = _bound_path(
            program_root, result_binding.get("path"), "result path"
        )
        result = Result.from_record(_json(result_path))
        if (
            result_binding.get("sha256") != result.sha256
            or result_binding.get("status") != result.status.value
        ):
            raise ElementwiseGraphError("result binding digest mismatch")
        if result.status is ResultStatus.COUNTEREXAMPLE:
            if (
                task is not None
                or counterexample is None
                or result.counterexample_sha256 != counterexample.sha256
                or result.checker_sha256 != counterexample.checker_sha256
                or result.toolchain_sha256 != counterexample.toolchain_sha256
            ):
                raise ElementwiseGraphError(
                    "counterexample result is not bound to its checked witness"
                )
        else:
            if task is None:
                raise ElementwiseGraphError("proof result has no valid proof task")
            if (
                result.proof_task_sha256 is not None
                and result.proof_task_sha256 != task.sha256
            ):
                raise ElementwiseGraphError("result is bound to another proof task")
            if (
                result.checker_sha256 != task.checker_policy_sha256
                or result.toolchain_sha256 != task.toolchain_sha256
            ):
                raise ElementwiseGraphError(
                    "result checker/toolchain differs from its proof task"
                )
        if result.proof_sha256 is not None and task is not None:
            proof_path = _bound_path(program_root, task.proof_path, "proof path")
            if not proof_path.is_file() or _sha256(proof_path) != result.proof_sha256:
                raise ElementwiseGraphError("proof file digest mismatch")

    return {
        "manifest": manifest,
        "models": models,
        "spec": spec,
        "capability_ids": tuple(sorted(capability_ids)),
        "intrinsic_capabilities": tuple(intrinsic_capabilities),
        "task": task,
        "result": result,
        "external": external,
        "phase": phase,
        "counterexample": counterexample,
    }


def _program_node(
    corpus_root: Path, record: Mapping[str, Any]
) -> tuple[dict[str, Any], tuple[IntrinsicCapability, ...]]:
    program_id = record.get("program_id")
    if not isinstance(program_id, str) or not program_id:
        raise ElementwiseGraphError("program id is malformed")
    status = str(record.get("status", "generation-failed"))
    layer = str(record.get("status_layer", "corpus"))
    artifacts: dict[str, object] = {
        "manifest": False,
        "models": False,
        "spec": False,
        "external_condition": False,
        "cross_phase_audit": False,
        "counterexample": False,
        "proof_task": False,
        "result": False,
    }
    claim = {"value": "not-checked", "c": "not-established", "isa": "not-established"}
    input_condition: dict[str, object] = {
        "scope": "not-generated",
        "status": str(record.get("external_condition_status", "not-generated")),
    }
    cross_phase: dict[str, object] = {
        "status": str(record.get("cross_phase_status", "not-generated")),
        "trial_count": 0,
    }
    counterexample_record: dict[str, object] | None = None
    stale = False
    detail = str(record.get("detail", "no detail"))
    intrinsic_capabilities: tuple[IntrinsicCapability, ...] = ()
    if record.get("artifact_index") is not None:
        try:
            stack = _verify_stack(corpus_root, record["artifact_index"])
            manifest = stack["manifest"]
            if record.get("manifest_sha256") != manifest.sha256:
                raise ElementwiseGraphError("CorpusReport manifest binding mismatch")
            task = stack["task"]
            result = stack["result"]
            external = stack["external"]
            phase = stack["phase"]
            counterexample = stack["counterexample"]
            input_condition = {
                "scope": external.scope.value,
                "status": external.status.value,
            }
            cross_phase = {
                "status": phase.status.value,
                "trial_count": phase.trial_count,
            }
            if counterexample is not None:
                counterexample_record = {
                    "claim": counterexample.claim,
                    "parameters": dict(counterexample.parameter_values),
                    "inputs": list(counterexample.input_values),
                    "left_output": counterexample.left_output,
                    "right_output": counterexample.right_output,
                }
            artifacts.update(
                manifest=True,
                models=True,
                spec=True,
                external_condition=True,
                cross_phase_audit=True,
                counterexample=stack["counterexample"] is not None,
                proof_task=task is not None,
                result=result is not None,
            )
            intrinsic_capabilities = stack["intrinsic_capabilities"]
            if result is not None:
                status = result.status.value
                layer = "checked-result"
                claim["value"] = (
                    "verified"
                    if result.status is ResultStatus.VERIFIED_VALUE
                    else "failed"
                )
                detail = result.detail
            elif task is not None:
                status = "proof-ready"
                layer = "frozen-proof-task"
                claim["value"] = "ready"
            else:
                claim["value"] = (
                    "spec-generated" if status == "spec-generated" else "blocked"
                )
        except Exception as error:
            status = "stale-artifact"
            layer = "artifact-integrity"
            stale = True
            detail = f"{type(error).__name__}: {error}"

    return (
        {
            "program_id": program_id,
            "status": status,
            "status_layer": layer,
            "layout": str(record.get("layout_preflight", "unknown")),
            "schedule": str(record.get("schedule_preflight", "unknown")),
            "contract": str(record.get("entry_contract_preflight", "unknown")),
            "missing_intrinsics": list(record.get("missing_intrinsics", [])),
            "artifacts": artifacts,
            "input_condition": input_condition,
            "cross_phase": cross_phase,
            "counterexample": counterexample_record,
            "claim": claim,
            "stale": stale,
            "detail": detail,
        },
        intrinsic_capabilities,
    )


def build_elementwise_graph(
    corpus_root: str | Path = DEFAULT_CORPUS_ROOT,
    *,
    include_intrinsic_audit: bool = True,
    include_program_reviews: bool = True,
) -> dict[str, Any]:
    """Build a fail-closed UI projection from the generated artifact graph."""

    root = Path(corpus_root).resolve()
    report_path = root / "CorpusReport.json"
    if not report_path.is_file():
        return {
            "schema_version": 3,
            "available": False,
            "message": f"Run the elementwise corpus compiler to create {report_path.name}",
            "summary": {},
            "programs": [],
            "capabilities": [],
        }
    report = _verify_report(root)
    registry_variants = _verify_intrinsic_registry(
        root, report.get("intrinsic_registry")
    )
    scoped_reviews_present = any(
        review is not None and review.schema_version == 2
        for _, review in registry_variants
    )
    registry_by_identity = {
        (capability.capability_id, capability.sha256): capability
        for capability, _ in registry_variants
    }
    program_nodes: list[dict[str, Any]] = []
    used_by_program: dict[tuple[str, str], set[str]] = {}
    for raw in report["programs"]:
        if not isinstance(raw, Mapping):
            raise ElementwiseGraphError("program record is malformed")
        node, capabilities = _program_node(root, raw)
        program_nodes.append(node)
        for capability in capabilities:
            identity = (capability.capability_id, capability.sha256)
            if identity not in registry_by_identity:
                raise ElementwiseGraphError(
                    "program capability is absent from the bound intrinsic registry"
                )
            used_by_program.setdefault(identity, set()).add(str(node["program_id"]))

    intrinsic_audit = (
        _verify_intrinsic_audit(
            root,
            registry_variants=registry_variants,
            used_by_program=used_by_program,
            required=scoped_reviews_present,
        )
        if include_intrinsic_audit
        else {}
    )
    intrinsic_review_families = (
        _verify_intrinsic_review_plan(
            root,
            intrinsic_audit=intrinsic_audit,
            required=scoped_reviews_present,
        )
        if include_intrinsic_audit
        else {}
    )

    # Establish the reusable intrinsic review closure before loading per-program
    # approvals.  This preserves fail-closed diagnostic priority and prevents a
    # copied corpus with external review parents absent from hiding a corrupted
    # intrinsic audit.
    try:
        program_reviews = load_program_reviews(root) if include_program_reviews else {}
    except ProgramReviewError as error:
        raise ElementwiseGraphError(str(error)) from error
    for node in program_nodes:
        review = program_reviews.get(str(node["program_id"]))
        node["independently_reviewed"] = review is not None
        node["program_review_sha256"] = None if review is None else review.sha256
        node["reviewed_outcome"] = None if review is None else review.outcome_status

    spelling_nodes: list[dict[str, Any]] = []
    for raw in report["intrinsic_dependencies"]:
        if not isinstance(raw, Mapping):
            raise ElementwiseGraphError("intrinsic dependency is malformed")
        intrinsic = str(raw.get("intrinsic", ""))
        architecture, separator, spelling = intrinsic.partition(":")
        if separator != ":" or architecture not in {"neon", "rvv"} or not spelling:
            raise ElementwiseGraphError("intrinsic dependency id is malformed")
        matching = [
            (capability, review if include_intrinsic_audit else None)
            for capability, review in registry_variants
            if capability.architecture.value == architecture
            and capability.spelling == spelling
        ]
        lean_checked = bool(matching) and all(
            review is not None
            and any(check.name == "lean-elaboration" for check in review.checks)
            for _, review in matching
        )
        independently_reviewed = bool(matching) and all(
            review is not None for _, review in matching
        )
        used_matching = [
            capability
            for capability, _ in matching
            if (capability.capability_id, capability.sha256) in used_by_program
        ]
        spelling_nodes.append(
            {
                "id": intrinsic,
                "architecture": architecture,
                "spelling": spelling,
                "configured": bool(raw.get("configured")) and bool(matching),
                "defined": bool(raw.get("configured")) and bool(matching),
                "lean_checked": lean_checked,
                "reviewed": independently_reviewed,
                "independently_reviewed": independently_reviewed,
                "typed_variants": len(matching),
                "used_typed_variants": len(used_matching),
                "review_sha256": sorted(
                    review.sha256 for _, review in matching if review is not None
                ),
                "programs": list(raw.get("programs", [])),
            }
        )

    variant_nodes: list[dict[str, Any]] = []
    for capability, review in registry_variants:
        if not include_intrinsic_audit:
            review = None
        identity = (capability.capability_id, capability.sha256)
        programs = sorted(used_by_program.get(identity, set()))
        audit = intrinsic_audit.get(capability.capability_id)
        lean_checked = review is not None and any(
            check.name == "lean-elaboration" for check in review.checks
        )
        variant_nodes.append(
            {
                "id": capability.capability_id,
                "sha256": capability.sha256,
                "architecture": capability.architecture.value,
                "spelling": capability.spelling,
                "function_type": capability.function_type,
                "argument_count": capability.argument_count,
                "role": capability.role.value,
                "semantic_symbol": capability.semantic_symbol,
                "descriptor_sha256": capability.descriptor_sha256,
                "implementation_sha256": capability.implementation_sha256,
                "defined": True,
                "used": bool(programs),
                "lean_checked": lean_checked,
                "reviewed": review is not None,
                "independently_reviewed": review is not None,
                "review_sha256": None if review is None else review.sha256,
                "primary_source_audited": audit is not None,
                "claim_scope": None if audit is None else audit["claim_scope"],
                "architecture_conditions": (
                    [] if audit is None else list(audit["architecture_conditions"])
                ),
                "review_family": intrinsic_review_families.get(
                    capability.capability_id
                ),
                "programs": programs,
            }
        )

    status_counts: dict[str, int] = {}
    for node in program_nodes:
        status_counts[node["status"]] = status_counts.get(node["status"], 0) + 1
    return {
        "schema_version": 3,
        "available": True,
        "report_sha256": report["report_sha256"],
        "authority": {
            "program_discovery": str(report["discovery_rule"]),
            "program_status": "content-addressed-artifact-closure",
            "legacy_case_lists_used": False,
        },
        "summary": {
            "discovered_elementwise": report["discovered_elementwise"],
            "scalar_layout_scope": report["scalar_layout_scope"],
            "grouped_layout_deferred": report["grouped_layout_deferred"],
            "status_counts": status_counts,
            "configured_intrinsic_spellings": sum(
                item["configured"] for item in spelling_nodes
            ),
            "reviewed_intrinsic_spellings": sum(
                item["reviewed"] for item in spelling_nodes
            ),
            "lean_checked_intrinsic_spellings": sum(
                item["lean_checked"] for item in spelling_nodes
            ),
            "intrinsic_spelling_dependencies": len(spelling_nodes),
            "registry_intrinsic_variants": len(variant_nodes),
            "primary_source_audited_intrinsic_variants": sum(
                item["primary_source_audited"] for item in variant_nodes
            ),
            "conditioned_intrinsic_variants": sum(
                bool(item["architecture_conditions"]) for item in variant_nodes
            ),
            "used_intrinsic_variants": sum(item["used"] for item in variant_nodes),
            "reviewed_registry_intrinsic_variants": sum(
                item["reviewed"] for item in variant_nodes
            ),
            "reviewed_used_intrinsic_variants": sum(
                item["reviewed"] and item["used"] for item in variant_nodes
            ),
            "lean_checked_used_intrinsic_variants": sum(
                item["lean_checked"] and item["used"] for item in variant_nodes
            ),
            "input_condition_counts": {
                status: sum(
                    node["input_condition"]["status"] == status
                    for node in program_nodes
                )
                for status in sorted(
                    {str(node["input_condition"]["status"]) for node in program_nodes}
                )
            },
            "cross_phase_counts": {
                status: sum(
                    node["cross_phase"]["status"] == status
                    for node in program_nodes
                )
                for status in sorted(
                    {str(node["cross_phase"]["status"]) for node in program_nodes}
                )
            },
            "independently_reviewed_programs": sum(
                bool(node["independently_reviewed"]) for node in program_nodes
            ),
        },
        "programs": sorted(program_nodes, key=lambda item: item["program_id"]),
        "intrinsic_spellings": sorted(spelling_nodes, key=lambda item: item["id"]),
        "capabilities": sorted(
            variant_nodes, key=lambda item: (item["architecture"], item["spelling"], item["id"])
        ),
    }


def create_elementwise_provider(corpus_root: str | Path = DEFAULT_CORPUS_ROOT):
    root = Path(corpus_root)
    return lambda: build_elementwise_graph(root)
