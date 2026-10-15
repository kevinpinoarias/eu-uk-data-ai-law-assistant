"""
Tests for the answer pipeline: the steps wired in order with fakes for the router, the table picker, the
search and the language model, so each path (answer, table figure, refusal, abstention) is checked on its own.
"""

from __future__ import annotations

from law_assistant.answer.generate import Draft
from law_assistant.answer.pipeline import AnswerPipeline, Result
from law_assistant.answer.router import Route
from law_assistant.answer.verify import Citation
from law_assistant.chunk.chunker import Chunk
from law_assistant.facts.table import Fact, FactSource


def chunk(cid, text, version="consolidated-20260727"):
    return Chunk(
        id=cid, instrument="eu-gdpr", jurisdiction="EU", language="en", version=version, unit="article",
        unit_path=("6",), citation="Article 6", heading=None, chapter=None,
        context="GDPR | Chapter II | Article 6: Lawfulness", text=text, provision_ids=("eu-gdpr/art-6/1",),
        part=1, parts=1, words=len(text.split()), order=0,
    )  # fmt: skip


CHUNKS = [
    chunk("c1", "Processing shall be lawful only if the data subject has given consent."),
    chunk("c2", "Older wording of the same rule.", version="oj"),
]
FACT = Fact(
    key="gdpr-age", kind="age", jurisdictions=("EU",), subject_en="Age of consent", subject_es="Edad",
    value={"age": 16}, summary_en="The age is 16 (GDPR Article 8(1)).", summary_es="La edad es 16 (RGPD art. 8.1).",
    sources=(FactSource("eu-gdpr", "article", ("8",), quotes=("sixteen years",)),),
    caveat_en="Member States may lower it to 13.", caveat_es="Los Estados pueden bajarla a 13.",
)  # fmt: skip


class FakeRouter:
    def __init__(self, route):
        self._route, self.seen = route, []

    def route(self, text):
        self.seen.append(text)
        return self._route


class FakePicker:
    def __init__(self, fact):
        self.fact = fact

    def pick(self, question, jurisdictions=()):
        return self.fact


class FakeRetriever:
    def __init__(self, ids, name="r"):
        self.ids, self.name, self.asked = ids, name, []

    def search(self, query, k):
        self.asked.append((query, k))
        return self.ids[:k]


class FakeWriter:
    def __init__(self, draft):
        self.draft, self.calls = draft, []

    def write(self, question, language, chunks, *, as_of=None):
        self.calls.append((question, language, [c.id for c in chunks], as_of))
        return self.draft


def pipeline(route=None, draft=None, fact=FACT, current=None, full=None, original=None, k=5):
    draft = draft or Draft(True, "Consent is needed.", [Citation(1, "has given consent")])
    parts = {
        "router": FakeRouter(route or Route("retrieve")),
        "picker": FakePicker(fact),
        "current": current or FakeRetriever(["c1"], "current"),
        "full": full or FakeRetriever(["c2", "c1"], "full"),
        "original": original or FakeRetriever(["c2"], "original"),
        "writer": FakeWriter(draft),
    }
    p = AnswerPipeline(
        router=parts["router"], picker=parts["picker"], current=parts["current"], full=parts["full"],
        original=parts["original"], writer=parts["writer"], chunks=CHUNKS, k=k,
    )  # fmt: skip
    return p, parts


def test_a_supported_answer_is_shown_with_the_verified_quote_and_a_label_for_the_source():
    p, _ = pipeline()
    result = p.ask("Do I need consent?")
    assert isinstance(result, Result) and result.kind == "answer"
    assert result.text.startswith("Consent is needed.")
    assert "GDPR, Article 6 (consolidated text of 27 July 2026)" in result.text
    assert "has given consent" in result.text and "not legal advice" in result.text.lower()
    assert [s.chunk_id for s in result.sources] == ["c1"]


def test_a_spanish_question_gets_spanish_framing():
    p, _ = pipeline()
    result = p.ask("¿Necesito consentimiento para tratar datos?")
    assert result.language == "es" and "Fuentes" in result.text and "asesoramiento jurídico" in result.text


def test_a_table_question_is_answered_from_the_table_without_the_language_model():
    p, parts = pipeline(route=Route("table"))
    result = p.ask("What is the age of consent in the EU?")
    assert (
        result.kind == "table" and "The age is 16" in result.text and "Member States may lower" in result.text
    )
    assert "GDPR" in result.text and "Article 8" in result.text
    assert parts["writer"].calls == [] and parts["current"].asked == []


def test_a_table_question_with_no_matching_row_falls_back_to_searching_the_text():
    p, parts = pipeline(route=Route("table"), fact=None)
    assert p.ask("What is the age of consent?").kind == "answer"
    assert parts["writer"].calls


def test_a_refusal_for_another_countrys_law_never_searches_or_writes():
    p, parts = pipeline(route=Route("refuse", "out_of_corpus"))
    result = p.ask("What does the CCPA say?")
    assert result.kind == "refused" and result.reason == "out_of_corpus"
    assert "another country" in result.text
    assert parts["writer"].calls == [] and parts["current"].asked == []


def test_a_refusal_for_advice_is_in_the_questions_language():
    p, _ = pipeline(route=Route("refuse", "legal_advice"))
    result = p.ask("¿Es legal mi tienda online? Ayer perdimos datos.")
    assert result.kind == "refused" and "abogado" in result.text


def test_when_the_model_says_the_passages_do_not_answer_the_pipeline_abstains():
    p, _ = pipeline(draft=Draft(False, "The passages do not cover it.", []))
    result = p.ask("Something unrelated?")
    assert result.kind == "abstained" and "enough" in result.text


def test_an_answer_whose_every_quote_fails_the_check_is_not_shown():
    p, _ = pipeline(draft=Draft(True, "Invented claim.", [Citation(1, "a sentence that is not in the law")]))
    result = p.ask("q?")
    assert result.kind == "abstained" and "Invented claim" not in result.text
    assert result.trace["invalid_citations"][0][1] == "the quote is not in the passage"


def test_an_answer_with_no_citation_at_all_is_not_shown():
    p, _ = pipeline(draft=Draft(True, "An unsupported claim.", []))
    assert p.ask("q?").kind == "abstained"


def test_one_bad_quote_among_good_ones_is_dropped_and_the_answer_stays():
    cites = [Citation(1, "has given consent"), Citation(1, "this was never written")]
    p, _ = pipeline(draft=Draft(True, "Consent is needed.", cites))
    result = p.ask("q?")
    assert result.kind == "answer" and "never written" not in result.text
    assert len(result.trace["invalid_citations"]) == 1


def test_without_a_date_the_current_text_is_searched_and_with_an_early_date_the_original_text_is():
    p, parts = pipeline()
    p.ask("What does the rule say?")
    assert parts["current"].asked and not parts["original"].asked and not parts["full"].asked
    p.ask("What did the rule say on 1 January 2025?")
    assert parts["original"].asked and not parts["full"].asked
    assert parts["writer"].calls[-1][3] == "2025-01-01"


def test_a_question_about_the_wording_as_first_published_searches_every_version():
    p, parts = pipeline()
    p.ask("How was Article 37 worded as first published in the Official Journal?")
    assert parts["full"].asked and not parts["current"].asked


def test_a_date_after_the_amendment_uses_the_current_text():
    p, parts = pipeline()
    p.ask("What did the rule say on 1 September 2026?")
    assert parts["current"].asked and not parts["original"].asked


def test_the_trace_records_what_each_step_decided_and_how_long_it_took():
    p, _ = pipeline()
    result = p.ask("Do I need consent in the EU?")
    assert result.trace["route"] == "retrieve" and result.trace["jurisdictions"] == ("EU",)
    assert {"understand", "route", "retrieve", "generate", "verify"} <= set(result.timings)
    assert all(t >= 0 for t in result.timings.values())


def test_passages_are_numbered_in_search_order_and_at_most_k_are_given_to_the_writer():
    ids = ["c1", "c2"]
    p, parts = pipeline(current=FakeRetriever(ids, "current"), k=1)
    p.ask("q?")
    assert parts["writer"].calls[0][2] == ["c1"]


def test_without_version_awareness_an_early_date_uses_the_full_index_and_original_wording_is_ignored():
    p, parts = pipeline()
    p._version_aware = False
    p.ask("What did the rule say on 1 January 2025?")
    p.ask("How was it worded as first published in the Official Journal?")
    assert parts["full"].asked and not parts["original"].asked
    assert len(parts["current"].asked) == 1
