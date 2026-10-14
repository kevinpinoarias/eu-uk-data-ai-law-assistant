"""
The committed gold set (eval/gold/questions.jsonl) stays well formed and on plan. These checks need no downloaded
data, so CI runs them too; the check of every gold provision against the parsed corpus is in test_gold_real.py.
"""

from __future__ import annotations

import pytest

from law_assistant import settings
from law_assistant.evaluation.checks import check_mix, check_questions
from law_assistant.evaluation.gold import MIX_TARGETS, read_gold

PATH = settings.GOLD_DIR / "questions.jsonl"

pytestmark = pytest.mark.skipif(not PATH.exists(), reason="the gold set is not written yet")


@pytest.fixture(scope="module")
def questions():
    return read_gold(PATH)


def test_the_set_is_complete_and_numbered_without_gaps(questions):
    assert len(questions) == sum(MIX_TARGETS.values()) == 80
    assert [q.id for q in questions] == [f"q{n:03d}" for n in range(1, 81)]


def test_every_question_is_well_formed(questions):
    assert check_questions(questions) == []


def test_the_mix_by_type_language_and_refusal_reason_is_exactly_the_plan(questions):
    assert check_mix(questions) == []


def test_each_route_has_what_it_needs(questions):
    for q in questions:
        if q.route == "retrieve":
            assert any(g.role == "primary" for g in q.gold), q.id
        elif q.route == "table":
            assert q.table_key, q.id
        else:
            assert not q.gold and q.refusal_reason, q.id


def test_the_set_carries_its_ambiguity_notes_and_is_not_yet_split_or_reviewed(questions):
    assert all(q.notes for q in questions)
    assert all(q.split is None for q in questions)  # the split is made when the set is frozen (step 2.5)
    assert all(q.author == "claude" for q in questions)  # until Kevin's review marks changes
