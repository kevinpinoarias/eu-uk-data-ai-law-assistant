"""
The candidate fixes to the router and the fact picker (decision 116), written after the sealed test half showed
three missed refusals, a figure question that never reached the table and a wrong fine tier. They are options:
the shipped defaults do not change until the candidates are measured on batch C (experiments/c1_routing_fixes.py)
and a decision adopts them.

What can be tested without a model: the defaults are untouched, the candidates add the definitions they were
written for and keep the old ones, no question of the sealed test half or of batch C is quoted in them (tuning
the wording to a question you will be scored on would make the measurement worthless), and the fine-tier scopes
added to two table rows say only what Article 83 says.
"""

from __future__ import annotations

import json

import pytest

from law_assistant import settings
from law_assistant.answer.facts_lookup import (
    PICK_INSTRUCTIONS,
    PICK_INSTRUCTIONS_V2,
    LLMFactPicker,
    apply_scope,
)
from law_assistant.answer.router import ROUTE_INSTRUCTIONS, ROUTE_INSTRUCTIONS_V2, LLMRouter
from law_assistant.evaluation.gold import read_gold
from law_assistant.facts.table import read_facts

OVERLAY = settings.PROJECT_ROOT / "experiments" / "data" / "c1_fact_scope.json"


class Recorder:
    def __init__(self, reply: str) -> None:
        self.reply, self.calls = reply, []

    def generate(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return self.reply


def test_the_router_and_the_picker_keep_their_shipped_instructions_by_default():
    router_gen = Recorder('{"route": "retrieve", "reason": null}')
    LLMRouter(router_gen).route("What is a data breach?")
    assert router_gen.calls[0][1]["system"] == ROUTE_INSTRUCTIONS

    facts = read_facts(settings.FACTS_DIR / "legal_facts.jsonl")
    picker_gen = Recorder('{"key": null}')
    LLMFactPicker(facts, picker_gen).pick("What is the highest fine?")
    assert picker_gen.calls[0][1]["system"].startswith(PICK_INSTRUCTIONS)


def test_a_candidate_router_sends_its_own_instructions():
    gen = Recorder('{"route": "refuse", "reason": "out_of_corpus"}')
    LLMRouter(gen, instructions=ROUTE_INSTRUCTIONS_V2).route("anything")
    assert gen.calls[0][1]["system"] == ROUTE_INSTRUCTIONS_V2


def test_the_candidate_router_adds_the_missing_definitions_and_keeps_the_old_ones():
    v2 = ROUTE_INSTRUCTIONS_V2.lower()
    for needed in ("court", "enforcement decision", "adequacy", "date from which"):
        assert needed in v2, needed
    for kept in ('"retrieve"', '"table"', '"refuse"', "out_of_corpus", "legal_advice", "json only"):
        assert kept in v2, kept
    # the old refusals are still refusals and the over-refusal guard is stated
    assert "california" in v2 and "still 'retrieve'" in v2


def test_the_candidate_picker_tells_the_model_to_choose_a_fine_tier_by_the_breach_named():
    v2 = PICK_INSTRUCTIONS_V2.lower()
    assert "tier" in v2 and "breach" in v2 and "null" in v2 and "rows:" in v2
    gen = Recorder('{"key": null}')
    facts = read_facts(settings.FACTS_DIR / "legal_facts.jsonl")
    LLMFactPicker(facts, gen, instructions=PICK_INSTRUCTIONS_V2).pick("x")
    assert gen.calls[0][1]["system"].startswith(PICK_INSTRUCTIONS_V2)


def _held_out_texts() -> list[str]:
    test_half = [q for q in read_gold(settings.GOLD_DIR / "questions.jsonl") if q.split == "test"]
    batch_c = read_gold(settings.PROJECT_ROOT / "eval" / "batch_c" / "questions.jsonl")
    return [q.text.casefold() for q in test_half + batch_c]


def test_no_scored_question_is_quoted_in_a_candidate_prompt_or_scope():
    prompts = (ROUTE_INSTRUCTIONS_V2 + PICK_INSTRUCTIONS_V2 + OVERLAY.read_text(encoding="utf-8")).casefold()
    assert not [t for t in _held_out_texts() if t in prompts]


def test_apply_scope_changes_only_the_named_subjects():
    facts = read_facts(settings.FACTS_DIR / "legal_facts.jsonl")
    overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    scoped = apply_scope(facts, overlay)
    assert [f.key for f in scoped] == [f.key for f in facts]
    for before, after in zip(facts, scoped, strict=True):
        if before.key in overlay:
            assert after.subject_en == overlay[before.key]["subject_en"]
            assert after.subject_es == overlay[before.key]["subject_es"]
            assert (after.value, after.sources, after.summary_en) == (
                before.value,
                before.sources,
                before.summary_en,
            )
        else:
            assert after is before
    with pytest.raises(KeyError):
        apply_scope(facts, {"no-such-fact": {"subject_en": "x", "subject_es": "y"}})


@pytest.mark.skipif(
    len(list(settings.PARSED_DIR.glob("*.jsonl"))) < 14, reason="the parsed corpus is not on this machine"
)
def test_the_fine_tier_scopes_say_only_what_article_83_says():
    from law_assistant.parse.store import read_jsonl

    art83 = {
        p.id: p.text
        for path in settings.PARSED_DIR.glob("eu-gdpr-consolidated-en.jsonl")
        for p in read_jsonl(path)
        if p.id.startswith("eu-gdpr/art-83/")
    }
    overlay = json.loads(OVERLAY.read_text(encoding="utf-8"))
    lower, upper = (
        overlay["gdpr-fine-lower-tier"]["subject_en"],
        overlay["gdpr-fine-upper-tier"]["subject_en"],
    )
    # every article range named in a scope is a range that Article 83 names in the matching paragraph
    assert "Articles 8, 11, 25 to 39" in art83["eu-gdpr/art-83/4/a"] and "25 to 39" in lower
    assert "Articles 5, 6, 7 and 9" in art83["eu-gdpr/art-83/5/a"] and "5, 6, 7 and 9" in upper
    assert "Articles 12 to 22" in art83["eu-gdpr/art-83/5/b"] and "12 to 22" in upper
    assert "Articles 44 to 49" in art83["eu-gdpr/art-83/5/c"] and "44 to 49" in upper
    assert "Article 83(4)" in lower and "Article 83(5)" in upper
