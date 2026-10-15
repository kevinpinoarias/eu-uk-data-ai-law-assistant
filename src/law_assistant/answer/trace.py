"""
A trace of every question the service handles: what route it took, which passages were retrieved, how
long each step took and how it ended. This is how a retrieval system is debugged after it ships (why did
this question get no answer?) and how latency is measured on real traffic. The client's address is never
stored; the question text is, because the traces are the only way to see what people ask, so a deployment
that logs them must say so.
"""

from __future__ import annotations

import json
import threading
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class TraceLog:
    def __init__(self, path: Path) -> None:
        self._path, self._lock = path, threading.Lock()

    def record(self, row: dict[str, Any]) -> None:
        row = {"ts": datetime.now(UTC).isoformat(timespec="seconds"), **row}
        line = json.dumps(row, ensure_ascii=False, default=str)
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8", newline="\n") as f:
                f.write(line + "\n")
