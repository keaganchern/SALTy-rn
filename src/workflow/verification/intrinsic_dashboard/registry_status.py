"""Project configured descriptors into reviewable dashboard records.

The review subject is one canonical descriptor variant, not an intrinsic
spelling.  This distinction matters because the same C spelling can have
case-specific immediate constraints, operand lowering, or even a different
Lean target.  Equal canonical variants used by several cases are merged.

``source_sha256`` binds the descriptor and the cases that use it.
``semantics_sha256`` separately binds the conservative translation, semantic,
and reviewer-authority TCB enumerated in ``tcb_files``.  Neither digest
establishes C/ISA adequacy.
"""

from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable

from ..lean_backend.registry import (
    QS8_VADD_MINMAX_NEON_SPECS,
    QS8_VADD_MINMAX_RVV_SPECS,
)
from ..lean_backend.scaleup_catalog import SCALEUP_CATALOGS
from ..lean_backend.schema import (
    IntrinsicSpec,
    ScheduleIntrinsic,
    SemanticIntrinsic,
    StructuralIntrinsic,
    render_clang_function_type,
)


_LEAN_ROOT = Path("src/verification_bw/lean/SALT")
_BACKEND_ROOT = Path("src/workflow/verification/lean_backend")
_REVIEWER_AUTHORITY = Path("verification/intrinsic-dashboard/reviewers.json")
_REGISTRY_DESCRIPTOR_SOURCE = _BACKEND_ROOT / "registry.py"
_SCALEUP_DESCRIPTOR_SOURCE = _BACKEND_ROOT / "scaleup_catalog.py"
_REGISTRY_SPEC_IDENTITIES = frozenset(
    id(spec) for spec in QS8_VADD_MINMAX_NEON_SPECS + QS8_VADD_MINMAX_RVV_SPECS
)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest_json(value: object) -> str:
    return hashlib.sha256(
        json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()


def _canonical_spec(spec: IntrinsicSpec) -> dict[str, Any]:
    constraints = [
        {
            "argument_index": constraint.argument_index,
            "allowed_values": sorted(
                constraint.allowed_values,
                key=lambda value: (type(value).__name__, value),
            ),
            "erased_from_semantics": constraint.erased_from_semantics,
        }
        for constraint in spec.immediate_constraints
    ]
    record: dict[str, Any] = {
        "architecture": spec.architecture.value,
        "spelling": spec.spelling,
        "kind": spec.kind.value,
        "shape": spec.shape.value,
        "signature": render_clang_function_type(spec.signature),
        "immediate_constraints": constraints,
    }
    if isinstance(spec, SemanticIntrinsic):
        record["lean_name"] = spec.lean_name
        record["lean_arguments"] = [
            {
                "source_index": argument.source_index,
                "transform": argument.transform.value,
            }
            for argument in spec.lean_arguments
        ]
    elif isinstance(spec, StructuralIntrinsic):
        record["operation"] = spec.operation.value
    elif isinstance(spec, ScheduleIntrinsic):
        record["operation"] = spec.operation.value
    else:  # pragma: no cover - closed IntrinsicSpec union
        raise TypeError(f"unsupported intrinsic descriptor: {type(spec)!r}")
    return record


def _configured_cases() -> Iterable[tuple[str, tuple[IntrinsicSpec, ...]]]:
    yield (
        "qs8-vadd-minmax",
        QS8_VADD_MINMAX_NEON_SPECS + QS8_VADD_MINMAX_RVV_SPECS,
    )
    for case_id, catalog in SCALEUP_CATALOGS.items():
        yield case_id, catalog.neon_specs + catalog.rvv_specs


def _descriptor_source(spec: IntrinsicSpec) -> Path:
    """Locate the descriptor definition, preserving ``_existing`` reuse."""

    if id(spec) in _REGISTRY_SPEC_IDENTITIES:
        return _REGISTRY_DESCRIPTOR_SOURCE
    return _SCALEUP_DESCRIPTOR_SOURCE


def _require_files(repository_root: Path, relatives: Iterable[Path]) -> list[Path]:
    paths = sorted({repository_root / relative for relative in relatives})
    missing = [path for path in paths if not path.is_file()]
    if missing:
        rendered = ", ".join(str(path) for path in missing)
        raise FileNotFoundError(f"registered TCB path is missing: {rendered}")
    return paths


def _implementation_paths(repository_root: Path, spec: IntrinsicSpec) -> list[str]:
    """Return short implementation addresses, not the semantic hash closure."""

    if isinstance(spec, SemanticIntrinsic):
        architecture = "Neon" if spec.architecture.value == "neon" else "RVV"
        relatives = [_LEAN_ROOT / "Intrinsics" / f"{architecture}.lean"]
    else:
        relatives = [_BACKEND_ROOT / "case_emit.py"]
    return [
        path.relative_to(repository_root).as_posix()
        for path in _require_files(repository_root, relatives)
    ]


def _translation_tcb_files(repository_root: Path, architecture: str) -> dict[str, str]:
    """Hash the conservative translation, semantics, and authority TCB.

    Every configured descriptor is interpreted by the same Python backend and
    parse facades, so all of those files are intentionally included even when a
    particular case does not exercise each one.  The Lean half includes the
    shared scalar definitions and the architecture-specific intrinsic module.
    Reviewer authority is included so changing the allowlist invalidates old
    approvals.  This is conservative invalidation, not an adequacy claim.
    """

    architecture_module = {"neon": "Neon.lean", "rvv": "RVV.lean"}.get(architecture)
    if architecture_module is None:
        raise ValueError(f"unsupported architecture: {architecture!r}")

    backend = repository_root / _BACKEND_ROOT
    relative_paths = {
        path.relative_to(repository_root)
        for path in backend.rglob("*.py")
        if path.is_file()
    }
    relative_paths.update(
        path.relative_to(repository_root)
        for path in (backend / "facade").rglob("*.h")
        if path.is_file()
    )
    relative_paths.update(
        {
            _LEAN_ROOT / "Basic.lean",
            _LEAN_ROOT / "Intrinsics" / architecture_module,
            _REVIEWER_AUTHORITY,
        }
    )
    paths = _require_files(repository_root, relative_paths)
    return {
        path.relative_to(repository_root).as_posix(): _sha256_file(path)
        for path in paths
    }


def collect_registry_implementations(
    repository_root: Path,
) -> dict[str, dict[str, Any]]:
    """Return one record per canonical descriptor variant.

    Keys and ``subject_id`` have the stable form
    ``architecture:spelling@profile``.  ``profile`` is the complete canonical
    descriptor SHA-256, so equal variants across cases share a subject while
    variants with distinct constraints or Lean lowering cannot be merged.
    """

    grouped: dict[
        tuple[str, str, str],
        list[tuple[str, IntrinsicSpec, dict[str, Any], Path]],
    ] = defaultdict(list)
    for case_id, specs in _configured_cases():
        for spec in specs:
            variant = _canonical_spec(spec)
            canonical = json.dumps(variant, sort_keys=True, separators=(",", ":"))
            grouped[(spec.architecture.value, spec.spelling, canonical)].append(
                (case_id, spec, variant, _descriptor_source(spec))
            )

    tcb_by_architecture = {
        architecture: _translation_tcb_files(repository_root, architecture)
        for architecture in sorted({architecture for architecture, _, _ in grouped})
    }
    result: dict[str, dict[str, Any]] = {}
    for (architecture, spelling, _), occurrences in sorted(grouped.items()):
        cases = sorted({case_id for case_id, _, _, _ in occurrences})
        spec = occurrences[0][1]
        variant = occurrences[0][2]
        if any(candidate != variant for _, _, candidate, _ in occurrences):
            raise AssertionError("canonical descriptor grouping is inconsistent")
        descriptor_paths = [
            path.relative_to(repository_root).as_posix()
            for path in _require_files(
                repository_root,
                {source for _, _, _, source in occurrences},
            )
        ]

        variant_sha256 = _digest_json(variant)
        profile = variant_sha256
        subject_id = f"{architecture}:{spelling}@{profile}"
        source_sha256 = _digest_json(
            {
                "variant": variant,
                "supported_cases": cases,
                "descriptor_paths": descriptor_paths,
            }
        )
        tcb_files = tcb_by_architecture[architecture]
        semantics_sha256 = _digest_json(tcb_files)
        subject_hash = _digest_json(
            {
                "subject_id": subject_id,
                "source_sha256": source_sha256,
                "semantics_sha256": semantics_sha256,
            }
        )
        if subject_id in result:  # pragma: no cover - SHA-256/canonical invariant
            raise AssertionError(f"duplicate descriptor subject: {subject_id}")

        result[subject_id] = {
            "subject_id": subject_id,
            "architecture": architecture,
            "name": spelling,
            "profile": profile,
            "variant_sha256": variant_sha256,
            "variant": variant,
            "descriptor_paths": descriptor_paths,
            "supported_cases": cases,
            "signature": variant["signature"],
            "lean_target": variant.get("lean_name"),
            "lowering_operation": variant.get("operation"),
            "kind": variant["kind"],
            "code": _implementation_paths(repository_root, spec),
            "tcb_files": tcb_files,
            "implementation_status": "case-scoped",
            "scope": "exact configured signature, operands, and constraints only",
            "source_sha256": source_sha256,
            "semantics_sha256": semantics_sha256,
            "subject_hash": subject_hash,
            "adequacy_status": "not-established",
        }
    return result
