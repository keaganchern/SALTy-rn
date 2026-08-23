"""Atomic per-agent activity records consumed by the live dashboard."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping


_AGENT_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,79}$")
_STATUSES = frozenset({"running", "idle", "completed", "failed", "blocked"})


class ActivityError(ValueError):
    """An activity update is malformed or cannot be persisted."""


def _timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


@dataclass(frozen=True, slots=True)
class ActivityRecord:
    agent_id: str
    name: str
    status: str
    task: str
    current_item: str = ""
    completed: int = 0
    total: int = 0
    updated_at: str = ""

    def __post_init__(self) -> None:
        if _AGENT_ID_RE.fullmatch(self.agent_id) is None:
            raise ActivityError(f"invalid agent id: {self.agent_id!r}")
        if not self.name.strip() or not self.task.strip():
            raise ActivityError("agent name and task must not be empty")
        if self.status not in _STATUSES:
            raise ActivityError(f"invalid activity status: {self.status!r}")
        if type(self.completed) is not int or type(self.total) is not int:
            raise ActivityError("activity progress must be integers")
        if self.completed < 0 or self.total < 0 or self.completed > self.total:
            raise ActivityError(
                "activity progress must satisfy 0 <= completed <= total"
            )
        if self.updated_at:
            try:
                parsed = datetime.fromisoformat(self.updated_at.replace("Z", "+00:00"))
            except ValueError as error:
                raise ActivityError("updated_at must be ISO-8601") from error
            if parsed.tzinfo is None:
                raise ActivityError("updated_at must include a timezone")

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.agent_id,
            "name": self.name,
            "status": self.status,
            "task": self.task,
            "current_item": self.current_item,
            "updated_at": self.updated_at or _timestamp(),
            "progress": {"completed": self.completed, "total": self.total},
        }

    @classmethod
    def from_dict(cls, value: Mapping[str, Any]) -> "ActivityRecord":
        expected = {
            "id",
            "name",
            "status",
            "task",
            "current_item",
            "updated_at",
            "progress",
        }
        if set(value) != expected:
            raise ActivityError(
                f"invalid activity fields: {sorted(set(value) ^ expected)}"
            )
        progress = value["progress"]
        if not isinstance(progress, Mapping) or set(progress) != {"completed", "total"}:
            raise ActivityError("activity progress must contain completed and total")
        return cls(
            agent_id=str(value["id"]),
            name=str(value["name"]),
            status=str(value["status"]),
            task=str(value["task"]),
            current_item=str(value["current_item"]),
            completed=progress["completed"],
            total=progress["total"],
            updated_at=str(value["updated_at"]),
        )


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="ascii",
            newline="",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as stream:
            temporary = Path(stream.name)
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
    except OSError as error:
        raise ActivityError(f"cannot persist activity {path}: {error}") from error
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def save_activity(directory: Path, record: ActivityRecord) -> Path:
    path = directory / f"{record.agent_id}.json"
    content = (
        json.dumps(record.to_dict(), ensure_ascii=True, indent=2, sort_keys=True) + "\n"
    )
    _atomic_write(path, content)
    return path


def load_activity(directory: Path) -> tuple[ActivityRecord, ...]:
    if not directory.exists():
        return ()
    records: list[ActivityRecord] = []
    for path in sorted(directory.glob("*.json")):
        try:
            value = json.loads(path.read_text(encoding="ascii"))
        except (OSError, UnicodeError, json.JSONDecodeError) as error:
            raise ActivityError(f"cannot read activity {path}: {error}") from error
        if not isinstance(value, Mapping):
            raise ActivityError(f"activity {path} must contain an object")
        record = ActivityRecord.from_dict(value)
        if path.stem != record.agent_id:
            raise ActivityError(
                f"activity filename {path.name} does not match id {record.agent_id}"
            )
        records.append(record)
    return tuple(records)
