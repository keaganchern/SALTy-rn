"""Generate proof-free Lean Models and Spec artifacts from one manifest."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Mapping

from workflow.verification.lean_backend.case_emit import emit_case_pair
from workflow.verification.lean_backend.frontend import KernelExtraction
from workflow.verification.lean_backend.model_profiles import (
    ModelProfile,
    ParameterField,
    PrefixTailProfile,
)
from workflow.verification.lean_backend.schema import IntrinsicSpec

from .capabilities import ScheduleKind
from .recognize import PairRecognition
from .schema import ProgramManifest


class GenerationError(ValueError):
    """The recognized pair cannot be rendered by the current generic emitter."""


@dataclass(frozen=True, slots=True)
class EmittedStack:
    models_text: str
    spec_text: str
    parameter_type: str
    neon_block: str
    rvv_chunk: str
    target_theorem: str


_FIELD_PREFIX = "field:params@0.scalar."
_INTEGER_WIDTHS = {
    "signed char": 8,
    "unsigned char": 8,
    "char": 8,
    "int8_t": 8,
    "uint8_t": 8,
    "short": 16,
    "unsigned short": 16,
    "int16_t": 16,
    "uint16_t": 16,
    "int": 32,
    "unsigned int": 32,
    "int32_t": 32,
    "uint32_t": 32,
    "long": 64,
    "unsigned long": 64,
    "int64_t": 64,
    "uint64_t": 64,
}


def _normalized_integer(type_spelling: str) -> str:
    value = re.sub(r"\b(const|volatile|restrict)\b", "", type_spelling)
    return " ".join(value.split())


def _integer_width(type_spelling: str) -> int | None:
    return _INTEGER_WIDTHS.get(_normalized_integer(type_spelling))


def _field(dependency: str) -> str | None:
    if not dependency.startswith(_FIELD_PREFIX):
        return None
    name = dependency.removeprefix(_FIELD_PREFIX)
    return name if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name) else None


def _field_widths(extractions: Iterable[KernelExtraction]) -> tuple[ParameterField, ...]:
    widths: dict[str, int] = {}
    for extraction in extractions:
        for definition in extraction.definitions:
            width = _integer_width(definition.type_spelling)
            if width is None:
                continue
            for dependency in definition.dependencies:
                name = _field(dependency)
                if name is not None:
                    widths[name] = max(widths.get(name, 0), width)
        for call in extraction.calls:
            for argument in call.arguments:
                width = _integer_width(argument.type_spelling)
                if width is None:
                    continue
                for dependency in argument.dependencies:
                    name = _field(dependency)
                    if name is not None:
                        widths[name] = max(widths.get(name, 0), width)
    return tuple(ParameterField(name, widths[name]) for name in sorted(widths))


def _rvv_scalar_types(extraction: KernelExtraction) -> tuple[tuple[str, str], ...]:
    result: dict[str, str] = {}
    for definition in extraction.definitions:
        if (
            definition.parent_control is not None
            or definition.definition_kind == "parameter"
            or definition.value_call is not None
            or len(definition.dependencies) != 1
        ):
            continue
        name = _field(definition.dependencies[0])
        if name is not None:
            result[name] = _normalized_integer(definition.type_spelling)
    return tuple(sorted(result.items()))


def _lean_component(namespace: str) -> str:
    component = namespace.rsplit(".", 1)[-1]
    if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_']*", component) is None:
        raise GenerationError(f"invalid generated Lean namespace {namespace!r}")
    return component


def infer_model_profile(
    neon: KernelExtraction,
    rvv: KernelExtraction,
    recognition: PairRecognition,
    *,
    namespace: str,
) -> ModelProfile:
    """Construct the old block-emitter interface solely from extracted facts."""

    fields = _field_widths((neon, rvv))
    prefix = None
    if recognition.neon.kind in {ScheduleKind.FIXED_TAIL, ScheduleKind.MULTI_PHASE}:
        prefix = PrefixTailProfile(
            recognition.neon.element_c_type,
            (
                recognition.neon.phase_widths[-1]
                if recognition.neon.kind is ScheduleKind.MULTI_PHASE
                else recognition.neon.lanes
            ),
            recognition.neon.store_widths,
        )
    return ModelProfile(
        case_id=f"manifest-{recognition.consumed_effects_sha256[:16]}",
        lean_namespace=namespace,
        parameter_type=f"{_lean_component(namespace)}Params",
        parameter_fields=fields,
        rvv_scalar_types=_rvv_scalar_types(rvv),
        inputs=recognition.inputs,
        neon_block_lanes=recognition.neon.lanes,
        neon_loop_condition=next(
            control.condition_text
            for control in neon.controls
            if control.node_id == recognition.neon.loop_control
        ),
        neon_loop_update=next(
            control.update_text
            for control in neon.controls
            if control.node_id == recognition.neon.loop_control
        ),
        input_width=recognition.element_width,
        output_width=recognition.output_width,
        element_c_type=recognition.neon.element_c_type,
        rvv_count_variable=recognition.rvv.count_variable,
        prefix_tail=prefix,
        rvv_signed_shift_branch=bool(recognition.rvv.nested_controls),
        multiphase_widths=(
            recognition.neon.phase_widths
            if recognition.neon.kind is ScheduleKind.MULTI_PHASE
            else ()
        ),
    )


def _model_extensions(
    profile: ModelProfile,
    recognition: PairRecognition,
) -> list[str]:
    input_width = recognition.element_width
    output_width = recognition.output_width
    block_width = recognition.neon.lanes
    inputs = recognition.inputs
    lines = [""]
    if len(inputs) == 1:
        value = "x"
        neon_args = f"(List.replicate {block_width} {value})"
        rvv_args = f"[{value}]"
        lines.extend(
            [
                "/-- Scalar action independently projected from the parsed Neon block. -/",
                f"def fNeon (p : {profile.parameter_type}) ({value} : BitVec {input_width}) : BitVec {output_width} :=",
                f"  ({profile.neon_function} p {neon_args}).headD (0 : BitVec {output_width})",
                "",
                "/-- Scalar action independently projected from the parsed RVV chunk. -/",
                f"def fRvv (p : {profile.parameter_type}) ({value} : BitVec {input_width}) : BitVec {output_width} :=",
                f"  ({profile.rvv_function} p {rvv_args}).headD (0 : BitVec {output_width})",
            ]
        )
    elif len(inputs) == 2:
        neon_args = " ".join(
            f"(List.replicate {block_width} {name})" for name in ("x", "y")
        )
        lines.extend(
            [
                "/-- Scalar action independently projected from the parsed Neon block. -/",
                f"def fNeon (p : {profile.parameter_type}) (x y : BitVec {input_width}) : BitVec {output_width} :=",
                f"  ({profile.neon_function} p {neon_args}).headD (0 : BitVec {output_width})",
                "",
                "/-- Scalar action independently projected from the parsed RVV chunk. -/",
                f"def fRvv (p : {profile.parameter_type}) (x y : BitVec {input_width}) : BitVec {output_width} :=",
                f"  ({profile.rvv_function} p [x] [y]).headD (0 : BitVec {output_width})",
            ]
        )
    else:
        raise GenerationError("value specification supports one or two input streams")

    if recognition.neon.kind is ScheduleKind.MULTI_PHASE:
        small_width = recognition.neon.phase_widths[-1]
        secondary_function = f"neonBlock{small_width}FromIntrinsics"
        if len(inputs) == 1:
            value = inputs[0]
            lines.extend(
                [
                    "",
                    "/-- Scalar action projected from the parsed secondary Neon block. -/",
                    f"def fNeonSecondary (p : {profile.parameter_type})",
                    f"    ({value} : BitVec {input_width}) : BitVec {output_width} :=",
                    f"  ({secondary_function} p [{value}]).headD "
                    f"(0 : BitVec {output_width})",
                ]
            )
        else:
            lines.extend(
                [
                    "",
                    "/-- Scalar action projected from the parsed secondary Neon block. -/",
                    f"def fNeonSecondary (p : {profile.parameter_type})",
                    f"    (x y : BitVec {input_width}) : BitVec {output_width} :=",
                    f"  ({secondary_function} p [x] [y]).headD "
                    f"(0 : BitVec {output_width})",
                ]
            )

    if recognition.neon.kind is ScheduleKind.FIXED_NO_TAIL:
        lines.extend([""])
        if len(inputs) == 1:
            name = inputs[0]
            lines.extend(
                [
                    "/-- Generated fixed-width loop assembly; divisibility stays in Spec. -/",
                    f"def neonValueLoopFromIntrinsics (p : {profile.parameter_type})",
                    f"    ({name} : List (BitVec {input_width})) : List (BitVec {output_width}) :=",
                    f"  SALT.Kernel.ElementwiseFamily.runFixedNoTail {block_width} (by omega)",
                    f"    ({profile.neon_function} p) {name}",
                    "",
                    "/-- Generated RVV positive-partition assembly. -/",
                    f"def rvvValueLoopFromIntrinsics (p : {profile.parameter_type})",
                    f"    ({name} : List (BitVec {input_width}))",
                    f"    (schedule : SALT.Kernel.Schedule.PositivePartition {name}.length) :",
                    f"    List (BitVec {output_width}) :=",
                    f"  SALT.Kernel.Schedule.processBlocks ({profile.rvv_function} p) {name} schedule",
                ]
            )
        else:
            first, second = inputs
            lines.extend(
                [
                    "/-- Generated synchronized fixed-width loop assembly. -/",
                    f"def neonValueLoopFromIntrinsics (p : {profile.parameter_type})",
                    f"    ({first} {second} : List (BitVec {input_width}))",
                    f"    (sameLength : {first}.length = {second}.length) : List (BitVec {output_width}) :=",
                    f"  SALT.Kernel.Schedule.runFixedChunkTail2 {block_width} (by omega)",
                    f"    ({profile.neon_function} p) (fun _ _ => []) {first} {second} sameLength",
                    "",
                    "/-- Generated synchronized RVV positive-partition assembly. -/",
                    f"def rvvValueLoopFromIntrinsics (p : {profile.parameter_type})",
                    f"    ({first} {second} : List (BitVec {input_width}))",
                    f"    (sameLength : {first}.length = {second}.length)",
                    f"    (schedule : SALT.Kernel.Schedule.PositivePartition {first}.length) :",
                    f"    List (BitVec {output_width}) :=",
                    f"  SALT.Kernel.Schedule.processBlocks2 ({profile.rvv_function} p)",
                    f"    {first} {second} sameLength schedule",
                ]
            )
    elif recognition.neon.kind is ScheduleKind.MULTI_PHASE:
        lines.extend(
            [
                "",
                "/-- Generated RVV positive-partition assembly. -/",
                f"def rvvValueLoopFromIntrinsics (p : {profile.parameter_type})",
            ]
        )
        if len(inputs) == 1:
            name = inputs[0]
            lines.extend(
                [
                    f"    ({name} : List (BitVec {input_width}))",
                    f"    (schedule : SALT.Kernel.Schedule.PositivePartition {name}.length) :",
                    f"    List (BitVec {output_width}) :=",
                    f"  SALT.Kernel.Schedule.processBlocks ({profile.rvv_function} p) {name} schedule",
                ]
            )
        elif len(inputs) == 2:
            first, second = inputs
            lines.extend(
                [
                    f"    ({first} {second} : List (BitVec {input_width}))",
                    f"    (sameLength : {first}.length = {second}.length)",
                    f"    (schedule : SALT.Kernel.Schedule.PositivePartition {first}.length) :",
                    f"    List (BitVec {output_width}) :=",
                    f"  SALT.Kernel.Schedule.processBlocks2 ({profile.rvv_function} p)",
                    f"    {first} {second} sameLength schedule",
                ]
            )
        else:
            raise GenerationError("multi-phase value loops support one or two input streams")
    return lines


def _insert_before_end(text: str, namespace: str, lines: Iterable[str]) -> str:
    marker = f"\nend {namespace}\n"
    if text.count(marker) != 1:
        raise GenerationError("generated base model has no unique namespace end")
    return text.replace(marker, "\n" + "\n".join(lines) + marker)


def _ensure_import(text: str, module: str) -> str:
    import_line = f"import {module}\n"
    if import_line in text:
        return text
    first_blank = text.find("\n\n")
    if first_blank < 0:
        raise GenerationError("generated model import header is malformed")
    return text[:first_blank] + "\n" + import_line.rstrip() + text[first_blank:]


def _spec_text(
    manifest: ProgramManifest,
    models_sha256: str,
    profile: ModelProfile,
    recognition: PairRecognition,
) -> str:
    input_width = recognition.element_width
    block_width = recognition.neon.lanes
    inputs = recognition.inputs
    binary = len(inputs) == 2
    map_expr = (
        f"{inputs[0]}.map (fNeon p)"
        if not binary
        else f"List.zipWith (fNeon p) {inputs[0]} {inputs[1]}"
    )
    rvv_map_expr = (
        f"{inputs[0]}.map (fRvv p)"
        if not binary
        else f"List.zipWith (fRvv p) {inputs[0]} {inputs[1]}"
    )
    secondary_map_expr = (
        f"{inputs[0]}.map (fNeonSecondary p)"
        if not binary
        else f"List.zipWith (fNeonSecondary p) {inputs[0]} {inputs[1]}"
    )
    params = " ".join(inputs)
    list_binders = f"({params} : List (BitVec {input_width}))"
    same_length = (
        ""
        if not binary
        else f" ({inputs[0]}.length = {inputs[1]}.length)"
    )
    element_args = "(x : BitVec {0})".format(input_width)
    element_apply = "x"
    if binary:
        element_args = f"(x y : BitVec {input_width})"
        element_apply = "x y"
    neon_loop_args = f"p {params}"
    rvv_loop_args = f"p {params}"
    if binary:
        neon_loop_args += " sameLength"
        rvv_loop_args += " sameLength"
    tail_family = recognition.neon.kind in {
        ScheduleKind.FIXED_TAIL,
        ScheduleKind.MULTI_PHASE,
    }
    if tail_family:
        tail_load_width = recognition.neon.phase_widths[-1]
        overreads = tuple(f"overread{index}" for index in range(len(inputs)))
        overread_binder = f"({' '.join(overreads)} : List (BitVec {input_width}))"
        neon_loop_args = f"p {params} {' '.join(overreads)}"
        if binary:
            neon_loop_args += " sameLength"
        overread_condition = " ∧ ".join(
            f"{tail_load_width - 1} ≤ {name}.length" for name in overreads
        )
    else:
        overread_binder = ""
        overread_condition = "True"
    same_binder = (
        ""
        if not binary
        else f"    (sameLength : {inputs[0]}.length = {inputs[1]}.length),\n"
    )
    neon_precondition = (
        f"{overread_condition} →"
        if tail_family
        else f"{block_width} ∣ {inputs[0]}.length →"
    )
    spec = [
        "-- This file is generated and proof-free. Proof search must not edit it.",
        f"import {profile.lean_namespace}.Models",
        "",
        f"namespace {profile.lean_namespace}",
        "",
        f'def manifestSha256InSpec : String := "{manifest.sha256}"',
        f'def modelsSha256InSpec : String := "{models_sha256}"',
        f'def sharedEntryContractSha256 : String := "{manifest.contracts.shared.sha256}"',
        "",
        "def neonBlockEqualsMapClaim : Prop :=",
        f"  ∀ (p : {profile.parameter_type}) {list_binders},",
    ]
    if binary:
        spec.extend(
            [
                f"    {inputs[0]}.length = {block_width} →",
                f"    {inputs[0]}.length = {inputs[1]}.length →",
                f"    {profile.neon_function} p {params} = {map_expr}",
            ]
        )
    else:
        spec.extend(
            [
                f"    {inputs[0]}.length = {block_width} →",
                f"    {profile.neon_function} p {params} = {map_expr}",
            ]
        )
    if recognition.neon.kind is ScheduleKind.MULTI_PHASE:
        small_width = recognition.neon.phase_widths[-1]
        spec.extend(
            [
                "",
                "def neonSecondaryBlockEqualsMapClaim : Prop :=",
                f"  ∀ (p : {profile.parameter_type}) {list_binders},",
                f"    {inputs[0]}.length = {small_width} →",
                *(
                    [f"    {inputs[0]}.length = {inputs[1]}.length →"]
                    if binary
                    else []
                ),
                f"    neonBlock{small_width}FromIntrinsics p {params} = "
                f"{secondary_map_expr}",
                "",
                "def neonPhaseFunctionsEqualClaim : Prop :=",
                f"  ∀ (p : {profile.parameter_type}) {element_args},",
                f"    fNeon p {element_apply} = "
                f"fNeonSecondary p {element_apply}",
            ]
        )
    spec.extend(
        [
            "",
            "def rvvChunkEqualsMapClaim : Prop :=",
            f"  ∀ (p : {profile.parameter_type}) {list_binders},",
            *(
                [f"    {inputs[0]}.length = {inputs[1]}.length →"]
                if binary
                else []
            ),
            f"    {profile.rvv_function} p {params} = {rvv_map_expr}",
            "",
            "def elementFunctionsEqualClaim : Prop :=",
            f"  ∀ (p : {profile.parameter_type}) {element_args}, fNeon p {element_apply} = fRvv p {element_apply}",
            "",
            "def neonLoopEqualsMapClaim : Prop :=",
            f"  ∀ (p : {profile.parameter_type}) {list_binders}",
        ]
    )
    if overread_binder:
        spec.append(f"    {overread_binder}{'' if binary else ','}")
    else:
        spec[-1] += ","
    if same_binder:
        spec.append(same_binder.rstrip())
    spec.extend(
        [
            f"    {neon_precondition}",
            f"    neonValueLoop{'WithOverread' if overread_binder else ''}FromIntrinsics {neon_loop_args} = {map_expr}",
            "",
            "def rvvLoopEqualsMapClaim : Prop :=",
            f"  ∀ (p : {profile.parameter_type}) {list_binders}",
        ]
    )
    if binary:
        spec.append(f"    (sameLength : {inputs[0]}.length = {inputs[1]}.length)")
    spec.extend(
        [
            f"    (schedule : SALT.Kernel.Schedule.PositivePartition {inputs[0]}.length),",
            f"    rvvValueLoopFromIntrinsics {rvv_loop_args} schedule = {rvv_map_expr}",
            "",
            "def completeValueEquivalenceClaim : Prop :=",
            f"  ∀ (p : {profile.parameter_type}) {list_binders}",
        ]
    )
    if overread_binder:
        spec.append(f"    {overread_binder}")
    if binary:
        spec.append(f"    (sameLength : {inputs[0]}.length = {inputs[1]}.length)")
    spec.extend(
        [
            f"    (schedule : SALT.Kernel.Schedule.PositivePartition {inputs[0]}.length),",
            f"    {neon_precondition}",
            f"    neonValueLoop{'WithOverread' if overread_binder else ''}FromIntrinsics {neon_loop_args} =",
            f"      rvvValueLoopFromIntrinsics {rvv_loop_args} schedule",
            "",
            f"end {profile.lean_namespace}",
            "",
        ]
    )
    return "\n".join(spec)


def emit_stack(
    neon: KernelExtraction,
    rvv: KernelExtraction,
    recognition: PairRecognition,
    manifest: ProgramManifest,
    *,
    namespace: str,
    neon_registry: Mapping[str, IntrinsicSpec],
    rvv_registry: Mapping[str, IntrinsicSpec],
) -> EmittedStack:
    profile = infer_model_profile(neon, rvv, recognition, namespace=namespace)
    registry_digest = hashlib.sha256(
        "".join(reference.sha256 for reference in manifest.intrinsic_capabilities).encode("ascii")
    ).hexdigest()
    emitted = emit_case_pair(
        neon,
        rvv,
        profile=profile,
        neon_registry=neon_registry,
        rvv_registry=rvv_registry,
        registry_sha256=registry_digest,
    )
    if len(emitted.neon_consumed_calls) != len(neon.calls):
        raise GenerationError("Neon emitter did not consume every reachable call")
    if len(emitted.rvv_consumed_calls) != len(rvv.calls):
        raise GenerationError("RVV emitter did not consume every reachable call")
    models = emitted.emitted.module_text
    models = _ensure_import(models, "SALT.Kernel.ElementwiseFamily")
    namespace_marker = f"namespace {namespace}\n\n"
    if models.count(namespace_marker) != 1:
        raise GenerationError("generated Models namespace marker is not unique")
    models = models.replace(
        namespace_marker,
        namespace_marker
        + f'def programManifestSha256 : String := "{manifest.sha256}"\n'
        + f'def consumedEffectsSha256 : String := "{manifest.consumed_effects_sha256}"\n\n',
    )
    models = _insert_before_end(models, namespace, _model_extensions(profile, recognition))
    models_sha = hashlib.sha256(models.encode("ascii")).hexdigest()
    spec = _spec_text(manifest, models_sha, profile, recognition)
    return EmittedStack(
        models,
        spec,
        profile.parameter_type,
        profile.neon_function,
        profile.rvv_function,
        "completeValueEquivalenceClaim",
    )
