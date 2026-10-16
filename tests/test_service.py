"""
Tests for the service layer around the pipeline: input checks, a rate limiter, the per-question trace log and
the JSON the web page receives. The pipeline is a fake, so no model, key or network is involved.
"""

from __future__ import annotations

import json

import pytest

from law_assistant.answer.pipeline import Result, Source
from law_assistant.answer.service import AskService, RateLimiter
from law_assistant.answer.trace import TraceLog


def result(kind="answer"):
    return Result(
        kind=kind, text="Body text.\n\nSources:\n- GDPR, Article 6: “x”", language="en", route="retrieve",
        sources=[Source("GDPR, Article 6 (consolidated text)", "c1", "has given consent", ("eu-gdpr/art-6/1",))],
        timings={"understand": 0.001, "generate": 1.5},
        trace={"route": "retrieve", "passages": ["c1"], "invalid_citations": [], "fact_key": None},
    )  # fmt: skip


class FakePipeline:
    def __init__(self, res=None, error=None):
        self.res, self.error, self.asked = res or result(), error, []

    def ask(self, question):
        self.asked.append(question)
        if self.error:
            raise self.error
        return self.res


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def service(pipeline=None, clock=None, trace=None, per_minute=3, per_day=5):
    clock = clock or Clock()
    return AskService(
        pipeline or FakePipeline(), trace=trace,
        limiter=RateLimiter(per_minute=per_minute, per_day=per_day, clock=clock),
    ), clock  # fmt: skip


def test_a_good_question_returns_the_answer_the_sources_and_the_route():
    svc, _ = service()
    status, body = svc.ask({"question": "Do I need consent?"}, client="1.2.3.4")
    assert status == 200 and body["kind"] == "answer" and body["route"] == "retrieve"
    assert body["answer"].startswith("Body text.")
    assert body["sources"] == [{"label": "GDPR, Article 6 (consolidated text)", "quote": "has given consent"}]
    assert body["seconds"] == pytest.approx(1.501)


@pytest.mark.parametrize("payload", [{}, {"question": ""}, {"question": "   "}, {"question": 5}, "x", None])
def test_a_missing_or_blank_question_is_a_400(payload):
    status, body = service()[0].ask(payload, client="c")
    assert status == 400 and "question" in body["error"]


def test_a_very_long_question_is_refused_before_any_model_is_called():
    pipe = FakePipeline()
    status, body = service(pipe)[0].ask({"question": "x" * 1001}, client="c")
    assert status == 400 and "1000" in body["error"] and pipe.asked == []


def test_the_limiter_allows_a_few_questions_a_minute_per_client_then_says_try_later():
    svc, clock = service(per_minute=2, per_day=100)
    assert svc.ask({"question": "a"}, client="c")[0] == 200
    assert svc.ask({"question": "b"}, client="c")[0] == 200
    status, body = svc.ask({"question": "c"}, client="c")
    assert status == 429 and "minute" in body["error"]
    assert svc.ask({"question": "d"}, client="other")[0] == 200  # another client is unaffected
    clock.now += 61
    assert svc.ask({"question": "e"}, client="c")[0] == 200


def test_the_daily_cap_protects_the_budget_across_all_clients():
    svc, clock = service(per_minute=100, per_day=3)
    for i in range(3):
        assert svc.ask({"question": f"q{i}"}, client=f"c{i}")[0] == 200
    status, body = svc.ask({"question": "late"}, client="new")
    assert status == 429 and "today" in body["error"]
    clock.now += 86401
    assert svc.ask({"question": "tomorrow"}, client="new")[0] == 200


def test_a_rejected_question_does_not_use_up_the_allowance():
    svc, _ = service(per_minute=1, per_day=1)
    assert svc.ask({"question": ""}, client="c")[0] == 400
    assert svc.ask({"question": "real"}, client="c")[0] == 200


def test_an_error_inside_the_pipeline_is_a_500_that_does_not_leak_details():
    svc, _ = service(FakePipeline(error=RuntimeError("secret key abc in message")))
    status, body = svc.ask({"question": "q"}, client="c")
    assert status == 500 and "abc" not in json.dumps(body) and "try again" in body["error"].lower()


def test_every_answered_question_is_written_to_the_trace_with_route_passages_and_time(tmp_path):
    log = TraceLog(tmp_path / "traces.jsonl")
    svc, _ = service(trace=log)
    svc.ask({"question": "Do I need consent?"}, client="1.2.3.4")
    (line,) = (tmp_path / "traces.jsonl").read_text(encoding="utf-8").splitlines()
    row = json.loads(line)
    assert row["question"] == "Do I need consent?" and row["kind"] == "answer" and row["route"] == "retrieve"
    assert row["passages"] == ["c1"] and row["seconds"] == pytest.approx(1.501) and "ts" in row
    assert "1.2.3.4" not in line  # the client address is not stored


def test_a_failed_question_is_traced_too(tmp_path):
    log = TraceLog(tmp_path / "t.jsonl")
    svc, _ = service(FakePipeline(error=RuntimeError("boom")), trace=log)
    svc.ask({"question": "q"}, client="c")
    row = json.loads((tmp_path / "t.jsonl").read_text(encoding="utf-8"))
    assert row["kind"] == "error" and row["error"] == "RuntimeError"


def test_old_traces_are_deleted_and_recent_ones_kept(tmp_path):
    from datetime import UTC, datetime, timedelta

    path = tmp_path / "traces.jsonl"
    now = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
    rows = [
        {"ts": (now - timedelta(days=40)).isoformat(), "question": "old"},
        {"ts": (now - timedelta(days=29)).isoformat(), "question": "recent"},
        {"ts": (now - timedelta(days=1)).isoformat(), "question": "new"},
        {"question": "no timestamp"},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    removed = TraceLog(path).prune(days=30, now=now)
    kept = [json.loads(line)["question"] for line in path.read_text(encoding="utf-8").splitlines()]
    assert removed == 2 and kept == [
        "recent",
        "new",
    ]  # a row with no timestamp cannot be aged, so it goes too


def test_pruning_a_missing_file_does_nothing(tmp_path):
    assert TraceLog(tmp_path / "none.jsonl").prune(days=30) == 0


def test_a_used_up_model_allowance_is_a_503_with_a_plain_message_not_a_generic_500():
    from law_assistant.llm.gemini import LLMError

    quota = LLMError("HTTP 429 from generateContent: the quota is used up and resets in about 8.5 hours")
    svc, _ = service(FakePipeline(error=quota))
    status, body = svc.ask({"question": "q"}, client="c")
    assert status == 503 and "allowance" in body["error"] and "8.5" not in body["error"]


def test_any_other_model_error_stays_a_generic_500():
    from law_assistant.llm.gemini import LLMError

    svc, _ = service(FakePipeline(error=LLMError("HTTP 400: bad request")))
    assert svc.ask({"question": "q"}, client="c")[0] == 500


def test_a_running_log_deletes_old_traces_by_itself_at_most_once_an_hour(tmp_path):
    from datetime import UTC, datetime, timedelta

    from law_assistant.answer.trace import DEFAULT_RETENTION_DAYS

    assert DEFAULT_RETENTION_DAYS == 30
    now = [datetime(2026, 10, 15, 12, 0, tzinfo=UTC)]
    path = tmp_path / "t.jsonl"
    old = {"ts": (now[0] - timedelta(days=45)).isoformat(), "question": "old"}
    path.write_text(json.dumps(old) + "\n", encoding="utf-8")
    log = TraceLog(path, retention_days=30, clock=lambda: now[0])
    log.record({"question": "first"})  # the first write prunes: the old row goes
    assert [json.loads(line)["question"] for line in path.read_text(encoding="utf-8").splitlines()] == [
        "first"
    ]
    path.write_text(path.read_text(encoding="utf-8") + json.dumps(old) + "\n", encoding="utf-8")
    now[0] += timedelta(minutes=30)
    log.record({"question": "second"})  # less than an hour since the last prune: nothing is deleted yet
    assert len(path.read_text(encoding="utf-8").splitlines()) == 3
    now[0] += timedelta(hours=2)
    log.record({"question": "third"})  # more than an hour: the old row goes again
    questions = [json.loads(line)["question"] for line in path.read_text(encoding="utf-8").splitlines()]
    assert "old" not in questions and questions[-1] == "third"
