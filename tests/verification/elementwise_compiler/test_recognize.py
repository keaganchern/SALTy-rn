from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from workflow.verification.elementwise_compiler.capabilities import ScheduleKind
from workflow.verification.elementwise_compiler.recognize import (
    RecognitionError,
    recognize_pair,
)
from workflow.verification.lean_backend.frontend import parse_kernel_explicit
from workflow.verification.lean_backend.schema import Architecture


ROOT = Path(__file__).resolve().parents[3]
FACADE_ROOT = ROOT / "src/workflow/verification/lean_backend/facade"
pytestmark = pytest.mark.skipif(shutil.which("clang") is None, reason="system clang required")


def _parse(path: Path, architecture: Architecture, facade: Path):
    return parse_kernel_explicit(
        path,
        architecture=architecture,
        function_name="test_neon" if architecture is Architecture.NEON else "test_rvv",
        facade=facade,
        target_triple=(
            "aarch64-none-elf"
            if architecture is Architecture.NEON
            else "riscv64-none-elf"
        ),
    )


def _pair(case: str, *, neon_path: Path | None = None):
    facade = FACADE_ROOT / f"{case.replace('-', '_')}.h"
    return (
        _parse(
            neon_path or ROOT / "kernels/source" / f"{case}.c",
            Architecture.NEON,
            facade,
        ),
        _parse(ROOT / "kernels/target" / f"{case}.c", Architecture.RVV, facade),
    )


@pytest.mark.parametrize(
    ("case", "arity", "local_count"),
    (
        ("qs8-vcvt", 1, 2),
        ("qs8-vlrelu", 1, 2),
        ("qu8-vadd-minmax", 2, 0),
    ),
)
def test_scalar_fixed_tail_and_rvv_are_recognized_from_structure(
    case: str, arity: int, local_count: int
) -> None:
    result = recognize_pair(*_pair(case), repository_root=ROOT)
    assert len(result.inputs) == arity
    assert result.neon.kind is ScheduleKind.FIXED_TAIL
    assert result.neon.lanes == 8
    assert result.neon.store_widths == (4, 2, 1)
    assert result.schedules[1].capability.capability_id == "schedule:rvv:rvv-strip-mine"
    assert len(result.local_assertions) == local_count
    assert result.contracts.neon == result.contracts.rvv


@pytest.mark.parametrize(
    ("case", "phase_widths"),
    (("qs8-vadd-minmax", (16, 8)), ("s8-vclamp", (64, 8))),
)
def test_two_phase_schedule_is_selected_from_control_structure(
    case: str, phase_widths: tuple[int, int]
) -> None:
    result = recognize_pair(*_pair(case), repository_root=ROOT)

    assert result.neon.kind is ScheduleKind.MULTI_PHASE
    assert result.neon.phase_widths == phase_widths
    assert result.neon.store_widths == (4, 2, 1)
    assert result.schedules[0].capability.capability_id == "schedule:neon:multi-phase"


def test_tail_store_plan_mutation_fails_family_recognition(tmp_path: Path) -> None:
    source = ROOT / "kernels/source/qs8-vcvt.c"
    mutated = tmp_path / "arbitrary.c"
    mutated.write_text(
        source.read_text(encoding="utf-8").replace(
            "batch & (2 * sizeof(int8_t))", "batch & (3 * sizeof(int8_t))", 1
        ),
        encoding="utf-8",
    )
    with pytest.raises(RecognitionError, match="tail"):
        recognize_pair(*_pair("qs8-vcvt", neon_path=mutated), repository_root=ROOT)


def test_unrelated_local_assertion_is_not_silently_consumed(tmp_path: Path) -> None:
    source = ROOT / "kernels/source/qs8-vcvt.c"
    mutated = tmp_path / "random.c"
    mutated.write_text(
        source.read_text(encoding="utf-8").replace(
            "assert(batch <= 7 * sizeof(int8_t));",
            "assert(batch <= 6 * sizeof(int8_t));",
            1,
        ),
        encoding="utf-8",
    )
    with pytest.raises(RecognitionError, match="local assertion"):
        recognize_pair(*_pair("qs8-vcvt", neon_path=mutated), repository_root=ROOT)


def test_entry_contract_mutation_returns_precise_state(tmp_path: Path) -> None:
    source = ROOT / "kernels/source/qs8-vcvt.c"
    mutated = tmp_path / "contract.c"
    mutated.write_text(
        source.read_text(encoding="utf-8").replace(
            "assert(batch != 0);", "assert(batch >= 8);", 1
        ),
        encoding="utf-8",
    )
    with pytest.raises(RecognitionError) as failure:
        recognize_pair(*_pair("qs8-vcvt", neon_path=mutated), repository_root=ROOT)
    assert failure.value.status == "entry-contract-mismatch"
