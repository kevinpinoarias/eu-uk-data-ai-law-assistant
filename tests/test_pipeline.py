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
        self.draft, self.calls, self.advice = draft, [], []

    def write(self, question, language, chunks, *, as_of=None, advice=False):
        self.calls.append((question, language, [c.id for c in chunks], as_of))
        self.advice.append(advice)
        return self.draft


def pipeline(
    route=None, draft=None, fact=FACT, current=None, full=None, original=None, k=5, advice_mode="refuse",
    writer=None, fallback_router=None, advice_rewriter=None,
):  # fmt: skip
    draft = draft or Draft(True, "Consent is needed.", [Citation(1, "has given consent")])
    parts = {
        "router": FakeRouter(route or Route("retrieve")),
        "picker": FakePicker(fact),
        "current": current or FakeRetriever(["c1"], "current"),
        "full": full or FakeRetriever(["c2", "c1"], "full"),
        "original": original or FakeRetriever(["c2"], "original"),
        "writer": writer or FakeWriter(draft),
    }
    p = AnswerPipeline(
        router=parts["router"], picker=parts["picker"], current=parts["current"], full=parts["full"],
        original=parts["original"], writer=parts["writer"], chunks=CHUNKS, k=k, advice_mode=advice_mode,
        fallback_router=fallback_router, advice_rewriter=advice_rewriter,
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


ADVICE = Route("refuse", "legal_advice")


def test_by_default_a_request_for_advice_is_still_refused_so_earlier_measurements_can_be_reproduced():
    p, parts = pipeline(route=ADVICE)
    result = p.ask("Can I use customer data to train a model?")
    assert result.kind == "refused" and result.notice is None and parts["writer"].calls == []


def test_in_general_mode_a_request_for_advice_gets_an_answer_from_the_texts_with_a_notice():
    p, parts = pipeline(route=ADVICE, advice_mode="general")
    result = p.ask("Can I use customer data to train a model?")
    assert result.kind == "answer" and result.text.startswith("Consent is needed.")
    assert result.notice and "not legal advice" in result.notice.lower() and "lawyer" in result.notice
    assert parts["writer"].advice == [True]  # the writer is told to explain in general terms, not to decide
    assert result.reason == "legal_advice" and result.sources  # the quotations are still checked and shown


def test_the_notice_is_in_the_questions_language():
    p, _ = pipeline(route=ADVICE, advice_mode="general")
    result = p.ask("¿Puedo usar los datos de mis clientes para entrenar un modelo?")
    assert (
        result.language == "es"
        and "abogado" in result.notice
        and "no es asesoramiento" in result.notice.lower()
    )


def test_an_ordinary_answer_carries_no_notice_and_the_writer_is_not_asked_for_advice_mode():
    p, parts = pipeline(advice_mode="general")
    result = p.ask("Do I need consent?")
    assert result.notice is None and parts["writer"].advice == [False]


def test_other_refusals_stay_refusals_in_general_mode():
    p, parts = pipeline(route=Route("refuse", "out_of_corpus"), advice_mode="general")
    result = p.ask("What does the CCPA say?")
    assert result.kind == "refused" and result.notice is None and parts["writer"].calls == []


def test_an_unsupported_advice_answer_still_abstains_and_still_carries_the_notice():
    p, _ = pipeline(
        route=ADVICE,
        advice_mode="general",
        draft=Draft(True, "Made up.", [Citation(1, "words that are not there")]),
    )
    result = p.ask("Can I use customer data to train a model?")
    assert result.kind == "abstained" and result.notice


def test_with_the_model_down_the_passages_are_shown_with_the_notice():
    p, _ = pipeline(
        route=ADVICE, advice_mode="general", writer=DownWriter(), fallback_router=FakeRouter(ADVICE)
    )
    result = p.ask("Can I use customer data to train a model?")
    assert result.kind == "sources" and result.notice and result.sources


def test_an_advice_question_is_searched_with_its_restatement_added_and_an_ordinary_one_is_not():
    seen = []

    def rewrite(q):
        seen.append(q)
        return "What does the GDPR say about further processing?"

    current = FakeRetriever(["c1"], "current")
    p, _ = pipeline(route=ADVICE, advice_mode="general", current=current, advice_rewriter=rewrite)
    p.ask("Can I reuse my customers' data?")
    assert seen == ["Can I reuse my customers' data?"]
    assert (
        current.asked[0][0]
        == "Can I reuse my customers' data?\nWhat does the GDPR say about further processing?"
    )

    current2 = FakeRetriever(["c1"], "current")
    p2, _ = pipeline(advice_mode="general", current=current2, advice_rewriter=rewrite)
    p2.ask("Do I need consent?")
    assert current2.asked[0][0] == "Do I need consent?" and seen == ["Can I reuse my customers' data?"]


def test_an_empty_restatement_leaves_the_question_alone():
    current = FakeRetriever(["c1"], "current")
    p, _ = pipeline(route=ADVICE, advice_mode="general", current=current, advice_rewriter=lambda q: "")
    p.ask("Can I reuse my customers' data?")
    assert current.asked[0][0] == "Can I reuse my customers' data?"


def test_when_an_advice_question_cannot_be_supported_the_reply_suggests_how_to_ask_it():
    p, _ = pipeline(route=ADVICE, advice_mode="general", draft=Draft(False, "Not covered.", []))
    result = p.ask("Can I reuse my customers' data?")
    assert result.kind == "abstained" and result.notice
    assert "what a specific law says" in result.text and "GDPR" in result.text
    es, _ = pipeline(route=ADVICE, advice_mode="general", draft=Draft(False, "No cubierto.", []))
    reply = es.ask("¿Puedo reutilizar los datos de mis clientes?")
    assert "qué dice una ley concreta" in reply.text
    plain, _ = pipeline(draft=Draft(False, "Not covered.", []))
    assert (
        "what a specific law says" not in plain.ask("Something unrelated?").text
    )  # ordinary reply unchanged


def test_the_trace_shows_that_a_question_was_handled_in_advice_mode():
    p, _ = pipeline(route=ADVICE, advice_mode="general")
    result = p.ask("Can I use customer data to train a model?")
    assert result.trace["route"] == "retrieve" and result.trace["reason"] == "legal_advice"
    assert result.trace["advice"] is True


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


# --- degraded mode: the language model is unavailable ---------------------------------------------------------
from law_assistant.answer.facts_lookup import FactMatch  # noqa: E402
from law_assistant.llm.gemini import LLMError  # noqa: E402


class DownRouter:
    def route(self, text):
        raise LLMError("HTTP 429: the quota is used up")


class DownPicker:
    def pick(self, question, jurisdictions=()):
        raise LLMError("down")


class DownWriter:
    def write(self, *args, **kwargs):
        raise LLMError("down")


class FakeMatcher:
    def __init__(self, fact):
        self.fact, self.asked = fact, []

    def match(self, question, language, jurisdictions=()):
        self.asked.append((question, language, tuple(jurisdictions)))
        return FactMatch(self.fact, 0.7 if self.fact else 0.2)


class RulesFake:
    name = "rules"

    def __init__(self, route):
        self._route = route

    def route(self, text):
        return self._route


def degraded(router=None, picker=None, writer=None, matcher=None, fallback=None):
    return AnswerPipeline(
        router=router or DownRouter(), picker=picker or DownPicker(), current=FakeRetriever(["c1", "c2"], "c"),
        full=FakeRetriever(["c1"], "f"), writer=writer or DownWriter(), chunks=CHUNKS, k=5,
        fallback_router=fallback, fallback_matcher=matcher,
    )  # fmt: skip


def test_without_a_fallback_a_model_error_still_stops_the_pipeline():
    p = AnswerPipeline(
        router=DownRouter(), picker=FakePicker(FACT), current=FakeRetriever(["c1"]), full=FakeRetriever(["c1"]),
        writer=FakeWriter(Draft(True, "x", [])), chunks=CHUNKS,
    )  # fmt: skip
    import pytest

    with pytest.raises(LLMError):
        p.ask("What is the age of consent?")


def test_when_the_router_is_down_the_rules_route_a_figure_question_and_the_matcher_finds_the_row():
    p = degraded(fallback=RulesFake(Route("table")), matcher=FakeMatcher(FACT))
    result = p.ask("What is the age of consent in the EU?")
    assert result.kind == "table" and "The age is 16" in result.text
    assert result.trace["degraded"] is True and result.trace["fact_key"] == "gdpr-age"


def test_a_refusal_needs_no_model_at_all_even_when_the_router_is_down():
    p = degraded(fallback=RulesFake(Route("refuse", "out_of_corpus")), matcher=FakeMatcher(None))
    result = p.ask("What does the CCPA say?")
    assert result.kind == "refused" and result.reason == "out_of_corpus" and result.trace["degraded"] is True


def test_when_the_picker_is_down_the_matcher_chooses_the_row_but_a_poor_match_falls_back_to_the_text():
    ok = degraded(router=FakeRouter(Route("table")), matcher=FakeMatcher(FACT))
    assert ok.ask("What is the age of consent?").kind == "table"
    poor = degraded(router=FakeRouter(Route("table")), matcher=FakeMatcher(None))
    result = poor.ask("What is the age of consent?")
    assert result.kind == "sources"  # no row matched, and the writer is down too


def test_when_the_writer_is_down_the_passages_are_shown_without_an_answer_and_without_inventing_one():
    p = degraded(router=FakeRouter(Route("retrieve")), picker=FakePicker(FACT), matcher=FakeMatcher(FACT))
    result = p.ask("Do I need consent?")
    assert result.kind == "sources" and result.trace["degraded"] is True
    assert "unavailable" in result.text.lower() and "Processing shall be lawful" in result.text
    assert "GDPR, Article 6" in result.text and [s.chunk_id for s in result.sources] == ["c1", "c2"]


def test_the_degraded_message_is_in_the_questions_language():
    p = degraded(router=FakeRouter(Route("retrieve")), matcher=FakeMatcher(None))
    result = p.ask("¿Necesito consentimiento para tratar datos?")
    assert result.kind == "sources" and "no está disponible" in result.text


def test_a_working_pipeline_is_not_marked_degraded():
    p, _ = pipeline()
    assert p.ask("Do I need consent?").trace["degraded"] is False
