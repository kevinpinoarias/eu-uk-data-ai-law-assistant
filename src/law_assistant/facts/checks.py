"""
Checks that keep the table honest: every source exists and its quotes are in the text, every number and
date in a fact's value appears in the provisions it cites, no key is repeated, and every numeric gold question
names a key that exists and whose figures its expected answer states.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Sequence

from law_assistant.evaluation.checks import Corpus, provision_problems
from law_assistant.evaluation.gold import GoldProvision, GoldQuestion
from law_assistant.facts.extract import dates_in, numbers_in, value_leaves
from law_assistant.facts.table import Fact, FactSource


def _as_provision(source: FactSource) -> GoldProvision:
    return GoldProvision(
        source.instrument, source.unit, source.unit_path, source.pinpoints, source.quotes, source.version
    )


def _shown(number: float) -> str:
    return str(int(number)) if float(number).is_integer() else str(number)


def check_facts(facts: Sequence[Fact], corpus: Corpus) -> list[str]:
    """Problems found in the table (an empty list means every figure is proved by its cited text)."""
    problems = [f"duplicate key {key}" for key, n in Counter(f.key for f in facts).items() if n > 1]
    for fact in facts:
        for name in ("subject_en", "subject_es", "summary_en", "summary_es"):
            if not getattr(fact, name).strip():
                problems.append(f"{fact.key}: {name} is blank")
        texts: list[str] = []
        for source in fact.sources:
            provision = _as_provision(source)
            problems += provision_problems(fact.key, provision, corpus)
            texts += corpus.unit_texts(provision)
        cited = " ".join(texts)
        found_numbers, found_dates = numbers_in(cited), dates_in(cited)
        numbers, dates = value_leaves(fact.value)
        problems += [
            f"{fact.key}: number {_shown(n)} not found in the cited text"
            for n in sorted(numbers)
            if n not in found_numbers
        ]
        problems += [
            f"{fact.key}: date {d} not found in the cited text" for d in sorted(dates) if d not in found_dates
        ]
    return problems


def check_gold_keys(questions: Sequence[GoldQuestion], facts: Sequence[Fact]) -> list[str]:
    """Each table question names an existing key, and its expected answer states the fact's figures."""
    by_key = {f.key: f for f in facts}
    problems = []
    for q in questions:
        if q.route != "table":
            continue
        fact = by_key.get(q.table_key or "")
        if fact is None:
            problems.append(f"{q.id}: table_key {q.table_key} is not in the facts table")
            continue
        stated_numbers, stated_dates = numbers_in(q.expected_answer), dates_in(q.expected_answer)
        numbers, dates = value_leaves(fact.value)
        problems += [
            f"{q.id}: expected answer lacks {_shown(n)} of fact {fact.key}"
            for n in sorted(numbers)
            if n not in stated_numbers
        ]
        problems += [
            f"{q.id}: expected answer lacks {d} of fact {fact.key}"
            for d in sorted(dates)
            if d not in stated_dates
        ]
    return problems
