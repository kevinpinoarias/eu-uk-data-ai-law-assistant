"""
A trace of every question the service handles: what route it took, which passages were retrieved, how
long each step took and how it ended. This is how a retrieval system is debugged after it ships (why did
this question get no answer?) and how latency is measured on real traffic. Neither the client's address nor
the text of the question is stored (a question can contain personal data, and the traces only need to show
how the system behaved), so a row cannot identify anyone. Rows are still deleted after a retention period.
"""

from __future__ import annotations

import json
import threading
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

DEFAULT_RETENTION_DAYS = 30  # the privacy notice says 30 days; a test ties the two together
PRUNE_EVERY = timedelta(hours=1)


class TraceLog:
    """Appends one JSON line per question. With `retention_days` set, rows older than that are deleted by the
    log itself (at the first write and then at most once an hour), so a server that never restarts still
    keeps its promise about how long questions are kept."""

    def __init__(
        self,
        path: Path,
        *,
        retention_days: int | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        self._path, self._lock = path, threading.Lock()
        self._retention_days = retention_days
        self._clock = clock or (lambda: datetime.now(UTC))
        self._last_prune: datetime | None = None

    def record(self, row: dict[str, Any]) -> None:
        now = self._clock()
        if self._retention_days is not None and (
            self._last_prune is None or now - self._last_prune >= PRUNE_EVERY
        ):
            self.prune(days=self._retention_days, now=now)
            self._last_prune = now
        row = {"ts": now.isoformat(timespec="seconds"), **row}
        line = json.dumps(row, ensure_ascii=False, default=str)
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(line + "\n")

    def prune(self, *, days: int, now: datetime | None = None) -> int:
        """Delete traces older than `days` days (and any row that cannot be dated); return how many went.
        Questions can contain personal data, so they are not kept longer than they are needed."""
        if not self._path.is_file():
            return 0
        cutoff = (now or datetime.now(UTC)) - timedelta(days=days)
        kept, removed = [], 0
        with self._lock:
            for line in self._path.read_text(encoding="utf-8").splitlines():
                if not line.strip():
                    continue
                try:
                    stamp = datetime.fromisoformat(json.loads(line)["ts"])
                except (ValueError, KeyError, TypeError):
                    stamp = None
                if stamp is not None and stamp >= cutoff:
                    kept.append(line)
                else:
                    removed += 1
            text = "".join(line + "\n" for line in kept)
            self._path.write_text(text, encoding="utf-8", newline="\n")
        return removed
