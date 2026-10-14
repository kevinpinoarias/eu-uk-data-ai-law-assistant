"""
The gold checks against the real parsed corpus: the corpus loads, a gold provision is found by instrument, unit,
version and language, and a quote is matched in the right text. These need data/parsed/ and are skipped without it.
"""

from __future__ import annotations

import pytest

from law_assistant import settings
from law_assistant.evaluation.checks import (
    Corpus,
    check_against_corpus,
    check_questions,
    overlap_ratio,
    overlap_warnings,
)
from law_assistant.evaluation.gold import GoldProvision, GoldQuestion

pytestmark = pytest.mark.skipif(
    len(list(settings.PARSED_DIR.glob("*.jsonl"))) < 14,
    reason="the parsed documents are not built (run the parsers in law_assistant.parse)",
)


@pytest.fixture(scope="module")
def corpus():
    return Corpus.from_dir()


def question(id_, text, gold, language="es", **kw):
    base = dict(
        id=id_,
        language=language,
        text=text,
        type="lookup",
        route="retrieve",
        phrasing="lay",
        jurisdictions=("ES",),
        gold=tuple(gold),
        expected_answer="x",
        author="claude",
    )
    return GoldQuestion(**{**base, **kw})


def test_the_corpus_holds_all_seven_instruments(corpus):
    assert corpus.instruments() == {
        "eu-gdpr",
        "eu-ai-act",
        "eu-ai-omnibus",
        "uk-gdpr",
        "uk-dpa-2018",
        "uk-duaa-2025",
        "es-lopdgdd",
    }


def test_the_age_of_consent_in_spain_is_found_by_unit_pinpoint_and_quote(corpus):
    g = GoldProvision(
        instrument="es-lopdgdd",
        unit="article",
        unit_path=("7",),
        pinpoints=("es-lopdgdd/art-7/1",),
        quotes=("únicamente podrá fundarse en su consentimiento cuando sea mayor de catorce años",),
    )
    q = question("q001", "¿A qué edad puede un menor dar su consentimiento en España?", [g])
    assert check_questions([q]) == [] and check_against_corpus([q], corpus) == []


def test_overlap_tells_a_copied_question_from_a_lay_one_on_the_real_corpus(corpus):
    g = GoldProvision("es-lopdgdd", "article", ("7",))
    copied = question(
        "q010",
        "El tratamiento de los datos personales de un menor de edad únicamente podrá fundarse en su "
        "consentimiento cuando sea mayor de catorce años",
        [g],
    )
    lay = question("q011", "¿Desde cuándo puede un chaval aceptar que una web use sus datos?", [g])
    texts = corpus.unit_texts(g, "es")
    idf = corpus.idf("es")
    assert overlap_ratio(copied.text, texts, idf) > 0.8 > overlap_ratio(lay.text, texts, idf)
    assert any("q010" in w for w in overlap_warnings([copied, lay], corpus))
    assert not any("q011" in w for w in overlap_warnings([copied, lay], corpus))


def test_a_disposition_and_a_recital_and_an_annex_are_found(corpus):
    gold = [
        GoldProvision(
            "es-lopdgdd",
            "disposition",
            ("derogatoria", "única"),
            quotes=("Queda derogado el Real Decreto-ley 5/2018",),
        ),
        GoldProvision("eu-gdpr", "recital", ("47",), quotes=("legitimate interests of a controller",)),
        GoldProvision("eu-ai-act", "annex", ("VI",), quotes=("internal control",)),
    ]
    assert check_against_corpus([question("q002", "Any?", gold)], corpus) == []


def test_a_uk_only_provision_is_found_and_is_not_in_the_eu_text(corpus):
    uk = GoldProvision("uk-gdpr", "article", ("22A",), quotes=("significant decision",))
    assert check_against_corpus([question("q003", "Any?", [uk], language="en")], corpus) == []
    eu = GoldProvision("eu-gdpr", "article", ("22A",))
    assert any(
        "unit" in p for p in check_against_corpus([question("q004", "Other?", [eu], language="en")], corpus)
    )


def test_the_version_decides_which_wording_a_quote_is_checked_against(corpus):
    original = GoldProvision("eu-ai-act", "article", ("113",), version="oj", quotes=("2 August 2026",))
    amended = GoldProvision(
        "eu-ai-act", "article", ("113",), version="consolidated-20260727", quotes=("2 December 2027",)
    )
    assert (
        check_against_corpus(
            [question("q005", "Any?", [original, amended], language="en", jurisdictions=("EU",))], corpus
        )
        == []
    )
    wrong = GoldProvision("eu-ai-act", "article", ("113",), version="oj", quotes=("2 December 2027",))
    assert any(
        "quote" in p
        for p in check_against_corpus([question("q006", "Other?", [wrong], language="en")], corpus)
    )
