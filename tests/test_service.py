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
