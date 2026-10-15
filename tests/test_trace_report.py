"""Tests for the summary of the trace log: what the live demo is doing, in numbers."""

from __future__ import annotations

import json

from law_assistant.answer.trace_report import load_rows, summarise


def row(kind="answer", route="retrieve", seconds=2.0, language="en", invalid=0, question="q?", **extra):
    return {
        "ts": "2026-10-15T10:00:00+00:00", "question": question, "kind": kind, "route": route,
        "language": language, "seconds": seconds, "invalid_citations": invalid,
        "timings": {"generate": seconds * 0.8, "retrieve": 0.1}, **extra,
    }  # fmt: skip


def test_counts_by_outcome_route_and_language():
    s = summarise(
        [row(), row(kind="refused", route="refuse"), row(kind="table", route="table", language="es")]
    )
    assert s["questions"] == 3
    assert s["by_kind"] == {"answer": 1, "refused": 1, "table": 1}
    assert s["by_language"] == {"en": 2, "es": 1}


def test_latency_percentiles_use_only_questions_that_were_timed():
    s = summarise([row(seconds=s) for s in (1, 2, 3, 4, 10)] + [{"kind": "error", "question": "x"}])
    assert s["latency"]["median"] == 3 and s["latency"]["p95"] == 10 and s["latency"]["count"] == 5


def test_the_share_of_questions_declined_and_of_answers_with_dropped_quotations():
    s = summarise([row(), row(), row(kind="abstained"), row(invalid=2)])
    assert s["abstained_share"] == 0.25 and s["answers_with_dropped_quotes"] == 1


def test_the_slowest_step_is_named():
    assert summarise([row(seconds=5)])["slowest_step"] == "generate"


def test_an_empty_log_gives_zeros_not_an_error():
    s = summarise([])
    assert s["questions"] == 0 and s["latency"]["count"] == 0 and s["abstained_share"] == 0


def test_rows_are_read_from_a_file_and_bad_lines_are_skipped(tmp_path):
    path = tmp_path / "t.jsonl"
    path.write_text(
        json.dumps(row()) + "\nnot json\n\n" + json.dumps(row(kind="error")) + "\n", encoding="utf-8"
    )
    assert len(load_rows(path)) == 2 and load_rows(tmp_path / "missing.jsonl") == []
