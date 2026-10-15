"""
Tests for the retrieval harness (step 3.0): tokenising, BM25 (checked against numbers worked out by hand),
the reference retrievers (random and oracle), running a retriever over the gold questions, and the report.
The runs on the real chunks are in test_retrieval_real.py.
"""

from __future__ import annotations

import math

import pytest

from law_assistant.chunk.chunker import Chunk
from law_assistant.evaluation.gold import GoldProvision, GoldQuestion
from law_assistant.retrieval.bm25 import BM25Index
from law_assistant.retrieval.reference import OracleRetriever, RandomRetriever
from law_assistant.retrieval.report import format_table, summarise_with_ci
from law_assistant.retrieval.runner import breakdown, evaluate, run_retriever, select
from law_assistant.retrieval.tokenize import tokenize


def chunk(id_, text, *, path=("17",), instrument="eu-gdpr", pins=()):
    return Chunk(
        id=id_, instrument=instrument, jurisdiction="EU", language="en", version="oj", unit="article",
        unit_path=tuple(path), citation="x", heading=None, chapter=None, context="", text=text,
        provision_ids=tuple(pins), part=1, parts=1, words=len(text.split()), order=0,
    )  # fmt: skip


def question(id_, text, path, *, split="dev", type_="lookup", route="retrieve"):
    gold = (GoldProvision("eu-gdpr", "article", tuple(path)),) if route == "retrieve" else ()
    return GoldQuestion(
        id=id_, language="en", text=text, type=type_, route=route, phrasing="lay", jurisdictions=("EU",),
        gold=gold, expected_answer="x", author="claude", split=split,
        table_key="k" if route == "table" else None,
    )  # fmt: skip


def text_only(c):
    return c.text


# --- tokenising --------------------------------------------------------------------------------------------


def test_text_is_lower_cased_and_split_on_everything_that_is_not_a_letter_or_digit():
    assert tokenize("Article 6(1)(f) GDPR, 'lawful'!") == ["article", "6", "1", "f", "gdpr", "lawful"]
    assert tokenize("") == [] and tokenize("  ...  ") == []


def test_accents_are_kept_by_default_and_folded_on_request():
    assert tokenize("Protección de datos, año") == ["protección", "de", "datos", "año"]
    assert tokenize("Protección de datos, año", fold_accents=True) == ["proteccion", "de", "datos", "ano"]


# --- BM25, against numbers worked out by hand --------------------------------------------------------------

DOCS = [chunk("d1", "apple banana"), chunk("d2", "apple apple cherry"), chunk("d3", "durian")]


def index(docs=DOCS, **kw):
    return BM25Index(docs, text_of=text_only, **kw)


def test_scores_match_the_formula_worked_out_by_hand():
    # N=3, average length 2, "apple" is in 2 documents; k1=1.2, b=0.75
    idf = math.log(1 + (3 - 2 + 0.5) / (2 + 0.5))
    d1 = idf * 1 * 2.2 / (1 + 1.2 * (1 - 0.75 + 0.75 * 2 / 2))
    d2 = idf * 2 * 2.2 / (2 + 1.2 * (1 - 0.75 + 0.75 * 3 / 2))
    ranking = index().scored("apple", 10)
    assert [cid for cid, _ in ranking] == ["d2", "d1"]
    assert dict(ranking)["d1"] == pytest.approx(d1) and dict(ranking)["d2"] == pytest.approx(d2)


def test_a_rarer_term_counts_for_more_and_scores_add_up_over_query_terms():
    both = dict(index().scored("apple cherry", 10))
    only_apple = dict(index().scored("apple", 10))
    only_cherry = dict(index().scored("cherry", 10))
    assert both["d2"] == pytest.approx(only_apple["d2"] + only_cherry["d2"])
    assert only_cherry["d2"] > only_apple["d2"]  # cherry is in one document, apple in two


def test_a_term_in_every_document_still_scores_above_zero():
    docs = [chunk("a", "law text"), chunk("b", "law more")]
    scores = dict(index(docs).scored("law", 10))
    assert all(s > 0 for s in scores.values())


def test_a_longer_document_scores_lower_for_the_same_count_of_the_term():
    docs = [chunk("short", "apple pear"), chunk("long", "apple pear fig grape lime plum kiwi")]
    scores = dict(index(docs).scored("apple", 10))
    assert scores["short"] > scores["long"]


def test_repeating_a_word_in_the_query_does_not_change_the_scores():
    assert index().scored("apple apple apple", 10) == index().scored("apple", 10)


def test_ties_are_broken_by_chunk_id_so_results_are_reproducible():
    docs = [chunk("b", "same words"), chunk("a", "same words"), chunk("c", "same words")]
    assert index(docs).search("same", 10) == ["a", "b", "c"]


def test_k_limits_the_results_and_documents_with_no_query_term_are_not_returned():
    assert index().search("apple", 1) == ["d2"]
    assert index().search("apple", 10) == ["d2", "d1"]
    assert index().search("zebra", 10) == []
    assert index().search("", 10) == []


def test_folding_accents_lets_an_unaccented_query_find_an_accented_text():
    docs = [chunk("a", "protección de datos"), chunk("b", "otra cosa")]
    assert BM25Index(docs, text_of=text_only).search("proteccion", 5) == []
    assert BM25Index(docs, text_of=text_only, fold_accents=True).search("proteccion", 5) == ["a"]


def test_by_default_the_context_line_and_the_text_are_both_indexed():
    c = Chunk(**{**chunk("a", "plain words").__dict__, "context": "GDPR | Article 17"})
    assert BM25Index([c]).search("gdpr", 5) == ["a"]
    assert BM25Index([c], text_of=text_only).search("gdpr", 5) == []


def test_an_empty_corpus_gives_an_empty_index():
    assert BM25Index([]).search("anything", 5) == []


# --- reference retrievers ----------------------------------------------------------------------------------


def corpus():
    return [chunk(f"c{i}", f"word{i}", path=(str(i),)) for i in range(30)]


def test_the_random_retriever_is_reproducible_gives_distinct_chunks_and_ignores_the_query():
    r = RandomRetriever(corpus(), seed=3)
    first = r.search("one question", 10)
    assert len(first) == len(set(first)) == 10
    assert first == RandomRetriever(corpus(), seed=3).search("one question", 10)
    assert first != RandomRetriever(corpus(), seed=4).search("one question", 10)


def test_the_oracle_puts_the_gold_provisions_first_primary_before_acceptable():
    chunks = corpus()
    q = GoldQuestion(**{**question("q1", "Where is it?", ("5",)).__dict__,
                        "gold": (GoldProvision("eu-gdpr", "article", ("9",), role="acceptable"),
                                 GoldProvision("eu-gdpr", "article", ("5",)))})  # fmt: skip
    ranking = OracleRetriever([q], chunks).search("Where is it?", 5)
    assert ranking[:2] == ["c5", "c9"]


# --- running ------------------------------------------------------------------------------------------------


def questions():
    return [
        question("q1", "apple question", ("1",), split="dev"),
        question("q2", "banana question", ("2",), split="test", type_="definition"),
        question("q3", "numeric one", ("3",), split="dev", type_="numeric", route="table"),
        question("q4", "cherry question", ("4",), split="dev", type_="definition"),
    ]


def test_select_keeps_only_retrieval_questions_of_the_chosen_split():
    assert [q.id for q in select(questions(), "dev")] == ["q1", "q4"]
    assert [q.id for q in select(questions(), "test")] == ["q2"]
    assert [q.id for q in select(questions(), None)] == ["q1", "q2", "q4"]


def test_a_run_maps_each_question_id_to_a_ranked_list_of_chunk_ids():
    chunks = corpus()
    qs = select(questions(), "dev")
    run = run_retriever(OracleRetriever(qs, chunks), qs, k=3)
    assert set(run) == {"q1", "q4"} and run["q1"][0] == "c1" and run["q4"][0] == "c4"


def test_the_oracle_scores_one_and_random_scores_near_zero():
    chunks = corpus()
    qs = select(questions(), "dev")
    oracle = evaluate(qs, run_retriever(OracleRetriever(qs, chunks), qs, k=10), chunks)
    assert all(s.hit[1] == 1.0 and s.recall[5] == 1.0 for s in oracle)
    rand = evaluate(qs, run_retriever(RandomRetriever(chunks, seed=0), qs, k=1), chunks, ks=(1,))
    assert sum(s.hit[1] for s in rand) <= 1


def test_a_breakdown_gives_the_mean_of_a_metric_for_each_group():
    chunks = corpus()
    qs = select(questions(), "dev")
    scores = evaluate(qs, {"q1": ["c1"], "q4": ["c9"]}, chunks)
    by_type = breakdown(qs, scores, lambda q: q.type, "recall@5")
    assert by_type == {"lookup": (1.0, 1), "definition": (0.0, 1)}


# --- the report ---------------------------------------------------------------------------------------------


def test_the_summary_gives_each_metric_with_a_reproducible_interval():
    chunks = corpus()
    qs = select(questions(), "dev")
    scores = evaluate(qs, {"q1": ["c1"], "q4": ["c9"]}, chunks)
    summary = summarise_with_ci(scores, resamples=300, seed=1)
    assert summary["recall@5"][0] == 0.5 and summary["recall@5"][1] <= 0.5 <= summary["recall@5"][2]
    assert summary == summarise_with_ci(scores, resamples=300, seed=1)
    assert {"recall@5", "mrr", "ndcg@10", "hit@5", "recall@10"} <= set(summary)


def test_the_table_lists_each_variant_with_its_numbers_and_intervals():
    summary = {"recall@5": (0.5, 0.25, 0.75), "mrr": (0.4, 0.2, 0.6), "ndcg@10": (0.3, 0.1, 0.5),
               "hit@5": (0.6, 0.4, 0.8), "recall@10": (0.7, 0.5, 0.9)}  # fmt: skip
    table = format_table({"R1.1 BM25 plain": summary})
    assert "| R1.1 BM25 plain |" in table and "0.50 (0.25 to 0.75)" in table and table.startswith("| Variant")
