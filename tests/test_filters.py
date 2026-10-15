"""
Tests for filters (R6): restrict the chunks a question is searched in by jurisdiction and by language, using
what the question says (or, as an upper bound, the gold labels).
"""

from __future__ import annotations

from law_assistant.chunk.chunker import Chunk
from law_assistant.retrieval.filters import FilteredRetriever, allowed_jurisdictions, language_filter


def chunk(cid, jurisdiction="EU", language="en", instrument="eu-gdpr"):
    return Chunk(
        id=cid, instrument=instrument, jurisdiction=jurisdiction, language=language, version="v",
        unit="article", unit_path=(cid,), citation=cid, heading=None, chapter=None, context="c",
        text="t", provision_ids=(cid,), part=1, parts=1, words=1, order=0,
    )  # fmt: skip


CHUNKS = [
    chunk("eu-en", "EU", "en"),
    chunk("eu-es", "EU", "es"),
    chunk("uk-en", "UK", "en", "uk-gdpr"),
    chunk("es-es", "ES", "es", "es-lopdgdd"),
]


class Ranked:
    name = "base"

    def __init__(self, order):
        self.order, self.asked = order, []

    def scored(self, query, k):
        self.asked.append(k)
        return [(i, 1.0 - n / 10) for n, i in enumerate(self.order[:k])]

    def search(self, query, k):
        return [i for i, _ in self.scored(query, k)]


def test_no_named_jurisdiction_means_no_restriction():
    assert allowed_jurisdictions(()) is None


def test_a_spanish_question_also_searches_eu_law_because_spanish_law_rests_on_it():
    assert allowed_jurisdictions(("ES",)) == {"ES", "EU"}


def test_eu_and_uk_questions_search_just_what_they_name():
    assert allowed_jurisdictions(("EU",)) == {"EU"}
    assert allowed_jurisdictions(("UK",)) == {"UK"}
    assert allowed_jurisdictions(("EU", "UK")) == {"EU", "UK"}


def test_a_jurisdiction_filter_keeps_the_ranking_order_of_the_chunks_it_allows():
    base = Ranked(["uk-en", "eu-en", "es-es", "eu-es"])
    retriever = FilteredRetriever(base, CHUNKS, lambda q, c: c.jurisdiction in {"EU"})
    assert retriever.search("q", 2) == ["eu-en", "eu-es"]
    assert base.asked == [len(CHUNKS)]  # the whole ranking is filtered, so nothing allowed is missed


def test_the_language_filter_prefers_the_questions_language_where_a_text_exists_in_both():
    keep = language_filter(CHUNKS)
    assert keep("en", CHUNKS[0]) and not keep("en", CHUNKS[1])  # eu in both languages: keep English
    assert keep("es", CHUNKS[1]) and not keep("es", CHUNKS[0])
    assert keep("en", CHUNKS[2])  # uk exists only in English: kept for a Spanish or English question
    assert keep("es", CHUNKS[2])
    assert keep("en", CHUNKS[3])  # the Spanish law exists only in Spanish: kept for an English question


def test_the_name_says_what_is_filtered():
    retriever = FilteredRetriever(Ranked([]), CHUNKS, lambda q, c: True, name="jurisdiction")
    assert retriever.name == "base+jurisdiction"
