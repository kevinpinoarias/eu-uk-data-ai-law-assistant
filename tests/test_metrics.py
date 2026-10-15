"""
Tests for the retrieval metrics (step 2.4): when a chunk counts as a hit for a gold provision, how a ranked list
of chunks is scored (hit, recall, MRR, nDCG), and the bootstrap intervals. The checks against the real chunks and
the committed gold set are in test_metrics_real.py.
"""

from __future__ import annotations

import math

import pytest

from law_assistant.chunk.chunker import Chunk
from law_assistant.evaluation.gold import GoldProvision, GoldQuestion
from law_assistant.evaluation.metrics import (
    bootstrap_ci,
    paired_bootstrap,
    read_run,
    retrieval_questions,
    score_question,
    score_run,
    summarise,
    unreachable_targets,
    write_run,
)
from law_assistant.evaluation.relevance import matches, targets_of


def chunk(
    id_,
    *,
    instrument="eu-gdpr",
    unit="article",
    path=("17",),
    pins=("eu-gdpr/art-17/1",),
    version="oj",
    language="en",
):
    return Chunk(
        id=id_,
        instrument=instrument,
        jurisdiction="EU",
        language=language,
        version=version,
        unit=unit,
        unit_path=tuple(path),
        citation="x",
        heading=None,
        chapter=None,
        context="c",
        text="t",
        provision_ids=tuple(pins),
        part=1,
        parts=1,
        words=1,
        order=0,
    )


def gold(**kw):
    base = dict(instrument="eu-gdpr", unit="article", unit_path=("17",))
    return GoldProvision(**{**base, **kw})


def question(*golds, id_="q001", **kw):
    base = dict(
        id=id_,
        language="en",
        text="A question?",
        type="lookup",
        route="retrieve",
        phrasing="lay",
        jurisdictions=("EU",),
        gold=tuple(golds) or (gold(),),
        expected_answer="x",
        author="claude",
    )
    return GoldQuestion(**{**base, **kw})


OTHER = dict(path=("99",), pins=("eu-gdpr/art-99/1",))

# --- when a chunk is a hit for a gold provision -----------------------------------------------------------


def test_without_pinpoints_any_chunk_of_the_unit_is_a_hit():
    assert matches(chunk("a"), gold())
    assert matches(chunk("a", pins=("eu-gdpr/art-17/3",)), gold())


def test_the_instrument_the_unit_kind_and_the_unit_path_must_all_match():
    assert not matches(chunk("a", instrument="uk-gdpr"), gold())
    assert not matches(chunk("a", unit="section"), gold())
    assert not matches(chunk("a", path=("18",)), gold())


def test_with_pinpoints_the_chunk_must_contain_one_of_them():
    g = gold(pinpoints=("eu-gdpr/art-17/1/a", "eu-gdpr/art-17/3"))
    assert matches(chunk("a", pins=("eu-gdpr/art-17/1", "eu-gdpr/art-17/3")), g)
    assert not matches(
        chunk("b", pins=("eu-gdpr/art-17/1", "eu-gdpr/art-17/2")), g
    )  # same article, wrong part


def test_a_version_pin_rejects_other_versions_and_no_pin_accepts_any():
    pinned = gold(version="consolidated-20260727")
    assert matches(chunk("a", version="consolidated-20260727"), pinned)
    assert not matches(chunk("a", version="oj"), pinned)
    assert matches(chunk("a", version="oj"), gold()) and matches(
        chunk("a", version="consolidated-20260727"), gold()
    )


def test_a_language_filter_rejects_the_other_language_and_no_filter_accepts_both():
    spanish = gold(language="es")
    assert matches(chunk("a", language="es"), spanish) and not matches(chunk("a", language="en"), spanish)
    assert matches(chunk("a", language="es"), gold()) and matches(chunk("a", language="en"), gold())


def test_targets_carry_a_grade_two_for_primary_and_one_for_acceptable():
    q = question(gold(), gold(unit_path=("18",), role="acceptable"))
    assert [(t.index, t.grade) for t in targets_of(q)] == [(0, 2), (1, 1)]


# --- scoring one ranked list --------------------------------------------------------------------------------


def test_a_primary_hit_at_rank_one_scores_perfectly():
    s = score_question(question(), [chunk("a"), chunk("b", **OTHER)], ks=(1, 3))
    assert (s.hit[1], s.recall[1], s.reciprocal_rank, s.ndcg[3], s.first_rank) == (1.0, 1.0, 1.0, 1.0, 1)


def test_a_primary_hit_at_rank_three_misses_at_one_and_scores_a_third_for_rank():
    ranking = [chunk("x", **OTHER), chunk("y", path=("98",), pins=()), chunk("a")]
    s = score_question(question(), ranking, ks=(1, 3))
    assert (s.hit[1], s.hit[3], s.recall[3], s.first_rank) == (0.0, 1.0, 1.0, 3)
    assert s.reciprocal_rank == pytest.approx(1 / 3)
    assert s.ndcg[3] == pytest.approx(1 / math.log2(4))  # one target, found at rank 3, ideal at rank 1


def test_recall_is_the_share_of_primary_provisions_found_and_hit_needs_only_one():
    q = question(gold(), gold(unit_path=("18",)))
    ranking = [chunk("a"), chunk("x", **OTHER), chunk("b", path=("18",), pins=())]
    s = score_question(q, ranking, ks=(1, 3))
    assert (s.hit[1], s.recall[1], s.recall[3], s.reciprocal_rank) == (1.0, 0.5, 1.0, 1.0)


def test_an_acceptable_chunk_earns_less_and_does_not_count_for_hit_recall_or_rank():
    q = question(gold(), gold(unit_path=("18",), role="acceptable"))
    ranking = [chunk("b", path=("18",), pins=()), chunk("a")]
    s = score_question(q, ranking, ks=(1, 2))
    assert (s.hit[1], s.hit[2], s.reciprocal_rank, s.first_rank) == (0.0, 1.0, 0.5, 2)
    dcg = 1 / math.log2(2) + 3 / math.log2(3)
    ideal = 3 / math.log2(2) + 1 / math.log2(3)
    assert s.ndcg[2] == pytest.approx(dcg / ideal)


def test_several_copies_of_one_target_are_credited_once():
    english, spanish, other_version = (
        chunk("a"),
        chunk("b", language="es"),
        chunk("c", version="consolidated"),
    )
    s = score_question(question(), [english, spanish, other_version], ks=(1, 3))
    assert s.recall[3] == 1.0 and s.ndcg[3] == pytest.approx(1.0)  # extra copies add nothing and cost nothing


def test_nothing_relevant_or_nothing_retrieved_scores_zero():
    for ranking in ([chunk("x", **OTHER)], []):
        s = score_question(question(), ranking, ks=(1, 3))
        assert (s.hit[3], s.recall[3], s.reciprocal_rank, s.ndcg[3], s.first_rank) == (
            0.0,
            0.0,
            0.0,
            0.0,
            None,
        )


def test_a_retrieval_question_without_a_primary_provision_is_refused():
    with pytest.raises(ValueError, match="primary"):
        score_question(question(gold(role="acceptable")), [chunk("a")])


# --- runs -------------------------------------------------------------------------------------------------


def test_only_retrieval_questions_are_scored():
    refusal = question(id_="q002", type="refuse", route="refuse", refusal_reason="legal_advice")
    refusal = GoldQuestion(**{**refusal.__dict__, "gold": ()})
    assert [q.id for q in retrieval_questions([question(), refusal])] == ["q001"]


def test_a_run_is_scored_from_chunk_ids_and_every_retrieval_question_must_be_in_it():
    chunks = {c.id: c for c in (chunk("a"), chunk("x", **OTHER))}
    qs = [question(id_="q001"), question(id_="q002", gold=(gold(unit_path=("99",)),))]
    scores = score_run(qs, {"q001": ["a"], "q002": ["x"]}, chunks, ks=(1,))
    assert [s.question_id for s in scores] == ["q001", "q002"] and [s.hit[1] for s in scores] == [1.0, 1.0]
    with pytest.raises(ValueError, match="q002"):
        score_run(qs, {"q001": ["a"]}, chunks)
    with pytest.raises(ValueError, match="unknown chunk"):
        score_run(qs, {"q001": ["nope"], "q002": []}, chunks)


def test_a_run_survives_a_round_trip_through_a_file(tmp_path):
    run = {"q002": ["b", "a"], "q001": ["a"]}
    write_run(tmp_path / "runs" / "r1.jsonl", run)
    assert read_run(tmp_path / "runs" / "r1.jsonl") == run


def test_targets_that_no_chunk_can_satisfy_are_listed():
    q = question(gold(), gold(unit_path=("404",)))
    assert unreachable_targets([q], [chunk("a")]) == [("q001", 1)]
    assert unreachable_targets([q], [chunk("a"), chunk("z", path=("404",), pins=())]) == []


def test_a_summary_gives_the_mean_of_each_metric_over_the_questions():
    perfect = score_question(question(id_="q001"), [chunk("a")], ks=(1, 3))
    missed = score_question(question(id_="q002"), [chunk("x", **OTHER)], ks=(1, 3))
    summary = summarise([perfect, missed], ks=(1, 3))
    assert summary == {
        "hit@1": 0.5,
        "hit@3": 0.5,
        "recall@1": 0.5,
        "recall@3": 0.5,
        "mrr": 0.5,
        "ndcg@1": 0.5,
        "ndcg@3": 0.5,
    }


# --- bootstrap ---------------------------------------------------------------------------------------------


def test_the_interval_of_identical_values_is_that_value():
    assert bootstrap_ci([0.5] * 10, resamples=200) == (0.5, 0.5, 0.5)


def test_the_interval_is_reproducible_with_a_seed_and_contains_the_mean():
    values = [1.0, 0.0, 1.0, 1.0, 0.0, 1.0, 0.0, 1.0]
    first = bootstrap_ci(values, resamples=500, seed=7)
    assert first == bootstrap_ci(values, resamples=500, seed=7)
    mean, low, high = first
    assert mean == 0.625 and low <= mean <= high and low < high


def test_more_questions_give_a_narrower_interval():
    few = bootstrap_ci([1.0, 0.0] * 5, resamples=1000, seed=1)
    many = bootstrap_ci([1.0, 0.0] * 50, resamples=1000, seed=1)
    assert (many[2] - many[1]) < (few[2] - few[1])


def test_a_paired_comparison_gives_the_difference_with_its_interval():
    result = paired_bootstrap([0, 0, 0, 0], [1, 1, 1, 1], resamples=200)
    assert (result.difference, result.low, result.high, result.p_not_better) == (1.0, 1.0, 1.0, 0.0)
    same = paired_bootstrap([1, 0, 1, 0], [1, 0, 1, 0], resamples=200)
    assert (same.difference, same.low, same.high, same.p_not_better) == (0.0, 0.0, 0.0, 1.0)


def test_pairing_is_tighter_than_comparing_two_separate_intervals():
    a = [1.0, 0.0] * 20
    b = [1.0, 1.0] + [1.0, 0.0] * 19  # the same as a on every question but one
    paired = paired_bootstrap(a, b, resamples=2000, seed=3)
    _, a_low, a_high = bootstrap_ci(a, resamples=2000, seed=3)
    assert (paired.high - paired.low) < (a_high - a_low)


def test_paired_values_must_come_from_the_same_questions():
    with pytest.raises(ValueError, match="same"):
        paired_bootstrap([1, 0], [1])
