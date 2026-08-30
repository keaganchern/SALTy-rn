"""Canonical global authority for intrinsic, layout, and schedule capabilities."""

from __future__ import annotations

from pathlib import Path
from typing import Mapping, Sequence

from .capabilities import (
    IntrinsicCapability,
    LayoutViewCapability,
    ScheduleFamilyCapability,
)
from .intrinsics import configured_intrinsic_capabilities
from .recognize import configured_layout_schedule_capabilities
from .schema import CapabilityRef, ElementwiseSchemaError, canonical_sha256


Capability = IntrinsicCapability | LayoutViewCapability | ScheduleFamilyCapability


def configured_capabilities(repository_root: str | Path) -> tuple[Capability, ...]:
    """Materialize every capability supported by the current compiler."""

    root = Path(repository_root).resolve()
    layouts, schedules = configured_layout_schedule_capabilities(root)
    capabilities: tuple[Capability, ...] = (
        *configured_intrinsic_capabilities(root),
        *layouts,
        *schedules,
    )
    ordered = tuple(
        sorted(
            capabilities,
            key=lambda item: (item.capability_id, item.version, item.sha256),
        )
    )
    identities = [(item.capability_id, item.version) for item in ordered]
    if len(identities) != len(set(identities)):
        raise ElementwiseSchemaError(
            "global capability registry contains a duplicate id/version"
        )
    return ordered


def capability_registry_record(repository_root: str | Path) -> dict[str, object]:
    """Build one deterministic, content-addressed registry document."""

    record: dict[str, object] = {
        "artifact_kind": "elementwise-capability-registry",
        "schema_version": 2,
        "capabilities": [
            capability.to_record()
            for capability in configured_capabilities(repository_root)
        ],
    }
    record["registry_sha256"] = canonical_sha256(record)
    return record


def verify_capability_refs(
    repository_root: str | Path,
    refs: Sequence[CapabilityRef],
) -> None:
    """Fail closed unless every reference names the exact current global entry."""

    registry: Mapping[tuple[str, int], Capability] = {
        (capability.capability_id, capability.version): capability
        for capability in configured_capabilities(repository_root)
    }
    identities = [(ref.capability_id, ref.version) for ref in refs]
    if identities != sorted(set(identities)):
        raise ElementwiseSchemaError(
            "capability references must be sorted and unique"
        )
    for ref in refs:
        capability = registry.get((ref.capability_id, ref.version))
        if capability is None:
            raise ElementwiseSchemaError(
                f"capability is absent from the global registry: {ref.capability_id}"
            )
        if capability.sha256 != ref.sha256:
            raise ElementwiseSchemaError(
                f"capability digest mismatch: {ref.capability_id}"
            )
