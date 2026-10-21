"""Non-authoritative intrinsic onboarding report for configured kernel profiles.

The report runs the real restricted Clang frontend, groups extracted call facts,
and asks the canonical descriptor index which configured lowerings remain
compatible.  Candidate discovery is not semantic approval: the kernel-scoped
catalog remains the only binding consumed by model generation.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from .descriptor import canonical_spec_digest, canonical_spec_record
from .frontend import FrontendError, KernelExtraction, parse_kernel
from .intrinsic_index import (
    CanonicalIntrinsicIndex,
    CanonicalIntrinsicVariant,
    IntrinsicIndexError,
    IntrinsicMatchStatus,
    SourceIntrinsicDescriptor,
    configured_intrinsic_occurrences,
)
from .profiles import FRONTEND_PROFILES, FrontendSideProfile
from .schema import Architecture


_REPOSITORY_ROOT = Path(__file__).resolve().parents[4]
_STATUS_ORDER = (
    IntrinsicMatchStatus.UNIQUE_CANDIDATE,
    IntrinsicMatchStatus.AMBIGUOUS,
    IntrinsicMatchStatus.SAME_NAME_MISMATCH,
    IntrinsicMatchStatus.UNKNOWN,
)


class RegistryOnboardingError(RuntimeError):
    """The requested source cannot enter the configured onboarding workflow."""


def _repository_relative(path: str | Path, root: Path) -> str:
    resolved = Path(path).resolve()
    try:
        return resolved.relative_to(root).as_posix()
    except ValueError as error:
        raise RegistryOnboardingError(
            f"onboarding evidence path is outside the repository: {resolved}"
        ) from error


def _candidate_record(variant: CanonicalIntrinsicVariant) -> dict[str, Any]:
    spec = variant.spec
    canonical = canonical_spec_record(spec)
    candidate = {
        "descriptor_sha256": canonical_spec_digest(spec),
        "architecture": spec.architecture.value,
        "spelling": spec.spelling,
        "kind": spec.kind.value,
        "shape": spec.shape.value,
        "immediate_constraints": canonical["immediate_constraints"],
        "provenance": [
            {
                "case_id": origin.case_id,
                "source_catalog": origin.source_catalog,
            }
            for origin in variant.provenance
        ],
    }
    if "lean_name" in canonical:
        candidate["lean_target"] = canonical["lean_name"]
        candidate["lean_arguments"] = canonical["lean_arguments"]
    elif "structural_operation" in canonical:
        candidate["structural_operation"] = canonical["structural_operation"]
    elif "schedule_operation" in canonical:
        candidate["schedule_operation"] = canonical["schedule_operation"]
    return candidate


def _constant_profile_sort_key(
    constants: tuple[tuple[int, int | str], ...],
) -> tuple[tuple[int, str, str], ...]:
    return tuple(
        (position, type(value).__name__, repr(value))
        for position, value in constants
    )


def _group_record(
    architecture: Architecture,
    calls: Sequence[tuple[str, SourceIntrinsicDescriptor]],
    index: CanonicalIntrinsicIndex,
) -> dict[str, Any]:
    if not calls:
        raise RegistryOnboardingError("cannot report an empty source-call group")
    descriptors = tuple(descriptor for _, descriptor in calls)
    first = descriptors[0]
    if any(descriptor.source_key != first.source_key for descriptor in descriptors[1:]):
        raise RegistryOnboardingError(
            "aggregated source-call group contains different architecture, spelling, "
            "function type, or arity facts"
        )
    if first.architecture is not architecture:
        raise RegistryOnboardingError("source-call group architecture mismatch")

    classification = index.classify_source_call_group(descriptors)
    candidates = sorted(
        (_candidate_record(variant) for variant in classification.variants),
        key=lambda candidate: candidate["descriptor_sha256"],
    )
    calls_by_constants: dict[
        tuple[tuple[int, int | str], ...], list[str]
    ] = defaultdict(list)
    for call_id, descriptor in calls:
        calls_by_constants[descriptor.known_constants].append(call_id)
    constant_profiles = [
        {
            "known_constant_arguments": [
                {"argument_index": argument_index, "value": value}
                for argument_index, value in constants
            ],
            "occurrence_count": len(calls_by_constants[constants]),
            "call_ids": sorted(calls_by_constants[constants]),
        }
        for constants in sorted(calls_by_constants, key=_constant_profile_sort_key)
    ]
    return {
        "architecture": architecture.value,
        "spelling": first.spelling,
        "callee_type": first.function_type,
        "argument_count": first.argument_count,
        "constant_profiles": constant_profiles,
        "occurrence_count": len(calls),
        "call_ids": sorted(call_id for call_id, _ in calls),
        "status": classification.status.value,
        "candidates": candidates,
    }


def _side_report(
    extraction: KernelExtraction,
    architecture: Architecture,
    root: Path,
    index: CanonicalIntrinsicIndex,
) -> dict[str, Any]:
    if extraction.dialect != architecture.value:
        raise RegistryOnboardingError(
            f"extraction dialect {extraction.dialect!r} does not match "
            f"report architecture {architecture.value!r}"
        )
    grouped: dict[
        tuple[Architecture, str, str, int],
        list[tuple[str, SourceIntrinsicDescriptor]],
    ] = defaultdict(list)
    for call in extraction.calls:
        descriptor = SourceIntrinsicDescriptor.from_extracted_call(architecture, call)
        grouped[descriptor.source_key].append((call.node_id, descriptor))

    groups = [
        _group_record(architecture, grouped[key], index)
        for key in sorted(
            grouped,
            key=lambda item: (
                item[0].value,
                item[1],
                item[2],
                item[3],
            ),
        )
    ]
    status_counts = Counter(group["status"] for group in groups)
    return {
        "architecture": architecture.value,
        "source": {
            "path": _repository_relative(extraction.source_path, root),
            "sha256": extraction.source_sha256,
        },
        "parse_facade": {
            "path": _repository_relative(extraction.facade_path, root),
            "sha256": extraction.facade_sha256,
        },
        "function_name": extraction.function_name,
        "function_type": extraction.function_type,
        "target_triple": extraction.target_triple,
        "clang_executable": extraction.clang_executable,
        "clang_version": extraction.clang_version,
        "call_occurrence_count": len(extraction.calls),
        "call_group_count": len(groups),
        "status_group_counts": {
            status.value: status_counts[status.value] for status in _STATUS_ORDER
        },
        "call_groups": groups,
    }


def _extract_side(
    *,
    case_id: str,
    architecture: Architecture,
    side_profile: FrontendSideProfile,
    root: Path,
    clang: str,
) -> KernelExtraction:
    source_directory = "source" if architecture is Architecture.NEON else "target"
    source_path = root / "kernels" / source_directory / f"{case_id}.c"
    facade_path = (
        root
        / "src"
        / "workflow"
        / "verification"
        / "lean_backend"
        / "facade"
        / side_profile.facade_path.name
    )
    return parse_kernel(
        source_path,
        clang=clang,
        facade=facade_path,
        profile=side_profile,
    )


def build_onboarding_report(
    case_id: str,
    *,
    repository_root: str | Path = _REPOSITORY_ROOT,
    clang: str = "clang",
    index: CanonicalIntrinsicIndex | None = None,
) -> dict[str, Any]:
    """Extract and classify one case that already has an exact parse profile."""

    try:
        profile = FRONTEND_PROFILES[case_id]
    except KeyError as error:
        raise RegistryOnboardingError(
            f"case {case_id!r} has no configured frontend profile; add an exact "
            "function/facade/call profile before Clang extraction. This command "
            "is not a generic new-kernel parser"
        ) from error

    root = Path(repository_root).resolve()
    if not root.is_dir():
        raise RegistryOnboardingError(f"repository root does not exist: {root}")

    excluded_case_catalog = index is None or all(
        origin.case_id != case_id
        for variant in index.variants
        for origin in variant.provenance
    )
    candidate_index = index
    if candidate_index is None:
        external_occurrences = tuple(
            occurrence
            for occurrence in configured_intrinsic_occurrences()
            if occurrence.provenance.case_id != case_id
        )
        if not external_occurrences:
            raise RegistryOnboardingError(
                "candidate discovery needs at least one configured catalog other "
                f"than the reported case {case_id!r}"
            )
        candidate_index = CanonicalIntrinsicIndex.from_occurrences(
            external_occurrences
        )

    neon = _extract_side(
        case_id=case_id,
        architecture=Architecture.NEON,
        side_profile=profile.neon,
        root=root,
        clang=clang,
    )
    rvv = _extract_side(
        case_id=case_id,
        architecture=Architecture.RVV,
        side_profile=profile.rvv,
        root=root,
        clang=clang,
    )
    sides = [
        _side_report(neon, Architecture.NEON, root, candidate_index),
        _side_report(rvv, Architecture.RVV, root, candidate_index),
    ]
    aggregate_counts = Counter(
        group["status"] for side in sides for group in side["call_groups"]
    )
    return {
        "schema_version": 1,
        "report_kind": "intrinsic-onboarding-candidate-report",
        "case_id": case_id,
        "authoritative": False,
        "semantic_review_inherited": False,
        "kernel_catalog_remains_authoritative": True,
        "excluded_case_catalog": excluded_case_catalog,
        "candidate_index_scope": (
            "configured catalogs excluding the reported case"
            if index is None
            else "caller-supplied canonical index"
        ),
        "binding_authority": (
            "the kernel-scoped intrinsic catalog remains authoritative"
        ),
        "candidate_status_meaning": (
            "source compatibility only; no candidate is an approved semantic binding"
        ),
        "frontend_boundary": {
            "configured_profile_required": True,
            "unconfigured_kernel_is_rejected_before_extraction": True,
            "configured_cases": sorted(FRONTEND_PROFILES),
        },
        "summary": {
            "call_occurrence_count": sum(side["call_occurrence_count"] for side in sides),
            "call_group_count": sum(side["call_group_count"] for side in sides),
            "status_group_counts": {
                status.value: aggregate_counts[status.value] for status in _STATUS_ORDER
            },
        },
        "sides": sides,
    }


def render_onboarding_report(
    report: Mapping[str, Any], *, pretty: bool = True
) -> str:
    """Render stable ASCII JSON for review or tooling."""

    return (
        json.dumps(
            report,
            sort_keys=True,
            indent=2 if pretty else None,
            separators=None if pretty else (",", ":"),
            ensure_ascii=True,
        )
        + "\n"
    )


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--case", required=True)
    parser.add_argument("--repository-root", type=Path, default=_REPOSITORY_ROOT)
    parser.add_argument("--clang", default="clang")
    parser.add_argument("--format", choices=("json",), default="json")
    arguments = parser.parse_args(argv)

    try:
        report = build_onboarding_report(
            arguments.case,
            repository_root=arguments.repository_root,
            clang=arguments.clang,
        )
    except (FrontendError, IntrinsicIndexError, RegistryOnboardingError) as error:
        sys.stderr.write(f"intrinsic onboarding failed: {error}\n")
        return 2

    if arguments.format == "json":
        sys.stdout.write(render_onboarding_report(report))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
