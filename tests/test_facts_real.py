"""
The facts table against the real parsed corpus: every source exists, every quote is in the cited text, and every
number and date in every fact's value appears in the provisions it cites. A corrupted figure must be caught.
These need data/parsed/ and are skipped without it.
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from law_assistant import settings
from law_assistant.evaluation.checks import Corpus
from law_assistant.facts.checks import check_facts
from law_assistant.facts.table import read_facts

PATH = settings.FACTS_DIR / "legal_facts.jsonl"

pytestmark = pytest.mark.skipif(
    len(list(settings.PARSED_DIR.glob("*.jsonl"))) < 14 or not PATH.exists(),
    reason="the parsed documents or the facts table are not available",
)


@pytest.fixture(scope="module")
def corpus():
    return Corpus.from_dir()


@pytest.fixture(scope="module")
def facts():
    return read_facts(PATH)


def test_every_figure_in_the_table_is_proved_by_its_cited_provision(facts, corpus):
    assert check_facts(facts, corpus) == []


def test_a_corrupted_amount_or_date_or_period_is_caught(facts, corpus):
    by_key = {f.key: f for f in facts}
    upper = by_key["gdpr-fine-upper-tier"]
    dates = by_key["ai-act-high-risk-application-dates"]
    period = by_key["gdpr-response-deadline"]
    problems = check_facts(
        [
            replace(upper, value={**upper.value, "amount": 20_000_001}),
            replace(dates, value={"annex_iii": "2027-12-03", "annex_i": "2028-08-02"}),
            replace(period, value={**period.value, "extension_quantity": 3}),
        ],
        corpus,
    )
    assert len(problems) == 3
    assert any("20000001" in p for p in problems) and any("2027-12-03" in p for p in problems)


def test_the_eu_and_uk_fine_figures_are_the_ones_in_their_texts(facts):
    by_key = {f.key: f for f in facts}
    assert (
        by_key["gdpr-fine-upper-tier"].value["amount"],
        by_key["gdpr-fine-upper-tier"].value["turnover_percent"],
    ) == (
        20_000_000,
        4,
    )
    assert by_key["ai-act-fine-prohibited-practices"].value["amount"] == 35_000_000
    assert by_key["gdpr-breach-notification-deadline"].value["quantity"] == 72
    assert by_key["ai-act-high-risk-application-dates"].value["annex_iii"] == "2027-12-02"
