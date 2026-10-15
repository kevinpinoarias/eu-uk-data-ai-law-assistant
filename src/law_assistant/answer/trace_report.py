"""
Summarise the trace log of a running demo: `python -m law_assistant.answer.trace_report [path]`.

How many questions, how they ended (answer, table figure, refusal, decline, error), what languages, how
long they took (median and 95th percentile, over the questions that were timed), how many answers had a
quotation dropped by the check, which step is slowest on average. This is how latency and failure rates are
read from real traffic.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from statistics import mean, median
from typing import Any

from law_assistant import settings


def load_rows(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            rows.append(json.loads(line))
        except ValueError:
            continue
    return rows


def _percentile(ordered: list[float], p: float) -> float:
    return ordered[min(len(ordered) - 1, int(p * len(ordered)))]


def summarise(rows: list[dict[str, Any]]) -> dict[str, Any]:
    times = sorted(r["seconds"] for r in rows if isinstance(r.get("seconds"), int | float))
    steps: dict[str, list[float]] = {}
    for r in rows:
        for name, seconds in (r.get("timings") or {}).items():
            steps.setdefault(name, []).append(seconds)
    kinds = Counter(r.get("kind", "unknown") for r in rows)
    answers = [r for r in rows if r.get("kind") == "answer"]
    return {
        "questions": len(rows),
        "by_kind": dict(kinds),
        "by_route": dict(Counter(r.get("route") for r in rows if r.get("route"))),
        "by_language": dict(Counter(r.get("language") for r in rows if r.get("language"))),
        "latency": {
            "count": len(times),
            "median": median(times) if times else 0,
            "p95": _percentile(times, 0.95) if times else 0,
            "slowest": times[-1] if times else 0,
        },
        "abstained_share": kinds.get("abstained", 0) / len(rows) if rows else 0,
        "answers_with_dropped_quotes": sum(1 for r in answers if r.get("invalid_citations")),
        "slowest_step": max(steps, key=lambda n: mean(steps[n])) if steps else None,
    }


def main(argv: list[str]) -> int:
    path = Path(argv[0]) if argv else settings.PROJECT_ROOT / "data" / "traces" / "traces.jsonl"
    s = summarise(load_rows(path))
    print(f"{s['questions']} questions in {path}")
    print("outcomes:", s["by_kind"], "| routes:", s["by_route"], "| languages:", s["by_language"])
    lat = s["latency"]
    print(
        f"latency over {lat['count']} timed questions: median {lat['median']:.2f} s, "
        f"p95 {lat['p95']:.2f} s, slowest {lat['slowest']:.2f} s"
    )
    print(
        f"declined {s['abstained_share']:.0%}; answers with a dropped quotation "
        f"{s['answers_with_dropped_quotes']}; slowest step {s['slowest_step']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
