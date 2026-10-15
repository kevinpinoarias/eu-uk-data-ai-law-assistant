"""Tests for the model-based judge of answers (no network: the model is a fake)."""

from __future__ import annotations

import json

import pytest

from law_assistant.answer.judge import (
    CORRECTNESS_INSTRUCTIONS,
    SUPPORT_INSTRUCTIONS,
    Judge,
    parse_verdict,
    score_of,
)
from law_assistant.llm.gemini import LLMError


class FakeGenerator:
    def __init__(self, text):
        self.text, self.calls = text, []

    def generate(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return self.text


def test_scores_are_one_half_and_zero():
    assert (score_of("yes"), score_of("partly"), score_of("no")) == (1.0, 0.5, 0.0)


def test_a_verdict_is_read_from_json_and_checked():
    assert parse_verdict('{"verdict": "partly", "reason": "misses the deadline"}') == (
        "partly",
        "misses the deadline",
    )
    for bad in ("nope", '{"verdict": "maybe"}', '{"reason": "x"}'):
        with pytest.raises(LLMError):
            parse_verdict(bad)


def test_correctness_sends_the_question_the_reference_and_the_answer_but_no_sources():
    g = FakeGenerator(json.dumps({"verdict": "yes", "reason": "same content"}))
    verdict, _ = Judge(g).correctness("What is X?", "X is 16.", "The answer is 16.")
    prompt, kwargs = g.calls[0]
    assert verdict == "yes"
    assert "What is X?" in prompt and "X is 16." in prompt and "The answer is 16." in prompt
    assert kwargs["system"] == CORRECTNESS_INSTRUCTIONS and kwargs["json_output"] is True
    assert kwargs["temperature"] == 0.0


def test_support_sends_the_answer_and_only_the_quotations():
    g = FakeGenerator(json.dumps({"verdict": "no", "reason": "claim 2 has no quote"}))
    verdict, reason = Judge(g).support("The answer.", ["quote one", "quote two"])
    prompt, kwargs = g.calls[0]
    assert (verdict, reason) == ("no", "claim 2 has no quote")
    assert "The answer." in prompt and "quote one" in prompt and "quote two" in prompt
    assert kwargs["system"] == SUPPORT_INSTRUCTIONS


def test_the_instructions_say_to_judge_content_not_style_or_language():
    assert "not style" in CORRECTNESS_INSTRUCTIONS and "language" in CORRECTNESS_INSTRUCTIONS
