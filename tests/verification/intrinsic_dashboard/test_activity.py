from pathlib import Path

import pytest

from src.workflow.verification.intrinsic_dashboard.activity import (
    ActivityError,
    ActivityRecord,
    load_activity,
    save_activity,
)


def test_activity_round_trip_is_atomic_and_sorted(tmp_path: Path) -> None:
    second = ActivityRecord(
        agent_id="translator-2",
        name="Translator 2",
        status="running",
        task="Translate RVV intrinsics",
        current_item="__riscv_vadd_vv_i8m1",
        completed=2,
        total=5,
        updated_at="2026-08-23T12:00:00+00:00",
    )
    first = ActivityRecord(
        agent_id="reviewer-1",
        name="Reviewer 1",
        status="idle",
        task="Review intrinsic semantics",
        updated_at="2026-08-23T12:00:00+00:00",
    )

    save_activity(tmp_path, second)
    save_activity(tmp_path, first)
    assert [record.agent_id for record in load_activity(tmp_path)] == [
        "reviewer-1",
        "translator-2",
    ]
    assert list(tmp_path.glob(".*.tmp")) == []


def test_activity_rejects_invalid_progress_and_identity() -> None:
    with pytest.raises(ActivityError, match="agent id"):
        ActivityRecord("../agent", "Agent", "running", "Task")
    with pytest.raises(ActivityError, match="0 <= completed"):
        ActivityRecord("agent", "Agent", "running", "Task", completed=2, total=1)
