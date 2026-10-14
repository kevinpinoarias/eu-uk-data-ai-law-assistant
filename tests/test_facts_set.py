"""
The committed table of facts (facts/legal_facts.jsonl) stays well formed and consistent with the gold set. These
checks need no downloaded data, so CI runs them too; the proof that every figure is in its cited provision is in
test_facts_real.py.
"""

from __future__ import annotations

import pytest

from law_assistant import settings
from law_assistant.evaluation.gold import read_gold
from law_assistant.facts.checks import check_gold_keys
from law_assistant.facts.table import KINDS, read_facts

PATH = settings.FACTS_DIR / "legal_facts.jsonl"
GOLD = settings.GOLD_DIR / "questions.jsonl"

pytestmark = pytest.mark.skipif(not PATH.exists(), reason="the facts table is not written yet")


@pytest.fixture(scope="module")
def facts():
    return read_facts(PATH)


def test_keys_are_unique_and_every_kind_is_used(facts):
    keys = [f.key for f in facts]
    assert len(keys) == len(set(keys)) == 19
    assert {f.kind for f in facts} == set(KINDS)


def test_every_fact_has_both_languages_a_value_and_a_source(facts):
    for f in facts:
        assert f.summary_en.strip() and f.summary_es.strip(), f.key
        assert f.subject_en.strip() and f.subject_es.strip(), f.key
        assert f.value and f.sources, f.key
        assert all(s.quotes for s in f.sources), f.key  # a source with no quote proves nothing


@pytest.mark.skipif(not GOLD.exists(), reason="the gold set is not written yet")
def test_every_numeric_gold_question_has_its_fact_and_states_its_figures(facts):
    assert check_gold_keys(read_gold(GOLD), facts) == []


@pytest.mark.skipif(not GOLD.exists(), reason="the gold set is not written yet")
def test_the_keys_named_by_the_numeric_questions_are_the_eight_expected(facts):
    keys = {q.table_key for q in read_gold(GOLD) if q.route == "table"}
    assert keys == {
        "gdpr-fine-upper-tier",
        "gdpr-fine-lower-tier",
        "ai-act-fine-prohibited-practices",
        "gdpr-breach-notification-deadline",
        "gdpr-response-deadline",
        "ai-act-high-risk-application-dates",
        "gdpr-child-consent-age",
    }
    assert keys <= {f.key for f in facts}


def test_the_uk_figure_that_the_ambiguous_fine_question_needs_is_in_the_table(facts):
    uk = next(f for f in facts if f.key == "uk-gdpr-fine-upper-tier")
    assert uk.value["amount"] == 17_500_000 and uk.value["currency"] == "GBP" and uk.jurisdictions == ("UK",)
