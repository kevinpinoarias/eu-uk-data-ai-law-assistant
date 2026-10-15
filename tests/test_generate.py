"""
Tests for step 5 of the answer layer: the prompt for the grounded answer, reading the model's JSON reply, and
the plain labels the code (not the model) puts on every source.
"""

from __future__ import annotations

import json

import pytest

from law_assistant.answer.generate import (
    ANSWER_INSTRUCTIONS,
    AnswerWriter,
    describe_version,
    format_passages,
    parse_draft,
    source_label,
)
from law_assistant.answer.verify import Citation
from law_assistant.chunk.chunker import Chunk
from law_assistant.llm.gemini import LLMError


def chunk(cid, text, version="consolidated-20260727", context="GDPR | Chapter II | Article 6: Lawfulness"):
    return Chunk(
        id=cid, instrument="eu-gdpr", jurisdiction="EU", language="en", version=version, unit="article",
        unit_path=("6",), citation="Article 6", heading=None, chapter=None, context=context, text=text,
        provision_ids=("eu-gdpr/art-6/1",), part=1, parts=1, words=len(text.split()), order=0,
    )  # fmt: skip


def test_versions_are_described_in_plain_words():
    assert describe_version("oj") == "as first published in the Official Journal"
    assert describe_version("consolidated-20260727") == "consolidated text of 27 July 2026"
    assert describe_version("consolidated") == "consolidated text"
    assert describe_version("as-of-20261014") == "text in force on 14 October 2026"
    assert describe_version("revised-20261014") == "text in force on 14 October 2026"
    assert describe_version("something-else") == "something-else"


def test_the_source_label_names_the_law_the_provision_and_the_text_version():
    assert source_label(chunk("c", "x")) == "GDPR, Article 6 (consolidated text of 27 July 2026)"


def test_passages_are_numbered_and_carry_their_version():
    text = format_passages([chunk("a", "First text."), chunk("b", "Second text.", version="oj")])
    assert text.startswith("[1] (text version: consolidated text of 27 July 2026)\nGDPR | Chapter II")
    assert "[2] (text version: as first published in the Official Journal)" in text
    assert "First text." in text and "Second text." in text


def test_the_instructions_demand_grounding_exact_quotes_the_language_and_no_advice():
    for phrase in ("only the passages", "copied exactly", "enough_evidence", "not legal advice"):
        assert phrase in ANSWER_INSTRUCTIONS


def test_a_good_reply_becomes_a_draft_with_citations():
    reply = json.dumps(
        {
            "enough_evidence": True,
            "answer": "Consent is one lawful basis (GDPR Article 6).",
            "citations": [{"passage": 1, "quote": "has given consent"}],
        }
    )
    draft = parse_draft(reply)
    assert draft.enough_evidence and draft.text.startswith("Consent")
    assert draft.citations == [Citation(1, "has given consent")]


def test_a_reply_in_a_code_fence_is_read_and_missing_citations_default_to_none():
    draft = parse_draft('```json\n{"enough_evidence": false, "answer": "Not covered."}\n```')
    assert not draft.enough_evidence and draft.citations == []


@pytest.mark.parametrize(
    "bad",
    [
        "not json",
        '{"answer": "x"}',
        '{"enough_evidence": true}',
        '{"enough_evidence": true, "answer": "x", "citations": [{"passage": "one", "quote": "q"}]}',
    ],
)
def test_a_malformed_reply_is_an_error(bad):
    with pytest.raises(LLMError):
        parse_draft(bad)


class FakeGenerator:
    def __init__(self, text):
        self.text, self.calls = text, []

    def generate(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return self.text


def test_the_writer_sends_the_language_the_date_the_question_and_the_passages_and_asks_for_json():
    reply = json.dumps({"enough_evidence": True, "answer": "ok", "citations": []})
    g = FakeGenerator(reply)
    AnswerWriter(g).write("Is consent needed?", "es", [chunk("a", "Some text.")], as_of="2025-01-01")
    prompt, kwargs = g.calls[0]
    assert "Spanish" in prompt and "2025-01-01" in prompt and "Is consent needed?" in prompt
    assert "[1]" in prompt and "Some text." in prompt
    assert kwargs["system"] == ANSWER_INSTRUCTIONS and kwargs["json_output"] is True
    assert kwargs["temperature"] == 0.0


def test_without_a_date_the_prompt_says_the_current_text_is_wanted():
    g = FakeGenerator(json.dumps({"enough_evidence": True, "answer": "ok", "citations": []}))
    AnswerWriter(g).write("q", "en", [chunk("a", "t")], as_of=None)
    assert "current law" in g.calls[0][0] and "English" in g.calls[0][0]


def test_a_passage_can_show_the_date_its_wording_took_effect_when_asked_to():
    from dataclasses import replace

    from law_assistant.answer.generate import describe_date

    dated = replace(chunk("a", "Text."), in_force_from="2026-02-05")
    assert describe_date("2026-02-05") == "5 February 2026"
    assert "in force from 5 February 2026" in format_passages([dated], include_dates=True)
    assert "in force from" not in format_passages([dated])  # off by default: the measured configuration
    undated = chunk("b", "Text.")
    assert "in force from" not in format_passages([undated], include_dates=True)


def test_the_writer_passes_the_option_on_and_the_instructions_explain_the_date_header():
    from dataclasses import replace

    from law_assistant.answer.generate import DATE_INSTRUCTIONS, answer_instructions

    reply = json.dumps({"enough_evidence": True, "answer": "ok", "citations": []})
    g = FakeGenerator(reply)
    dated = replace(chunk("a", "Text."), in_force_from="2026-02-05")
    AnswerWriter(g, include_dates=True).write("Since when?", "en", [dated])
    prompt, kwargs = g.calls[0]
    assert "in force from 5 February 2026" in prompt
    system = kwargs["system"]
    assert system == answer_instructions(True) and DATE_INSTRUCTIONS in system
    assert "since when" in DATE_INSTRUCTIONS.lower()
    assert system.index("in force from") < system.index("Reply with JSON only")
    plain = FakeGenerator(reply)
    AnswerWriter(plain).write("Since when?", "en", [dated])
    assert plain.calls[0][1]["system"] == ANSWER_INSTRUCTIONS
