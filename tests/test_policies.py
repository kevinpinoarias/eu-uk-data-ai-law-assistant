"""
Tests for the index version policies (R8) and for collapsing duplicate copies of a unit in the results (R10).
"""

from __future__ import annotations

from law_assistant.chunk.chunker import Chunk
from law_assistant.evaluation.gold import GoldProvision, GoldQuestion
from law_assistant.retrieval.policies import (
    AsOfRetriever,
    CollapsedRetriever,
    current_text_only,
    original_text_only,
)


def chunk(id_, *, instrument="eu-ai-act", version="oj", unit="article", path=("4",), language="en", part=1):
    return Chunk(
        id=id_, instrument=instrument, jurisdiction="EU", language=language, version=version, unit=unit,
        unit_path=tuple(path), citation="x", heading=None, chapter=None, context="", text=id_,
        provision_ids=(), part=part, parts=2, words=1, order=0,
    )  # fmt: skip


def ids(chunks):
    return [c.id for c in chunks]


SET = [
    chunk("ai-oj-art4", version="oj"),
    chunk("ai-oj-rct12", version="oj", unit="recital", path=("12",)),
    chunk("ai-cons-art4", version="consolidated-20260727"),
    chunk("omnibus-oj", instrument="eu-ai-omnibus", version="oj"),
    chunk("uk-art6", instrument="uk-gdpr", version="revised-20261014"),
    chunk("es-art7", instrument="es-lopdgdd", version="as-of-20261014", language="es"),
]


def test_the_current_text_drops_the_original_articles_but_keeps_the_recitals_only_the_original_has():
    assert ids(current_text_only(SET)) == ["ai-oj-rct12", "ai-cons-art4", "omnibus-oj", "uk-art6", "es-art7"]


def test_the_original_text_drops_the_consolidated_chunks_of_texts_that_have_an_original():
    assert ids(original_text_only(SET)) == ["ai-oj-art4", "ai-oj-rct12", "omnibus-oj", "uk-art6", "es-art7"]


def test_a_text_with_one_version_is_left_alone_by_both_policies():
    only = [
        chunk("a", version="oj", instrument="eu-ai-omnibus"),
        chunk("b", instrument="uk-gdpr", version="r"),
    ]
    assert ids(current_text_only(only)) == ["a", "b"] and ids(original_text_only(only)) == ["a", "b"]


# --- collapsing copies -----------------------------------------------------------------------------------------


class Fixed:
    """A retriever that returns a fixed ranking, and remembers the depth it was asked for."""

    name = "fixed"

    def __init__(self, ranking):
        self.ranking, self.asked = list(ranking), []

    def search(self, query, k):
        self.asked.append(k)
        return self.ranking[:k]


COPIES = [
    chunk("en-oj", version="oj", language="en"),
    chunk("en-cons", version="consolidated-20260727", language="en"),
    chunk("es-cons", version="consolidated-20260727", language="es"),
    chunk("en-oj-part2", version="oj", language="en", part=2),
    chunk("other", path=("5",)),
]


def collapsed(by, ranking=("en-oj", "en-cons", "es-cons", "en-oj-part2", "other"), **kw):
    base = Fixed(ranking)
    return CollapsedRetriever(base, {c.id: c for c in COPIES}, by=by, **kw), base


def test_collapsing_copies_keeps_the_best_ranked_chunk_of_each_piece_across_versions_and_languages():
    r, _ = collapsed("copies")
    assert r.search("q", 10) == ["en-oj", "en-oj-part2", "other"]


def test_collapsing_units_keeps_one_chunk_per_article_even_if_it_is_another_piece():
    r, _ = collapsed("units")
    assert r.search("q", 10) == ["en-oj", "other"]


def test_the_base_retriever_is_asked_for_more_than_k_and_the_result_is_cut_to_k():
    r, base = collapsed("copies", depth=50)
    assert r.search("q", 2) == ["en-oj", "en-oj-part2"] and base.asked == [50]


def test_an_unknown_way_of_collapsing_is_refused():
    import pytest

    with pytest.raises(ValueError, match="by"):
        collapsed("nonsense")


# --- the as-of router --------------------------------------------------------------------------------------------


def question(id_, text, as_of):
    return GoldQuestion(
        id=id_, language="en", text=text, type="as_of", route="retrieve", phrasing="lay",
        jurisdictions=("EU",), gold=(GoldProvision("eu-ai-act", "article", ("4",)),),
        expected_answer="x", author="claude", as_of=as_of,
    )  # fmt: skip


def test_a_question_about_the_past_goes_to_the_original_text_and_any_other_to_the_current_text():
    early, late = Fixed(["from-original"]), Fixed(["from-current"])
    qs = [
        question("q1", "old?", "2025-06-01"),
        question("q2", "now?", "2026-10-14"),
        question("q3", "undated?", None),
    ]
    router = AsOfRetriever(qs, early=early, late=late, cutoff="2026-07-27")
    assert router.search("old?", 5) == ["from-original"]
    assert router.search("now?", 5) == ["from-current"]
    assert router.search("undated?", 5) == ["from-current"]


def test_text_before_the_amendment_is_the_original_text_without_the_amending_regulation():
    from law_assistant.retrieval.policies import before_amendment_text

    chunks = [
        chunk("orig", version="oj"),
        chunk("cons", version="consolidated-20260727"),
        chunk("amend", instrument="eu-ai-omnibus", version="oj"),
        chunk("uk", instrument="uk-gdpr", version="revised-20261014"),
    ]
    assert ids(before_amendment_text(chunks)) == ["orig", "uk"]
