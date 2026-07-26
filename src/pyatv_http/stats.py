from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass(frozen=True)
class CommandRecord:
    device: str
    command: str
    ok: bool
    detail: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))


class StatsStore:
    def __init__(self, history_size: int) -> None:
        self._records: deque[CommandRecord] = deque(maxlen=history_size)
        self._totals: dict[str, dict[str, int]] = {}

    def record(self, device: str, command: str, *, ok: bool, detail: str) -> None:
        self._records.appendleft(
            CommandRecord(device=device, command=command, ok=ok, detail=detail)
        )
        counts = self._totals.setdefault(device, {"success": 0, "error": 0})
        counts["success" if ok else "error"] += 1

    def recent(self) -> list[CommandRecord]:
        return list(self._records)

    def totals(self) -> dict[str, dict[str, int]]:
        global_totals = {"success": 0, "error": 0}
        for counts in self._totals.values():
            global_totals["success"] += counts["success"]
            global_totals["error"] += counts["error"]
        return {**self._totals, "_global": global_totals}
