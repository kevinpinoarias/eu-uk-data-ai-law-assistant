"""
Tests for the Gemini text client (no network: the transport is a fake) and its answer cache, and for the
question rewriter built on it.
"""

from __future__ import annotations

import json

import pytest

from law_assistant.llm.gemini import CachedGenerator, GeminiGenerator, LLMError
from law_assistant.retrieval.rewriter import INSTRUCTIONS, LLMRewriter


def reply(text="hello", prompt_tokens=10, output_tokens=3):
    return 200, json.dumps(
        {
            "candidates": [{"content": {"parts": [{"text": text}]}, "finishReason": "STOP"}],
            "usageMetadata": {"promptTokenCount": prompt_tokens, "candidatesTokenCount": output_tokens},
        }
    ).encode()


class FakeTransport:
    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def __call__(self, url, headers, body):
        self.calls.append((url, headers, json.loads(body)))
        return self.replies.pop(0) if len(self.replies) > 1 else self.replies[0]


def generator(replies, **kwargs):
    sleeps = []
    g = GeminiGenerator(
        "SECRET-KEY", transport=FakeTransport(replies), sleep=sleeps.append, model="m1", **kwargs
    )
    return g, sleeps


def test_the_key_goes_in_a_header_only_and_the_request_has_the_system_text_and_settings():
    g, _ = generator([reply("ok")])
    assert g.generate("the question", system="be brief", temperature=0.0, max_output_tokens=50) == "ok"
    url, headers, body = g._transport.calls[0]
    assert url.endswith("/models/m1:generateContent") and "SECRET-KEY" not in url
    assert headers["x-goog-api-key"] == "SECRET-KEY"
    assert body["contents"][0]["parts"][0]["text"] == "the question"
    assert body["systemInstruction"]["parts"][0]["text"] == "be brief"
    assert body["generationConfig"]["temperature"] == 0.0
    assert body["generationConfig"]["maxOutputTokens"] == 50
    assert "SECRET-KEY" not in repr(g)


def test_usage_and_the_time_of_each_call_are_recorded():
    g, _ = generator([reply("ok", 12, 4)])
    g.generate("q")
    (call,) = g.calls
    assert (call.prompt_tokens, call.output_tokens) == (12, 4) and call.seconds >= 0


def test_a_rate_limit_is_waited_out_and_retried():
    g, sleeps = generator([(429, b"{}"), reply("fine")])
    assert g.generate("q") == "fine"
    assert len(g._transport.calls) == 2 and len(sleeps) == 1 and sleeps[0] >= 15


def test_giving_up_raises_an_error_that_does_not_contain_the_key():
    g, _ = generator([(500, b"server broke")], max_retries=2)
    with pytest.raises(LLMError, match="HTTP 500") as info:
        g.generate("q")
    assert "SECRET-KEY" not in str(info.value)
    assert len(g._transport.calls) == 3


def test_a_client_error_is_not_retried():
    g, sleeps = generator([(400, b"bad request")])
    with pytest.raises(LLMError, match="HTTP 400"):
        g.generate("q")
    assert len(g._transport.calls) == 1 and sleeps == []


def test_a_reply_without_text_is_an_error():
    blocked = 200, json.dumps({"candidates": [{"finishReason": "SAFETY"}]}).encode()
    g, _ = generator([blocked])
    with pytest.raises(LLMError, match="SAFETY"):
        g.generate("q")


def test_the_cache_answers_a_repeat_without_calling_the_model_and_survives_a_restart(tmp_path):
    path = tmp_path / "cache.jsonl"
    g, _ = generator([reply("first"), reply("second")])
    cached = CachedGenerator(g, path)
    assert cached.generate("q", system="s") == "first"
    assert cached.generate("q", system="s") == "first"
    assert cached.generate("q2", system="s") == "second"
    assert len(g._transport.calls) == 2
    g2, _ = generator([reply("never")])
    assert CachedGenerator(g2, path).generate("q", system="s") == "first"
    assert g2._transport.calls == []


def test_a_change_in_system_text_or_settings_is_a_different_cache_entry(tmp_path):
    g, _ = generator([reply("a"), reply("b"), reply("c")])
    cached = CachedGenerator(g, tmp_path / "c.jsonl")
    cached.generate("q", system="s1")
    cached.generate("q", system="s2")
    cached.generate("q", system="s1", temperature=0.5)
    assert len(g._transport.calls) == 3


def test_the_rewriter_sends_the_instructions_and_the_question_and_cleans_the_reply(tmp_path):
    g, _ = generator([reply('  "RGPD: derecho de acceso\n del interesado"  ')])
    rewriter = LLMRewriter(CachedGenerator(g, tmp_path / "c.jsonl"))
    assert rewriter.rewrite("¿Puedo ver mis datos?") == "RGPD: derecho de acceso del interesado"
    _, _, body = g._transport.calls[0]
    assert body["systemInstruction"]["parts"][0]["text"] == INSTRUCTIONS
    assert "¿Puedo ver mis datos?" in body["contents"][0]["parts"][0]["text"]
    assert body["generationConfig"]["temperature"] == 0.0


def test_the_instructions_forbid_article_numbers_and_ask_for_the_questions_language():
    assert "article" in INSTRUCTIONS.lower() and "same language" in INSTRUCTIONS.lower()


def test_an_empty_rewrite_is_an_error_not_a_silent_blank_query(tmp_path):
    g, _ = generator([reply("   ")])
    with pytest.raises(LLMError, match="empty"):
        LLMRewriter(CachedGenerator(g, tmp_path / "c.jsonl")).rewrite("q")


def test_the_rewriter_can_be_given_other_instructions_and_the_expanding_ones_differ_from_the_plain_ones(
    tmp_path,
):
    from law_assistant.retrieval.rewriter import EXPANDING_INSTRUCTIONS

    assert EXPANDING_INSTRUCTIONS != INSTRUCTIONS and "60 words" in EXPANDING_INSTRUCTIONS
    assert "At most 40 words" not in EXPANDING_INSTRUCTIONS
    g, _ = generator([reply("x")])
    LLMRewriter(CachedGenerator(g, tmp_path / "c.jsonl"), instructions=EXPANDING_INSTRUCTIONS).rewrite("q")
    assert g._transport.calls[0][2]["systemInstruction"]["parts"][0]["text"] == EXPANDING_INSTRUCTIONS


def test_a_quota_that_resets_in_hours_fails_at_once_instead_of_sleeping_for_hours():
    quota = json.dumps(
        {"error": {"details": [{"retryDelay": "34129s"}], "message": "quota used up"}}
    ).encode()
    g, sleeps = generator([(429, quota)])
    with pytest.raises(LLMError, match="quota") as info:
        g.generate("q")
    assert sleeps == [] and len(g._transport.calls) == 1
    assert "SECRET-KEY" not in str(info.value)


def test_a_short_rate_limit_delay_is_still_waited_out():
    short = json.dumps({"error": {"details": [{"retryDelay": "20s"}]}}).encode()
    g, sleeps = generator([(429, short), reply("ok")])
    assert g.generate("q") == "ok" and sleeps == [22.0]


def test_json_mode_asks_for_a_json_reply_and_is_a_separate_cache_entry(tmp_path):
    g, _ = generator([reply('{"a": 1}'), reply("plain")])
    cached = CachedGenerator(g, tmp_path / "c.jsonl")
    assert cached.generate("q", json_output=True) == '{"a": 1}'
    assert cached.generate("q") == "plain"
    assert g._transport.calls[0][2]["generationConfig"]["responseMimeType"] == "application/json"
    assert "responseMimeType" not in g._transport.calls[1][2]["generationConfig"]
