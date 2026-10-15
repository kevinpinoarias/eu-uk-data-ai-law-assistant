"""
The service layer: what a web page or an API call talks to. It checks the input, limits how often one
client and all clients together may ask (every question costs model calls, which cost money or free-tier
allowance), runs the pipeline, turns the result into JSON, and writes a trace. It knows nothing about HTTP,
so the same code can sit behind the standard-library server in `serve.py` or a framework later.
"""

from __future__ import annotations

import threading
import time
from collections import defaultdict, deque
from collections.abc import Callable
from typing import Any

from law_assistant.answer.trace import TraceLog

MAX_QUESTION_CHARS = 1000


class RateLimiter:
    """At most `per_minute` questions per client in any 60 seconds and `per_day` from everyone in 24 hours."""

    def __init__(
        self, *, per_minute: int = 6, per_day: int = 300, clock: Callable[[], float] = time.monotonic
    ) -> None:
        self._per_minute, self._per_day, self._clock = per_minute, per_day, clock
        self._by_client: dict[str, deque[float]] = defaultdict(deque)
        self._day: deque[float] = deque()
        self._lock = threading.Lock()

    def check(self, client: str) -> str | None:
        """Reserve a place and return None, or return why the question must wait."""
        now = self._clock()
        with self._lock:
            recent = self._by_client[client]
            while recent and now - recent[0] >= 60:
                recent.popleft()
            while self._day and now - self._day[0] >= 86400:
                self._day.popleft()
            if len(self._day) >= self._per_day:
                return "The limit of questions for today has been reached; please try again tomorrow."
            if len(recent) >= self._per_minute:
                return "Too many questions in a minute; please wait a moment and try again."
            recent.append(now)
            self._day.append(now)
            return None


class AskService:
    def __init__(
        self, pipeline, *, trace: TraceLog | None = None, limiter: RateLimiter | None = None
    ) -> None:
        self._pipeline, self._trace, self._limiter = pipeline, trace, limiter or RateLimiter()

    def ask(self, payload: Any, *, client: str) -> tuple[int, dict[str, Any]]:
        question = payload.get("question") if isinstance(payload, dict) else None
        if not isinstance(question, str) or not question.strip():
            return 400, {"error": "Send a JSON object with a non-empty 'question'."}
        question = question.strip()
        if len(question) > MAX_QUESTION_CHARS:
            return 400, {"error": f"The question is too long (at most {MAX_QUESTION_CHARS} characters)."}
        wait = self._limiter.check(client)
        if wait:
            return 429, {"error": wait}
        try:
            result = self._pipeline.ask(question)
        except Exception as error:  # the details stay in the trace; the user sees a plain message
            self._record({"question": question, "kind": "error", "error": type(error).__name__})
            return 500, {"error": "Something went wrong while answering. Please try again later."}
        seconds = round(sum(result.timings.values()), 3)
        self._record(
            {
                "question": question,
                "kind": result.kind,
                "route": result.trace.get("route"),
                "reason": result.reason,
                "language": result.language,
                "passages": result.trace.get("passages", []),
                "fact_key": result.trace.get("fact_key"),
                "invalid_citations": len(result.trace.get("invalid_citations", [])),
                "timings": {k: round(v, 3) for k, v in result.timings.items()},
                "seconds": seconds,
            }
        )
        return 200, {
            "kind": result.kind,
            "route": result.route,
            "language": result.language,
            "answer": result.text,
            "sources": [{"label": s.label, "quote": s.quote} for s in result.sources],
            "seconds": seconds,
        }

    def _record(self, row: dict[str, Any]) -> None:
        if self._trace:
            self._trace.record(row)
