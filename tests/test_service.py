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
    status, body = svc.ask({"question": "Do I need consent?"})
    assert status == 200 and body["kind"] == "answer" and body["route"] == "retrieve"
    assert body["answer"].startswith("Body text.")
    assert body["sources"] == [{"label": "GDPR, Article 6 (consolidated text)", "quote": "has given consent"}]
    assert body["seconds"] == pytest.approx(1.501)


@pytest.mark.parametrize("payload", [{}, {"question": ""}, {"question": "   "}, {"question": 5}, "x", None])
def test_a_missing_or_blank_question_is_a_400(payload):
    status, body = service()[0].ask(payload)
    assert status == 400 and "question" in body["error"]


def test_a_very_long_question_is_refused_before_any_model_is_called():
    pipe = FakePipeline()
    status, body = service(pipe)[0].ask({"question": "x" * 1001})
    assert status == 400 and "1000" in body["error"] and pipe.asked == []


def test_the_service_cannot_be_given_a_visitors_address():
    # The limits count questions in total; nothing identifies a visitor, so there is no address to hold.
    import inspect

    assert list(inspect.signature(AskService.ask).parameters) == ["self", "payload"]
    assert list(inspect.signature(RateLimiter.check).parameters) == ["self"]


def test_the_limiter_allows_a_few_questions_a_minute_in_total_then_says_try_later():
    svc, clock = service(per_minute=2, per_day=100)
    assert svc.ask({"question": "a"})[0] == 200
    assert svc.ask({"question": "b"})[0] == 200
    status, body = svc.ask({"question": "c"})
    assert status == 429 and "minute" in body["error"]
    clock.now += 61
    assert svc.ask({"question": "e"})[0] == 200


def test_the_daily_cap_is_a_hard_limit_that_protects_the_budget():
    svc, clock = service(per_minute=100, per_day=3)
    for i in range(3):
        assert svc.ask({"question": f"q{i}"})[0] == 200
    status, body = svc.ask({"question": "late"})
    assert status == 429 and "today" in body["error"]
    clock.now += 86401
    assert svc.ask({"question": "tomorrow"})[0] == 200


def test_a_rejected_question_does_not_use_up_the_allowance():
    svc, _ = service(per_minute=1, per_day=1)
    assert svc.ask({"question": ""})[0] == 400
    assert svc.ask({"question": "real"})[0] == 200


def test_an_error_inside_the_pipeline_is_a_500_that_does_not_leak_details():
    svc, _ = service(FakePipeline(error=RuntimeError("secret key abc in message")))
    status, body = svc.ask({"question": "q"})
    assert status == 500 and "abc" not in json.dumps(body) and "try again" in body["error"].lower()


def test_every_answered_question_is_traced_with_route_passages_and_time_but_not_its_text(tmp_path):
    log = TraceLog(tmp_path / "traces.jsonl")
    svc, _ = service(trace=log)
    svc.ask({"question": "Do I need consent? My name is Ana Pérez."})
    (line,) = (tmp_path / "traces.jsonl").read_text(encoding="utf-8").splitlines()
    row = json.loads(line)
    assert row["kind"] == "answer" and row["route"] == "retrieve"
    assert row["passages"] == ["c1"] and row["seconds"] == pytest.approx(1.501) and "ts" in row
    assert "question" not in row and "Ana" not in line and "consent?" not in line


def test_a_failed_question_is_traced_too_without_its_text(tmp_path):
    log = TraceLog(tmp_path / "t.jsonl")
    svc, _ = service(FakePipeline(error=RuntimeError("boom")), trace=log)
    svc.ask({"question": "secret wording"})
    text = (tmp_path / "t.jsonl").read_text(encoding="utf-8")
    row = json.loads(text)
    assert row["kind"] == "error" and row["error"] == "RuntimeError" and "secret wording" not in text


def test_old_traces_are_deleted_and_recent_ones_kept(tmp_path):
    from datetime import UTC, datetime, timedelta

    path = tmp_path / "traces.jsonl"
    now = datetime(2026, 10, 15, 12, 0, tzinfo=UTC)
    rows = [
        {"ts": (now - timedelta(days=40)).isoformat(), "id": "old"},
        {"ts": (now - timedelta(days=29)).isoformat(), "id": "recent"},
        {"ts": (now - timedelta(days=1)).isoformat(), "id": "new"},
        {"id": "no timestamp"},
    ]
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")
    removed = TraceLog(path).prune(days=30, now=now)
    kept = [json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines()]
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
    status, body = svc.ask({"question": "q"})
    assert status == 503 and "allowance" in body["error"] and "8.5" not in body["error"]


def test_any_other_model_error_stays_a_generic_500():
    from law_assistant.llm.gemini import LLMError

    svc, _ = service(FakePipeline(error=LLMError("HTTP 400: bad request")))
    assert svc.ask({"question": "q"})[0] == 500


def test_a_running_log_deletes_old_traces_by_itself_at_most_once_an_hour(tmp_path):
    from datetime import UTC, datetime, timedelta

    from law_assistant.answer.trace import DEFAULT_RETENTION_DAYS

    assert DEFAULT_RETENTION_DAYS == 30
    now = [datetime(2026, 10, 15, 12, 0, tzinfo=UTC)]
    path = tmp_path / "t.jsonl"
    old = {"ts": (now[0] - timedelta(days=45)).isoformat(), "id": "old"}
    path.write_text(json.dumps(old) + "\n", encoding="utf-8")
    log = TraceLog(path, retention_days=30, clock=lambda: now[0])
    log.record({"id": "first"})  # the first write prunes: the old row goes
    assert [json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines()] == ["first"]
    path.write_text(path.read_text(encoding="utf-8") + json.dumps(old) + "\n", encoding="utf-8")
    now[0] += timedelta(minutes=30)
    log.record({"id": "second"})  # less than an hour since the last prune: nothing is deleted yet
    assert len(path.read_text(encoding="utf-8").splitlines()) == 3
    now[0] += timedelta(hours=2)
    log.record({"id": "third"})  # more than an hour: the old row goes again
    ids = [json.loads(line)["id"] for line in path.read_text(encoding="utf-8").splitlines()]
    assert "old" not in ids and ids[-1] == "third"
