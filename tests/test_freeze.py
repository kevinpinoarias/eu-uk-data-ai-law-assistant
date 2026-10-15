"""
Tests for the split and the freeze (step 2.5): a seeded split into development and test that is balanced within
every type and language, and a manifest that records the fingerprint of the frozen set so that any later edit is
detected. The checks of the committed set against its manifest are in test_gold_set.py.
"""

from __future__ import annotations

import json
from collections import Counter

import pytest

from law_assistant.evaluation.freeze import (
    assign_splits,
    build_manifest,
    check_manifest,
    read_manifest,
    split_counts,
    write_manifest,
)
from law_assistant.evaluation.gold import TYPES, GoldProvision, GoldQuestion, freeze_hash


def make(id_, type_, language, split=None):
    retrieve = type_ not in ("numeric", "refuse")
    return GoldQuestion(
        id=id_,
        language=language,
        text=f"Question {id_}?",
        type=type_,
        route="retrieve" if retrieve else ("table" if type_ == "numeric" else "refuse"),
        phrasing="lay",
        jurisdictions=("EU",),
        gold=(GoldProvision("eu-gdpr", "article", ("17",)),) if retrieve else (),
        expected_answer="x",
        author="claude",
        split=split,
        table_key="k" if type_ == "numeric" else None,
        refusal_reason="legal_advice" if type_ == "refuse" else None,
    )


def eighty():
    qs, n = [], 0
    for type_ in TYPES:
        for language in ("en", "es"):
            for _ in range(5):
                n += 1
                qs.append(make(f"q{n:03d}", type_, language))
    return qs


def test_the_split_gives_forty_and_forty_and_balances_every_type_and_language():
    split = assign_splits(eighty(), seed=7)
    assert split_counts(split) == {"dev": 40, "test": 40}
    cells = Counter((q.type, q.language, q.split) for q in split)
    for type_ in TYPES:
        for language in ("en", "es"):
            assert abs(cells[(type_, language, "dev")] - cells[(type_, language, "test")]) <= 1


def test_the_split_is_reproducible_with_a_seed_and_different_with_another():
    first = [(q.id, q.split) for q in assign_splits(eighty(), seed=7)]
    assert first == [(q.id, q.split) for q in assign_splits(eighty(), seed=7)]
    assert first != [(q.id, q.split) for q in assign_splits(eighty(), seed=8)]


def test_the_split_returns_new_questions_and_leaves_the_input_untouched():
    original = eighty()
    split = assign_splits(original, seed=1)
    assert all(q.split is None for q in original) and all(q.split in ("dev", "test") for q in split)
    assert [q.id for q in split] == [q.id for q in original]


def test_a_set_that_is_already_split_is_refused():
    with pytest.raises(ValueError, match="already"):
        assign_splits([make("q001", "lookup", "en", split="dev")], seed=1)


def test_each_half_keeps_a_fair_share_of_the_retrieval_questions():
    split = assign_splits(eighty(), seed=7)
    retrieval = Counter(q.split for q in split if q.route == "retrieve")
    assert abs(retrieval["dev"] - retrieval["test"]) <= 2


# --- the manifest -------------------------------------------------------------------------------------------


def frozen():
    return assign_splits(eighty(), seed=7)


def test_the_manifest_records_the_fingerprint_counts_seed_date_and_review_statement(tmp_path):
    qs = frozen()
    manifest = build_manifest(
        qs, date="2026-10-15", seed=7, review="drafted by an assistant; no lawyer review"
    )
    assert (
        manifest["sha256"] == freeze_hash(qs) and manifest["frozen"] == "2026-10-15" and manifest["seed"] == 7
    )
    assert manifest["questions"] == 80 and manifest["split"] == {"dev": 40, "test": 40}
    assert manifest["by_type"]["lookup"] == 10 and manifest["review"].startswith("drafted")
    assert sum(manifest["retrieval_questions"].values()) == 60
    path = tmp_path / "gold" / "MANIFEST.json"
    write_manifest(path, manifest)
    assert read_manifest(path) == manifest
    assert json.loads(path.read_text(encoding="utf-8"))["version"] == 1


def test_a_set_that_matches_its_manifest_has_no_problems():
    qs = frozen()
    assert check_manifest(qs, build_manifest(qs, date="2026-10-15", seed=7, review="r")) == []


def test_any_edit_after_the_freeze_is_detected():
    qs = frozen()
    manifest = build_manifest(qs, date="2026-10-15", seed=7, review="r")
    edited = [GoldQuestion(**{**qs[0].__dict__, "text": "A different question?"}), *qs[1:]]
    problems = check_manifest(edited, manifest)
    assert any("changed since it was frozen" in p for p in problems)


def test_a_missing_question_or_an_unsplit_one_is_detected():
    qs = frozen()
    manifest = build_manifest(qs, date="2026-10-15", seed=7, review="r")
    assert any("questions" in p for p in check_manifest(qs[:-1], manifest))
    unsplit = [GoldQuestion(**{**qs[0].__dict__, "split": None}), *qs[1:]]
    assert any("split" in p for p in check_manifest(unsplit, manifest))
