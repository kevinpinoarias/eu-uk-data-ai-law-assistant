"""
Tests for the table lookup (answer-layer step 2b): which row of the facts table does an exact-figure question ask
about? The embedding model is replaced by a bag-of-words fake so no model is needed.
"""

from __future__ import annotations

import math
import re

from law_assistant.answer.facts_lookup import FactMatcher
from law_assistant.facts.table import Fact, FactSource

VOCAB = ["fine", "multa", "age", "edad", "breach", "brecha", "hours", "deadline", "consent", "turnover"]


def embed(texts):
    out = []
    for text in texts:
        words = re.findall(r"\w+", text.lower())
        v = [float(sum(w.startswith(t) for w in words)) for t in VOCAB]
        norm = math.sqrt(sum(x * x for x in v)) or 1.0
        out.append([x / norm for x in v])
    return out


def fact(key, jurisdiction, subject_en, subject_es, summary_en="", summary_es=""):
    return Fact(
        key=key, kind="deadline", jurisdictions=(jurisdiction,), subject_en=subject_en, subject_es=subject_es,
        value={"n": 1}, summary_en=summary_en or subject_en, summary_es=summary_es or subject_es,
        sources=(FactSource("x", "article", ("1",)),),
    )  # fmt: skip


FACTS = [
    fact("eu-fine", "EU", "Maximum fine turnover", "Multa máxima volumen"),
    fact("uk-fine", "UK", "Maximum fine turnover", "Multa máxima volumen"),
    fact("eu-age", "EU", "Age of child consent", "Edad del consentimiento del niño"),
    fact("eu-breach", "EU", "Breach notification deadline hours", "Plazo de notificación de la brecha"),
]


def test_the_closest_fact_in_the_questions_language_is_chosen():
    matcher = FactMatcher(FACTS, embed, threshold=0.3)
    assert matcher.match("what is the age of consent for a child", "en").fact.key == "eu-age"
    assert matcher.match("¿a qué edad puede consentir un niño?", "es").fact.key == "eu-age"
    assert matcher.match("how many hours to report a breach", "en").fact.key == "eu-breach"


def test_a_named_jurisdiction_limits_the_choice_to_that_jurisdictions_facts():
    matcher = FactMatcher(FACTS, embed, threshold=0.3)
    assert matcher.match("maximum fine in the UK", "en", jurisdictions=("UK",)).fact.key == "uk-fine"
    assert matcher.match("maximum fine in the EU", "en", jurisdictions=("EU",)).fact.key == "eu-fine"


def test_a_question_that_matches_no_fact_well_enough_gets_none_and_keeps_its_score():
    matcher = FactMatcher(FACTS, embed, threshold=0.5)
    result = matcher.match("what colour is the sky", "en")
    assert result.fact is None and result.score == 0.0


def test_naming_a_jurisdiction_with_no_facts_gives_none():
    matcher = FactMatcher(FACTS, embed, threshold=0.3)
    assert matcher.match("maximum fine in Spain", "en", jurisdictions=("ES",)).fact is None


class FakeGenerator:
    def __init__(self, text):
        self.text, self.calls = text, []

    def generate(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return self.text


def test_the_picker_lists_every_fact_key_and_returns_the_key_the_model_names():
    from law_assistant.answer.facts_lookup import PICK_INSTRUCTIONS, LLMFactPicker

    g = FakeGenerator('{"key": "eu-age"}')
    picker = LLMFactPicker(FACTS, g)
    assert picker.pick("age of consent?", ("EU",)).key == "eu-age"
    prompt, kwargs = g.calls[0]
    assert kwargs["system"].startswith(PICK_INSTRUCTIONS) and kwargs["json_output"] is True
    for f in FACTS:
        assert f.key in kwargs["system"]
    assert "age of consent?" in prompt and "EU" in prompt


def test_the_picker_returns_none_for_null_for_an_unknown_key_and_for_a_malformed_reply():
    from law_assistant.answer.facts_lookup import LLMFactPicker

    for reply in ('{"key": null}', '{"key": "made-up-key"}', "not json", '{"other": 1}'):
        assert LLMFactPicker(FACTS, FakeGenerator(reply)).pick("q", ()) is None
