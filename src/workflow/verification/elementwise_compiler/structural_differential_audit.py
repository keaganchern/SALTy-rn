"""Trace exact schedule/structural capabilities through C and Lean lowering.

This audit intentionally does *not* use the word ``passed`` to mean ISA
adequacy.  It checks a narrower boundary: every used S0/S1/S2 exact capability
must be joined to pinned authority metadata, real elementwise C call sites, its
canonical descriptor, the production structural lowerer, and every generated
program manifest that claims to consume it.  A small mutation suite exercises
the production generator's fail-closed handling of lane selectors, slide
offsets, RVV active length, and a negated broadcast.

The independent lexical call scanner below is deliberately separate from the
Clang frontend.  It is not a C type checker; the exact type identity still comes
from the canonical registry.  Its purpose is to make missing call sites,
immediate values, and active-length operands visible instead of accepting the
generator's own manifest as its sole oracle.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import tempfile
from pathlib import Path
from typing import Any, Mapping, Sequence

from workflow.verification.lean_backend.case_emit import (
    CaseEmissionError,
    emit_case_pair,
)
from workflow.verification.lean_backend.descriptor import (
    canonical_spec_digest,
    canonical_spec_record,
)
from workflow.verification.lean_backend.emit_lean import LeanEmissionError
from workflow.verification.lean_backend.frontend import parse_kernel
from workflow.verification.lean_backend.intrinsic_index import (
    CANONICAL_INTRINSIC_INDEX,
)
from workflow.verification.lean_backend.model_profiles import SCALE_UP_MODELS
from workflow.verification.lean_backend.profiles import FRONTEND_PROFILES
from workflow.verification.lean_backend.scaleup_catalog import SCALEUP_CATALOGS
from workflow.verification.lean_backend.schema import (
    ScheduleIntrinsic,
    StructuralIntrinsic,
    StructuralOp,
)

from .schema import canonical_json, canonical_sha256


SCHEMA_VERSION = 1
ARTIFACT_KIND = "structural-lowering-trace-audit"
SELECTED_FAMILIES = (
    "S0-schedule-setvl",
    "S1-structural-plain",
    "S2-structural-immediate",
)
L2 = "L2-traceable-lowering"
L3 = "L3-generator-mutation"
COVERAGE_SCOPE = (
    "exact-used-capability-to-real-c-call-and-production-lowering;"
    "generator-boundary-only;not-isa-adequacy;memory-alias-overread-flags-traps-"
    "and-legal-vsetvl-refinement-excluded"
)


class StructuralDifferentialAuditError(RuntimeError):
    """The exact structural corpus or its trace evidence is inconsistent."""


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_json(path: Path) -> dict[str, Any]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise StructuralDifferentialAuditError(f"expected JSON object: {path}")
    return value


def _relative(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError as error:
        raise StructuralDifferentialAuditError(
            f"audit evidence must remain inside repository: {path}"
        ) from error


def _mask_non_code(source: str) -> str:
    """Mask comments and literals while preserving byte offsets and newlines."""

    chars = list(source)
    index = 0
    state = "code"
    quote = ""
    while index < len(chars):
        current = chars[index]
        following = chars[index + 1] if index + 1 < len(chars) else ""
        if state == "code":
            if current == "/" and following == "/":
                chars[index] = chars[index + 1] = " "
                index += 2
                state = "line-comment"
                continue
            if current == "/" and following == "*":
                chars[index] = chars[index + 1] = " "
                index += 2
                state = "block-comment"
                continue
            if current in {'"', "'"}:
                quote = current
                chars[index] = " "
                index += 1
                state = "literal"
                continue
        elif state == "line-comment":
            if current == "\n":
                state = "code"
            else:
                chars[index] = " "
        elif state == "block-comment":
            if current == "*" and following == "/":
                chars[index] = chars[index + 1] = " "
                index += 2
                state = "code"
                continue
            if current != "\n":
                chars[index] = " "
        else:
            if current == "\\" and following:
                if current != "\n":
                    chars[index] = " "
                if following != "\n":
                    chars[index + 1] = " "
                index += 2
                continue
            if current == quote:
                chars[index] = " "
                state = "code"
            elif current != "\n":
                chars[index] = " "
        index += 1
    return "".join(chars)


def _split_arguments(source: str) -> tuple[str, ...]:
    values: list[str] = []
    start = 0
    depths = {"(": 0, "[": 0, "{": 0}
    closing = {")": "(", "]": "[", "}": "{"}
    for index, character in enumerate(source):
        if character in depths:
            depths[character] += 1
        elif character in closing:
            opener = closing[character]
            depths[opener] -= 1
            if depths[opener] < 0:
                raise StructuralDifferentialAuditError("unbalanced call argument")
        elif character == "," and not any(depths.values()):
            values.append(source[start:index].strip())
            start = index + 1
    if any(depths.values()):
        raise StructuralDifferentialAuditError("unbalanced nested call argument")
    tail = source[start:].strip()
    if tail or source.strip():
        values.append(tail)
    return tuple(values)


def _integer_literal(value: str) -> int | None:
    compact = re.sub(r"\s+", "", value)
    matched = re.fullmatch(r"([+-]?)(0[xX][0-9A-Fa-f]+|[0-9]+)(?:[uUlL]+)?", compact)
    if matched is None:
        return None
    parsed = int(matched.group(2), 0)
    return -parsed if matched.group(1) == "-" else parsed


def _call_sites(path: Path, spelling: str, architecture: str, program: str) -> list[dict[str, Any]]:
    source = path.read_text(encoding="utf-8")
    masked = _mask_non_code(source)
    pattern = re.compile(rf"\b{re.escape(spelling)}\s*\(")
    records: list[dict[str, Any]] = []
    for matched in pattern.finditer(masked):
        opening = masked.find("(", matched.start())
        depth = 1
        cursor = opening + 1
        while cursor < len(masked) and depth:
            if masked[cursor] == "(":
                depth += 1
            elif masked[cursor] == ")":
                depth -= 1
            cursor += 1
        if depth:
            raise StructuralDifferentialAuditError(
                f"unterminated call {spelling} in {path}"
            )
        arguments = _split_arguments(source[opening + 1 : cursor - 1])
        prefix_start = max(
            source.rfind(";", 0, matched.start()),
            source.rfind("{", 0, matched.start()),
            source.rfind("}", 0, matched.start()),
        ) + 1
        prefix = source[prefix_start : matched.start()]
        assignment = re.search(
            r"(?:^|\s)([A-Za-z_][A-Za-z0-9_]*)\s*=\s*$", prefix
        )
        line = source.count("\n", 0, matched.start()) + 1
        column = matched.start() - source.rfind("\n", 0, matched.start())
        records.append(
            {
                "program": program,
                "architecture": architecture,
                "path": path.as_posix(),
                "file_sha256": _sha256(path),
                "line": line,
                "column": column,
                "call_text": re.sub(r"\s+", " ", source[matched.start() : cursor]).strip(),
                "arguments": [re.sub(r"\s+", " ", value).strip() for value in arguments],
                "assigned_to": None if assignment is None else assignment.group(1),
            }
        )
    return records


def _line_numbers(path: Path, needle: str) -> list[int]:
    matches = [
        index
        for index, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1)
        if needle in line
    ]
    if not matches:
        raise StructuralDifferentialAuditError(
            f"production lowering anchor disappeared: {path}: {needle}"
        )
    return matches


_GENERIC_ANCHORS = {
    "broadcast": "if operation is StructuralOp.BROADCAST:",
    "take_low": "if operation in {StructuralOp.TAKE_LOW, StructuralOp.TAKE_HIGH}:",
    "take_high": "if operation in {StructuralOp.TAKE_LOW, StructuralOp.TAKE_HIGH}:",
    "concatenate": "if operation is StructuralOp.CONCATENATE:",
    "bitcast": "if operation is StructuralOp.BITCAST:",
    "extract_from_concat": "if operation is StructuralOp.EXTRACT_FROM_CONCAT:",
}

_CONTEXT_ANCHORS = {
    "set_active_length": "if isinstance(spec, ScheduleIntrinsic):",
    "broadcast": "if spec.operation is StructuralOp.BROADCAST:",
    "load-broadcast": "if spec.operation is StructuralOp.LOAD_BROADCAST:",
    "load": "and spec.operation is StructuralOp.LOAD",
    "store": "and spec.operation is StructuralOp.STORE",
    "lane_store": "def _consume_little_endian_lane_store(",
    "extract_from_concat": "and advance_spec.operation is StructuralOp.EXTRACT_FROM_CONCAT",
}


def _operation(spec: StructuralIntrinsic | ScheduleIntrinsic) -> str:
    return spec.operation.value


def _operand_roles(spec: StructuralIntrinsic | ScheduleIntrinsic) -> tuple[str, ...]:
    if isinstance(spec, ScheduleIntrinsic):
        roles = ("requested-active-length",)
    else:
        roles_by_operation: dict[StructuralOp, tuple[str, ...]] = {
            StructuralOp.BROADCAST: ("scalar-value",),
            StructuralOp.LOAD_BROADCAST: ("memory-base",),
            StructuralOp.LOAD: ("memory-base",),
            StructuralOp.STORE: ("memory-base", "stored-vector"),
            StructuralOp.LANE_STORE: ("memory-base", "stored-vector", "lane-immediate"),
            StructuralOp.TAKE_LOW: ("source-vector",),
            StructuralOp.TAKE_HIGH: ("source-vector",),
            StructuralOp.CONCATENATE: ("low-vector", "high-vector"),
            StructuralOp.BITCAST: ("source-bits",),
            StructuralOp.EXTRACT_FROM_CONCAT: (
                "left-vector",
                "right-vector",
                "offset-immediate",
            ),
        }
        roles = roles_by_operation[spec.operation]
        if spec.architecture.value == "rvv":
            parameters = spec.signature.parameters
            if len(parameters) == len(roles) + 1 and parameters[-1].name == "vl":
                roles = (*roles, "active-length")
    if len(roles) != len(spec.signature.parameters):
        raise StructuralDifferentialAuditError(
            f"operand accounting incomplete for {spec.spelling}: {roles!r}"
        )
    return roles


def _lowering_record(
    root: Path, spec: StructuralIntrinsic | ScheduleIntrinsic
) -> dict[str, Any]:
    generic = root / "src/workflow/verification/lean_backend/emit_lean.py"
    context = root / "src/workflow/verification/lean_backend/case_emit.py"
    binding = root / "src/workflow/verification/lean_backend/binding.py"
    operation = _operation(spec)
    generic_anchor = _GENERIC_ANCHORS.get(operation)
    context_anchor = _CONTEXT_ANCHORS.get(operation)
    anchors: list[dict[str, Any]] = []
    if generic_anchor is not None:
        anchors.append(
            {
                "path": _relative(generic, root),
                "file_sha256": _sha256(generic),
                "needle": generic_anchor,
                "lines": _line_numbers(generic, generic_anchor),
            }
        )
    if context_anchor is not None:
        anchors.append(
            {
                "path": _relative(context, root),
                "file_sha256": _sha256(context),
                "needle": context_anchor,
                "lines": _line_numbers(context, context_anchor),
            }
        )
    if not anchors:
        # Loads/stores and lane operations are context-sensitive.  Every closed
        # operation must nevertheless have an explicit production anchor.
        raise StructuralDifferentialAuditError(
            f"no production lowering anchor for {spec.spelling}/{operation}"
        )
    return {
        "renderer": "production-case-emitter",
        "structural_operation": operation,
        "operand_roles": list(_operand_roles(spec)),
        "all_source_arguments_accounted_for": True,
        "anchors": anchors,
        "binding_guard": {
            "path": _relative(binding, root),
            "file_sha256": _sha256(binding),
            "argument_validation_lines": _line_numbers(
                binding, "def _validate_argument_operations("
            ),
        },
    }


def _extract_and_emit_scaleup(root: Path, case_id: str, *, neon: Path | None = None, rvv: Path | None = None):
    profile = FRONTEND_PROFILES[case_id]
    neon_extraction = parse_kernel(
        neon or root / "kernels/source" / f"{case_id}.c", profile=profile.neon
    )
    rvv_extraction = parse_kernel(
        rvv or root / "kernels/target" / f"{case_id}.c", profile=profile.rvv
    )
    catalog = SCALEUP_CATALOGS[case_id]
    return emit_case_pair(
        neon_extraction,
        rvv_extraction,
        profile=SCALE_UP_MODELS[case_id],
        neon_registry=catalog.registry,
        rvv_registry=catalog.registry,
        registry_sha256="0" * 64,
    )


def _expected_rejection(probe: str, action, message: str) -> dict[str, Any]:
    try:
        action()
    except (CaseEmissionError, LeanEmissionError, ValueError) as error:
        if re.search(message, str(error)) is None:
            raise StructuralDifferentialAuditError(
                f"{probe} rejected for the wrong reason: {type(error).__name__}: {error}"
            ) from error
        return {
            "probe": probe,
            "status": "passed",
            "expected": "production generator rejects mutation",
            "observed_exception": type(error).__name__,
            "observed_reason_pattern": message,
        }
    raise StructuralDifferentialAuditError(f"{probe} was silently accepted")


def _generator_mutation_probes(root: Path) -> list[dict[str, Any]]:
    """Run deterministic source mutations against the real production emitter."""

    records: list[dict[str, Any]] = []
    with tempfile.TemporaryDirectory(prefix=".structural-audit-", dir=root) as directory:
        temporary = Path(directory)

        rvv_source = root / "kernels/target/s8-vclamp.c"
        rvv_text = rvv_source.read_text(encoding="utf-8")
        old_vl = "__riscv_vle8_v_i8m8(input, vl)"
        if rvv_text.count(old_vl) != 1:
            raise StructuralDifferentialAuditError("active-vl mutation anchor changed")
        changed_rvv = temporary / "s8-vclamp-active-vl.c"
        changed_rvv.write_text(rvv_text.replace(old_vl, old_vl.replace("vl)", "-vl)")), encoding="utf-8")
        records.append(
            _expected_rejection(
                "rvv-active-length-expression",
                lambda: _extract_and_emit_scaleup(root, "s8-vclamp", rvv=changed_rvv),
                "does not consume active vl",
            )
        )

        neon_source = root / "kernels/source/s8-vclamp.c"
        neon_text = neon_source.read_text(encoding="utf-8")
        old_slide = "vext_s8(vacc, vacc, 4)"
        if neon_text.count(old_slide) != 1:
            raise StructuralDifferentialAuditError("slide mutation anchor changed")
        changed_neon = temporary / "s8-vclamp-slide.c"
        changed_neon.write_text(neon_text.replace(old_slide, "vext_s8(vacc, vacc, 3)"), encoding="utf-8")
        records.append(
            _expected_rejection(
                "neon-slide-immediate",
                lambda: _extract_and_emit_scaleup(root, "s8-vclamp", neon=changed_neon),
                "immediate|same-name-mismatch|conditional slide changed",
            )
        )

        lane_source = root / "kernels/source/s8-vclamp.c"
        lane_text = lane_source.read_text(encoding="utf-8")
        old_lane = "vst1_lane_s8(output, vacc, 0)"
        if lane_text.count(old_lane) != 1:
            raise StructuralDifferentialAuditError("lane mutation anchor changed")
        changed_lane = temporary / "s8-vclamp-lane.c"
        changed_lane.write_text(lane_text.replace(old_lane, "vst1_lane_s8(output, vacc, 1)"), encoding="utf-8")
        records.append(
            _expected_rejection(
                "neon-tail-lane-selector",
                lambda: _extract_and_emit_scaleup(root, "s8-vclamp", neon=changed_lane),
                "lane-store shape changed",
            )
        )

        qs8_source = root / "kernels/source/qu8-vadd-minmax.c"
        qs8_text = qs8_source.read_text(encoding="utf-8")
        old_broadcast = "vdupq_n_s32(-params->scalar.shift)"
        if qs8_text.count(old_broadcast) != 1:
            raise StructuralDifferentialAuditError("broadcast mutation anchor changed")
        changed_broadcast = temporary / "qu8-vadd-minmax-broadcast.c"
        changed_broadcast.write_text(
            qs8_text.replace(old_broadcast, "vdupq_n_s32(params->scalar.shift)"),
            encoding="utf-8",
        )
        original = _extract_and_emit_scaleup(root, "qu8-vadd-minmax").emitted.module_text
        changed = _extract_and_emit_scaleup(
            root, "qu8-vadd-minmax", neon=changed_broadcast
        ).emitted.module_text
        original_shift_lines = [
            line for line in original.splitlines() if "let vright_shift_0 :=" in line
        ]
        changed_shift_lines = [
            line for line in changed.splitlines() if "let vright_shift_0 :=" in line
        ]
        if (
            original == changed
            or not original_shift_lines
            or not all("List.replicate 4 (-" in line for line in original_shift_lines)
        ):
            raise StructuralDifferentialAuditError(
                "negated broadcast is not reflected in the emitted model"
            )
        if not changed_shift_lines or any(
            "List.replicate 4 (-" in line for line in changed_shift_lines
        ):
            raise StructuralDifferentialAuditError(
                "broadcast sign mutation was silently erased"
            )
        records.append(
            {
                "probe": "neon-negated-broadcast-roundtrip",
                "status": "passed",
                "expected": "supported sign mutation changes generated Lean",
                "original_models_sha256": hashlib.sha256(original.encode()).hexdigest(),
                "mutated_models_sha256": hashlib.sha256(changed.encode()).hexdigest(),
            }
        )
    return records


def _subject_evidence_level(
    family: str, spec: StructuralIntrinsic | ScheduleIntrinsic, calls: Sequence[Mapping[str, Any]]
) -> str:
    if family in {"S0-schedule-setvl", "S2-structural-immediate"}:
        return L3
    if spec.architecture.value == "rvv" and any(
        role == "active-length" for role in _operand_roles(spec)
    ):
        return L3
    if (
        spec.spelling == "vdupq_n_s32"
        and isinstance(spec, StructuralIntrinsic)
        and spec.operation is StructuralOp.BROADCAST
    ):
        if any(str(call["arguments"][0]).lstrip().startswith("-") for call in calls):
            return L3
    return L2


def load_exact_subjects(root: Path, corpus: Path) -> tuple[dict[str, Any], ...]:
    registry = _load_json(corpus / "IntrinsicRegistry.json")
    audit = _load_json(corpus / "IntrinsicAudit.json")
    plan = _load_json(corpus / "IntrinsicReviewPlan.json")
    registry_by_id = {
        row["capability"]["capability_id"]: row["capability"]
        for row in registry["variants"]
    }
    audit_by_id = {row["capability_id"]: row for row in audit["variants"]}
    subjects: list[dict[str, Any]] = []
    for family in plan["families"]:
        if family["family"] not in SELECTED_FAMILIES:
            continue
        for planned in family["subjects"]:
            capability_id = planned["capability_id"]
            capability = registry_by_id.get(capability_id)
            audit_row = audit_by_id.get(capability_id)
            if capability is None or audit_row is None:
                raise StructuralDifferentialAuditError(
                    f"structural plan subject is absent from registry/audit: {capability_id}"
                )
            for field in (
                "architecture",
                "spelling",
                "function_type",
                "argument_count",
                "descriptor_sha256",
                "role",
            ):
                if capability[field] != planned[field] or audit_row[field] != planned[field]:
                    raise StructuralDifferentialAuditError(
                        f"exact subject mismatch {capability_id}: {field}"
                    )
            subjects.append(
                {
                    "family": family["family"],
                    "capability": capability,
                    "audit": audit_row,
                    "planned": planned,
                }
            )
    subjects.sort(key=lambda row: row["capability"]["capability_id"])
    if len(subjects) != 68 or len(
        {row["capability"]["capability_id"] for row in subjects}
    ) != 68:
        raise StructuralDifferentialAuditError(
            f"expected 68 unique used S0/S1/S2 exact subjects, got {len(subjects)}"
        )
    return tuple(subjects)


def build_audit(repository_root: str | Path) -> dict[str, Any]:
    root = Path(repository_root).resolve()
    corpus = root / "verification/elementwise-compiler"
    plan = _load_json(corpus / "IntrinsicReviewPlan.json")
    registry = _load_json(corpus / "IntrinsicRegistry.json")
    intrinsic_audit = _load_json(corpus / "IntrinsicAudit.json")
    specs = {
        canonical_spec_digest(variant.spec): variant.spec
        for variant in CANONICAL_INTRINSIC_INDEX.variants
    }
    mutation_probes = _generator_mutation_probes(root)
    rows: list[dict[str, Any]] = []
    for joined in load_exact_subjects(root, corpus):
        family = joined["family"]
        capability = joined["capability"]
        audit_row = joined["audit"]
        spec = specs.get(capability["descriptor_sha256"])
        if not isinstance(spec, (StructuralIntrinsic, ScheduleIntrinsic)):
            raise StructuralDifferentialAuditError(
                f"S-family subject is not structural/schedule: {capability['capability_id']}"
            )
        calls: list[dict[str, Any]] = []
        manifest_bindings: list[dict[str, Any]] = []
        for program in audit_row["programs"]:
            architecture = capability["architecture"]
            path = root / "kernels" / ("source" if architecture == "neon" else "target") / f"{program}.c"
            if not path.is_file():
                raise StructuralDifferentialAuditError(
                    f"real C source is absent for {capability['capability_id']}: {path}"
                )
            found = _call_sites(path, capability["spelling"], architecture, program)
            if not found:
                raise StructuralDifferentialAuditError(
                    f"planned program has no lexical call {capability['spelling']}: {program}"
                )
            for call in found:
                call["path"] = _relative(path, root)
                if len(call["arguments"]) != capability["argument_count"]:
                    raise StructuralDifferentialAuditError(
                        f"lexical arity mismatch {capability['capability_id']} at {program}:{call['line']}"
                    )
            calls.extend(found)

            manifest_path = corpus / "programs" / program / "ProgramManifest.json"
            models_path = corpus / "programs" / program / "Models.lean"
            if not manifest_path.is_file() or not models_path.is_file():
                raise StructuralDifferentialAuditError(
                    f"generated program evidence is absent: {program}"
                )
            manifest = _load_json(manifest_path)
            bound = {
                item["capability_id"] for item in manifest["intrinsic_capabilities"]
            }
            if capability["capability_id"] not in bound:
                raise StructuralDifferentialAuditError(
                    f"manifest omits exact structural capability: {program}/{capability['capability_id']}"
                )
            source_record = next(
                (
                    item
                    for item in manifest["sources"]
                    if item["architecture"] == architecture
                ),
                None,
            )
            if source_record is None or source_record["path"] != _relative(path, root):
                raise StructuralDifferentialAuditError(
                    f"manifest source binding mismatch: {program}/{architecture}"
                )
            if source_record["source_sha256"] != _sha256(path):
                raise StructuralDifferentialAuditError(
                    f"manifest source hash is stale: {program}/{architecture}"
                )
            manifest_bindings.append(
                {
                    "program": program,
                    "manifest_path": _relative(manifest_path, root),
                    "manifest_file_sha256": _sha256(manifest_path),
                    "manifest_sha256": manifest["manifest_sha256"],
                    "models_path": _relative(models_path, root),
                    "models_sha256": _sha256(models_path),
                    "exact_capability_bound": True,
                }
            )

        immediate_values: list[int] = []
        for constraint in spec.immediate_constraints:
            for call in calls:
                value = _integer_literal(call["arguments"][constraint.argument_index])
                if value is None or value not in constraint.allowed_values:
                    raise StructuralDifferentialAuditError(
                        f"immediate provenance mismatch {capability['capability_id']} at "
                        f"{call['path']}:{call['line']}"
                    )
                immediate_values.append(value)

        roles = _operand_roles(spec)
        active_indices = [index for index, role in enumerate(roles) if role == "active-length"]
        active_length_calls = 0
        for call in calls:
            for index in active_indices:
                if call["arguments"][index] != "vl":
                    raise StructuralDifferentialAuditError(
                        f"RVV active-length operand is not exact vl: {capability['capability_id']} "
                        f"at {call['path']}:{call['line']}"
                    )
                active_length_calls += 1
        if isinstance(spec, ScheduleIntrinsic):
            for call in calls:
                if call["assigned_to"] != "vl":
                    raise StructuralDifferentialAuditError(
                        f"vsetvl result is not bound to vl: {call['path']}:{call['line']}"
                    )

        evidence_level = _subject_evidence_level(family, spec, calls)
        row: dict[str, Any] = {
            "capability_id": capability["capability_id"],
            "semantic_family": family,
            "architecture": capability["architecture"],
            "spelling": capability["spelling"],
            "function_type": capability["function_type"],
            "role": capability["role"],
            "descriptor": {
                "descriptor_sha256": capability["descriptor_sha256"],
                "canonical_record": canonical_spec_record(spec),
                "registry_source_path": "src/workflow/verification/lean_backend/registry.py",
                "registry_source_sha256": _sha256(
                    root / "src/workflow/verification/lean_backend/registry.py"
                ),
            },
            "official_pinned_source": audit_row["primary_evidence"],
            "architecture_conditions": audit_row["architecture_conditions"],
            "c_calls": sorted(
                calls, key=lambda item: (item["program"], item["path"], item["line"], item["column"])
            ),
            "lowering": _lowering_record(root, spec),
            "provenance_checks": {
                "program_set_exact": sorted(audit_row["programs"]),
                "manifest_bindings": sorted(manifest_bindings, key=lambda item: item["program"]),
                "immediate_values": sorted(set(immediate_values)),
                "immediates_consumed_by_structural_lowering": bool(spec.immediate_constraints),
                "negative_broadcast_calls": sum(
                    isinstance(spec, StructuralIntrinsic)
                    and spec.operation is StructuralOp.BROADCAST
                    and str(call["arguments"][0]).lstrip().startswith("-")
                    for call in calls
                ),
                "active_length_call_count": active_length_calls,
                "all_call_arities_exact": True,
                "all_source_arguments_accounted_for": True,
            },
            "evidence_level": evidence_level,
            "semantic_correspondence_status": (
                "generator-boundary-validated-only"
                if evidence_level == L3
                else "not-independently-validated"
            ),
            "coverage_scope": COVERAGE_SCOPE,
            "status": "passed",
            "issues": [],
        }
        row["evidence_sha256"] = canonical_sha256(row)
        rows.append(row)

    family_counts = {
        family: sum(row["semantic_family"] == family for row in rows)
        for family in SELECTED_FAMILIES
    }
    operation_counts: dict[str, int] = {}
    for row in rows:
        operation = row["lowering"]["structural_operation"]
        operation_counts[operation] = operation_counts.get(operation, 0) + 1
    record: dict[str, Any] = {
        "artifact_kind": ARTIFACT_KIND,
        "schema_version": SCHEMA_VERSION,
        "coverage_scope": COVERAGE_SCOPE,
        "verdict_definition": (
            "passed means the exact capability is traceably bound to real C calls, "
            "a canonical descriptor, production lowering, generated manifests, and "
            "the applicable generator mutations; it is not an ISA correctness proof"
        ),
        "selected_semantic_families": list(SELECTED_FAMILIES),
        "registry_path": "verification/elementwise-compiler/IntrinsicRegistry.json",
        "registry_file_sha256": _sha256(corpus / "IntrinsicRegistry.json"),
        "registry_sha256": registry["registry_sha256"],
        "intrinsic_audit_path": "verification/elementwise-compiler/IntrinsicAudit.json",
        "intrinsic_audit_file_sha256": _sha256(corpus / "IntrinsicAudit.json"),
        "intrinsic_audit_sha256": intrinsic_audit["audit_sha256"],
        "review_plan_path": "verification/elementwise-compiler/IntrinsicReviewPlan.json",
        "review_plan_file_sha256": _sha256(corpus / "IntrinsicReviewPlan.json"),
        "review_plan_sha256": plan["plan_sha256"],
        "generator_mutation_probes": mutation_probes,
        "ledger_projection_path": "verification/elementwise-compiler/StructuralDifferentialAuditLedger.csv",
        "ledger_join_key": "capability_id",
        "counts": {
            "subjects": len(rows),
            "passed_subjects": sum(row["status"] == "passed" for row in rows),
            "l2_traceable_subjects": sum(row["evidence_level"] == L2 for row in rows),
            "l3_generator_mutation_subjects": sum(row["evidence_level"] == L3 for row in rows),
            "c_call_sites": sum(len(row["c_calls"]) for row in rows),
            "manifest_bindings": sum(
                len(row["provenance_checks"]["manifest_bindings"]) for row in rows
            ),
            "generator_mutation_probes": len(mutation_probes),
            "isa_correctness_validated_subjects": 0,
            "semantic_correspondence_pending_subjects": len(rows),
            "families": family_counts,
            "operations": dict(sorted(operation_counts.items())),
        },
        "subjects": rows,
    }
    validate_audit(record)
    record["audit_sha256"] = canonical_sha256(record)
    return record


def render_ledger_projection(record: Mapping[str, Any]) -> str:
    fields = (
        "capability_id",
        "semantic_family",
        "architecture",
        "spelling",
        "structural_operation",
        "evidence_level",
        "semantic_correspondence_status",
        "audit_status",
        "c_call_sites",
        "manifest_bindings",
        "immediate_values",
        "active_length_call_count",
        "negative_broadcast_calls",
        "evidence_path",
        "evidence_sha256",
        "isa_correctness_proof",
    )
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in sorted(record["subjects"], key=lambda item: item["capability_id"]):
        provenance = row["provenance_checks"]
        writer.writerow(
            {
                "capability_id": row["capability_id"],
                "semantic_family": row["semantic_family"],
                "architecture": row["architecture"],
                "spelling": row["spelling"],
                "structural_operation": row["lowering"]["structural_operation"],
                "evidence_level": row["evidence_level"],
                "semantic_correspondence_status": row[
                    "semantic_correspondence_status"
                ],
                "audit_status": row["status"],
                "c_call_sites": len(row["c_calls"]),
                "manifest_bindings": len(provenance["manifest_bindings"]),
                "immediate_values": ";".join(map(str, provenance["immediate_values"])),
                "active_length_call_count": provenance["active_length_call_count"],
                "negative_broadcast_calls": provenance["negative_broadcast_calls"],
                "evidence_path": "verification/elementwise-compiler/StructuralDifferentialAudit.json",
                "evidence_sha256": row["evidence_sha256"],
                "isa_correctness_proof": "no",
            }
        )
    return stream.getvalue()


def validate_audit(record: Mapping[str, Any]) -> None:
    if record.get("artifact_kind") != ARTIFACT_KIND or record.get("schema_version") != 1:
        raise StructuralDifferentialAuditError("invalid structural audit kind/schema")
    if record.get("coverage_scope") != COVERAGE_SCOPE:
        raise StructuralDifferentialAuditError("structural audit coverage scope changed")
    if record.get("selected_semantic_families") != list(SELECTED_FAMILIES):
        raise StructuralDifferentialAuditError("structural audit family selection changed")
    probes = record.get("generator_mutation_probes")
    if not isinstance(probes, list) or len(probes) != 4 or any(
        probe.get("status") != "passed" for probe in probes
    ):
        raise StructuralDifferentialAuditError("structural mutation probes are incomplete")
    subjects = record.get("subjects")
    if not isinstance(subjects, list) or len(subjects) != 68:
        raise StructuralDifferentialAuditError("structural audit must contain 68 subjects")
    capability_ids: set[str] = set()
    for row in subjects:
        capability_id = row.get("capability_id")
        if not isinstance(capability_id, str) or capability_id in capability_ids:
            raise StructuralDifferentialAuditError("structural capability IDs must be unique")
        capability_ids.add(capability_id)
        if row.get("semantic_family") not in SELECTED_FAMILIES:
            raise StructuralDifferentialAuditError(f"non-structural family: {capability_id}")
        if row.get("evidence_level") not in {L2, L3}:
            raise StructuralDifferentialAuditError(f"invalid evidence level: {capability_id}")
        expected_correspondence = (
            "generator-boundary-validated-only"
            if row.get("evidence_level") == L3
            else "not-independently-validated"
        )
        if row.get("semantic_correspondence_status") != expected_correspondence:
            raise StructuralDifferentialAuditError(
                f"overstated semantic correspondence: {capability_id}"
            )
        if row.get("status") != "passed" or row.get("issues") != []:
            raise StructuralDifferentialAuditError(f"unresolved structural subject: {capability_id}")
        if row.get("coverage_scope") != COVERAGE_SCOPE:
            raise StructuralDifferentialAuditError(f"subject scope changed: {capability_id}")
        if not row.get("c_calls"):
            raise StructuralDifferentialAuditError(f"subject lacks real C calls: {capability_id}")
        lowering = row.get("lowering", {})
        if (
            not lowering.get("all_source_arguments_accounted_for")
            or not lowering.get("anchors")
            or len(lowering.get("operand_roles", [])) != len(row["c_calls"][0]["arguments"])
        ):
            raise StructuralDifferentialAuditError(f"incomplete lowering trace: {capability_id}")
        provenance = row.get("provenance_checks", {})
        if (
            not provenance.get("all_call_arities_exact")
            or not provenance.get("all_source_arguments_accounted_for")
            or len(provenance.get("manifest_bindings", []))
            != len(provenance.get("program_set_exact", []))
        ):
            raise StructuralDifferentialAuditError(f"incomplete provenance: {capability_id}")
        digest = row.get("evidence_sha256")
        unsigned = dict(row)
        unsigned.pop("evidence_sha256", None)
        if digest != canonical_sha256(unsigned):
            raise StructuralDifferentialAuditError(
                f"subject evidence digest mismatch: {capability_id}"
            )


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("verification/elementwise-compiler/StructuralDifferentialAudit.json"),
    )
    parser.add_argument(
        "--ledger-output",
        type=Path,
        default=Path(
            "verification/elementwise-compiler/StructuralDifferentialAuditLedger.csv"
        ),
    )
    parser.add_argument("--check", action="store_true")
    arguments = parser.parse_args(argv)
    root = arguments.root.resolve()
    output = arguments.output if arguments.output.is_absolute() else root / arguments.output
    ledger = (
        arguments.ledger_output
        if arguments.ledger_output.is_absolute()
        else root / arguments.ledger_output
    )
    record = build_audit(root)
    rendered = canonical_json(record, pretty=True)
    projection = render_ledger_projection(record)
    if arguments.check:
        if not output.is_file() or output.read_text(encoding="utf-8") != rendered:
            raise StructuralDifferentialAuditError(f"stale structural audit: {output}")
        if not ledger.is_file() or ledger.read_text(encoding="utf-8") != projection:
            raise StructuralDifferentialAuditError(
                f"stale structural audit ledger projection: {ledger}"
            )
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")
        ledger.parent.mkdir(parents=True, exist_ok=True)
        ledger.write_text(projection, encoding="utf-8")
    print(json.dumps(record["counts"], sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
