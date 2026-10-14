"""
Tests for the gold question record (step 2.0): the shape of a question, reading and writing the set, the mix
targets, and the hash that freezes a version of the set. The checks live in test_gold_checks.py.
"""

from __future__ import annotations

import pytest

from law_assistant.evaluation.gold import (
    LANGUAGE_TARGETS,
    MIX_TARGETS,
    REASON_TARGETS,
    GoldProvision,
    GoldQuestion,
    freeze_hash,
    mix_counts,
    read_gold,
    write_gold,
)


def provision(**kw):
    base = dict(instrument="es-lopdgdd", unit="article", unit_path=("7",), pinpoints=("es-lopdgdd/art-7/1",))
    return GoldProvision(**{**base, **kw})


def question(**kw):
    base = dict(
        id="q001",
        language="es",
        text="¿A qué edad puede un menor dar su consentimiento para el tratamiento de sus datos en España?",
        type="lookup",
        route="retrieve",
        phrasing="lay",
        jurisdictions=("ES",),
        gold=(provision(),),
        expected_answer="A partir de los catorce años (artículo 7.1 LOPDGDD).",
        author="claude",
    )
    return GoldQuestion(**{**base, **kw})


def test_a_question_has_sensible_defaults_for_what_is_decided_later():
    q = question()
    assert (q.as_of, q.split, q.reviewed, q.table_key, q.refusal_reason, q.notes) == (
        None,
        None,
        None,
        None,
        None,
        "",
    )
    assert q.gold[0].role == "primary" and q.gold[0].version is None and q.gold[0].quotes == ()


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("language", "fr"),
        ("type", "trivia"),
        ("route", "guess"),
        ("phrasing", "slang"),
        ("author", "someone"),
        ("split", "validation"),
        ("refusal_reason", "boredom"),
        ("jurisdictions", ("FR",)),
    ],
)
def test_an_unknown_value_in_a_fixed_list_is_refused(field, value):
    with pytest.raises(ValueError, match=field):
        question(**{field: value})


def test_an_unknown_gold_role_or_unit_is_refused():
    with pytest.raises(ValueError, match="role"):
        provision(role="maybe")
    with pytest.raises(ValueError, match="unit"):
        provision(unit="chapter")
    with pytest.raises(ValueError, match="unit_path"):
        provision(unit_path=())


def test_a_question_survives_a_round_trip_through_a_dict():
    q = question(
        as_of="2026-10-14",
        split="dev",
        gold=(provision(quotes=("mayor de catorce años",), version="as-of-20261014", language="es"),),
    )
    assert GoldQuestion.from_dict(q.to_dict()) == q
    assert q.to_dict()["gold"][0]["unit_path"] == ["7"]


def test_the_set_is_written_and_read_back_in_id_order(tmp_path):
    path = tmp_path / "gold" / "questions.jsonl"
    qs = [question(id="q002", text="Segunda pregunta?"), question(id="q001")]
    write_gold(path, qs)
    assert [q.id for q in read_gold(path)] == ["q001", "q002"]
    assert read_gold(path)[0] == question(id="q001")
    assert path.read_bytes().endswith(b"\n") and b"\r" not in path.read_bytes()


def test_the_freeze_hash_ignores_order_and_changes_with_any_edit():
    a, b = question(id="q001"), question(id="q002", text="Otra pregunta?")
    assert freeze_hash([a, b]) == freeze_hash([b, a])
    assert freeze_hash([a, b]) != freeze_hash([a, question(id="q002", text="Otra pregunta distinta?")])
    assert freeze_hash([a, b]) != freeze_hash(
        [a, question(id="q002", text="Otra pregunta?", expected_answer="Otra")]
    )
    assert len(freeze_hash([a])) == 64


def test_the_mix_targets_are_the_plan_for_eighty_questions():
    assert sum(MIX_TARGETS.values()) == 80
    assert MIX_TARGETS == {
        "lookup": 16,
        "definition": 8,
        "cross_reference": 10,
        "comparison": 10,
        "spanish_law": 8,
        "as_of": 10,
        "numeric": 8,
        "refuse": 10,
    }
    assert sum(LANGUAGE_TARGETS.values()) == 80 and set(LANGUAGE_TARGETS) == {"en", "es"}
    assert REASON_TARGETS == {"out_of_corpus": 6, "legal_advice": 4}


def test_mix_counts_by_type_language_and_reason():
    qs = [
        question(id="q001"),
        question(
            id="q002", language="en", type="refuse", route="refuse", gold=(), refusal_reason="legal_advice"
        ),
        question(
            id="q003", language="en", type="refuse", route="refuse", gold=(), refusal_reason="out_of_corpus"
        ),
        question(
            id="q004", language="en", type="refuse", route="refuse", gold=(), refusal_reason="legal_advice"
        ),
    ]
    counts = mix_counts(qs)
    assert counts["type"] == {"lookup": 1, "refuse": 3}
    assert counts["language"] == {"es": 1, "en": 3}
    assert counts["reason"] == {"legal_advice": 2, "out_of_corpus": 1}
