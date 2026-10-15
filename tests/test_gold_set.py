"""
The committed gold set (eval/gold/questions.jsonl) stays well formed and on plan. These checks need no downloaded
data, so CI runs them too; the check of every gold provision against the parsed corpus is in test_gold_real.py.
"""

from __future__ import annotations

from collections import Counter

import pytest

from law_assistant import settings
from law_assistant.evaluation.checks import check_mix, check_questions
from law_assistant.evaluation.freeze import check_manifest, read_manifest, split_counts
from law_assistant.evaluation.gold import MIX_TARGETS, read_gold

PATH = settings.GOLD_DIR / "questions.jsonl"
MANIFEST = settings.GOLD_DIR / "MANIFEST.json"

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


def test_the_set_carries_its_ambiguity_notes_and_its_author(questions):
    assert all(q.notes for q in questions)
    assert all(
        q.author == "claude" for q in questions
    )  # a question rewritten by a person would carry "kevin"


# --- the freeze ------------------------------------------------------------------------------------------


@pytest.fixture(scope="module")
def manifest():
    return read_manifest(MANIFEST)


def test_the_set_is_frozen_and_matches_its_manifest(questions, manifest):
    """Any edit changes the fingerprint: change the set only by making a new version and a new manifest."""
    assert check_manifest(questions, manifest) == []


def test_the_manifest_says_what_was_reviewed_and_what_was_not(manifest):
    assert manifest["version"] == 1 and manifest["frozen"] == "2026-10-15" and len(manifest["sha256"]) == 64
    assert "NOT reviewed by a qualified lawyer" in manifest["review"]


def test_the_split_is_forty_and_forty_with_the_same_number_of_retrieval_questions_in_each_half(questions):
    assert split_counts(questions) == {"dev": 40, "test": 40}
    retrieval = Counter(q.split for q in questions if q.route == "retrieve")
    assert retrieval["dev"] == retrieval["test"] == 31


def test_every_type_and_language_is_split_within_one_question_of_even(questions):
    cells = Counter((q.type, q.language, q.split) for q in questions)
    for q in questions:
        assert abs(cells[(q.type, q.language, "dev")] - cells[(q.type, q.language, "test")]) <= 1
