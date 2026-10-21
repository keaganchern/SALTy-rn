from __future__ import annotations

import copy
from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.capabilities import (
    IntrinsicCapability,
    IntrinsicRole,
    LayoutKind,
    LayoutViewCapability,
    ScheduleFamilyCapability,
    ScheduleKind,
)
from workflow.verification.elementwise_compiler.capability_registry import (
    capability_registry_record,
    configured_capabilities,
    verify_capability_refs,
)
from workflow.verification.elementwise_compiler.schema import (
    Architecture,
    ElementwiseSchemaError,
)


D = "0" * 64
E = "1" * 64
ROOT = Path(__file__).resolve().parents[3]


def test_intrinsic_capability_is_global_strict_and_content_addressed() -> None:
    capability = IntrinsicCapability(
        Architecture.NEON,
        "vmaxq_s8",
        "int8x16_t (int8x16_t, int8x16_t)",
        2,
        IntrinsicRole.SEMANTIC,
        D,
        E,
        "SALT.Intrinsics.Neon.vmaxq_s8",
    )
    record = capability.to_record()
    assert IntrinsicCapability.from_record(record) == capability
    assert "case" not in " ".join(record)
    assert capability.ref.sha256 == capability.sha256

    changed = copy.deepcopy(record)
    changed["semantic_symbol"] = "SALT.Intrinsics.Neon.vminq_s8"
    with pytest.raises(ElementwiseSchemaError, match="digest disagrees"):
        IntrinsicCapability.from_record(changed)


def test_exact_descriptor_variants_cannot_share_a_capability_identity() -> None:
    first = IntrinsicCapability(
        Architecture.NEON,
        "vmax_s8",
        "int8x8_t (int8x8_t, int8x8_t)",
        2,
        IntrinsicRole.SEMANTIC,
        D,
        E,
        "SALT.Intrinsics.Neon.vmax_s8",
    )
    second = IntrinsicCapability(
        Architecture.NEON,
        "vmax_s8",
        "int8x8_t (int8x8_t, int8x8_t)",
        2,
        IntrinsicRole.SEMANTIC,
        "2" * 64,
        E,
        "SALT.Intrinsics.Neon.vmax_s8_other",
    )

    assert first.capability_id != second.capability_id


def test_layout_and_schedule_capabilities_round_trip_without_program_names() -> None:
    layout = LayoutViewCapability(
        LayoutKind.SCALAR_LANE,
        D,
        "SALT.Kernel.Schedule.scalarLane",
        E,
    )
    schedule = ScheduleFamilyCapability(
        Architecture.NEON,
        ScheduleKind.FIXED_TAIL,
        E,
        ("SALT.Kernel.Schedule.fixedTail_map",),
        D,
    )
    assert LayoutViewCapability.from_record(layout.to_record()) == layout
    assert ScheduleFamilyCapability.from_record(schedule.to_record()) == schedule
    assert layout.ref.capability_id == "layout:scalar-lane"
    assert schedule.ref.capability_id == "schedule:neon:fixed-tail"


def test_semantic_intrinsic_requires_a_bound_lean_symbol() -> None:
    with pytest.raises(ElementwiseSchemaError, match="semantic symbol"):
        IntrinsicCapability(
            Architecture.RVV,
            "__riscv_vmax_vx_i8m2",
            "vint8m2_t (vint8m2_t, signed char, unsigned long)",
            3,
            IntrinsicRole.SEMANTIC,
            D,
            E,
            None,
        )


def test_global_registry_covers_intrinsic_layout_and_schedule_refs() -> None:
    capabilities = configured_capabilities(ROOT)
    record = capability_registry_record(ROOT)

    assert len(capabilities) == 190
    assert len(record["capabilities"]) == len(capabilities)
    verify_capability_refs(ROOT, tuple(item.ref for item in capabilities))

    changed = list(item.ref for item in capabilities)
    changed[0] = type(changed[0])(
        changed[0].capability_id,
        changed[0].version,
        D,
    )
    with pytest.raises(ElementwiseSchemaError, match="digest mismatch"):
        verify_capability_refs(ROOT, tuple(changed))
