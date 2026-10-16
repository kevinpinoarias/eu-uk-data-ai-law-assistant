"""
Guards on batch C (eval/batch_c/): the unseen questions written for measuring candidate fixes to the router and the
fact picker (decision 115). The questions are frozen by a fingerprint like the main gold set, and checked with the
same code. The checks that need the parsed corpus skip themselves when the corpus is not downloaded (CI).
"""

from __future__ import annotations

import json
from collections import Counter

import pytest

from law_assistant import settings
from law_assistant.evaluation.checks import Corpus, check_against_corpus, check_questions, overlap_warnings
from law_assistant.evaluation.gold import freeze_hash, read_gold
from law_assistant.facts.table import read_facts

BATCH = settings.PROJECT_ROOT / "eval" / "batch_c"
QUESTIONS = read_gold(BATCH / "questions.jsonl")
MANIFEST = json.loads((BATCH / "MANIFEST.json").read_text(encoding="utf-8"))
needs_corpus = pytest.mark.skipif(
    len(list(settings.PARSED_DIR.glob("*.jsonl"))) < 14, reason="the parsed corpus is not on this machine"
)


def test_the_batch_has_not_changed_since_it_was_frozen():
    assert freeze_hash(QUESTIONS) == MANIFEST["sha256"], "batch C changed: make a new version, do not edit it"
    assert len(QUESTIONS) == MANIFEST["questions"]
    assert dict(Counter(q.route for q in QUESTIONS)) == MANIFEST["by_route"]


def test_the_batch_is_well_formed_and_its_ids_do_not_collide_with_the_frozen_set():
    assert check_questions(QUESTIONS) == []
    frozen = read_gold(settings.GOLD_DIR / "questions.jsonl")
    assert not {q.id for q in QUESTIONS} & {q.id for q in frozen}
    assert not {q.text.casefold() for q in QUESTIONS} & {q.text.casefold() for q in frozen}


def test_every_table_question_names_a_real_row_and_has_both_languages_in_the_batch():
    keys = {f.key for f in read_facts(settings.FACTS_DIR / "legal_facts.jsonl")}
    assert all(q.table_key in keys for q in QUESTIONS if q.route == "table")
    assert {q.language for q in QUESTIONS} == {"en", "es"}


def test_the_batch_covers_the_failure_categories_it_was_written_for():
    notes = " ".join(q.notes for q in QUESTIONS if q.route == "refuse")
    assert all(word in notes for word in ("case law", "enforcement", "adequacy"))
    refusals = Counter(q.refusal_reason for q in QUESTIONS if q.route == "refuse")
    assert refusals["out_of_corpus"] >= 8 and refusals["legal_advice"] >= 4
    assert sum(q.route == "retrieve" for q in QUESTIONS) >= 10  # enough to see a false refusal or false table


@needs_corpus
def test_every_cited_unit_pinpoint_and_quote_exists_and_no_question_copies_its_answer():
    corpus = Corpus.from_dir()
    assert check_against_corpus(QUESTIONS, corpus) == []
    assert overlap_warnings(QUESTIONS, corpus) == []
