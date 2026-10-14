"""
Checks of the EU parser against the real downloaded Official Journal files: known totals, the structural checks,
the same skeleton in English and Spanish, near-complete coverage, and a handful of golden provisions whose exact
text was compared with the official text.

These need the files in data/raw/ (run `python -m law_assistant.fetch.eu`). They are skipped when the files are
absent, as in CI, and run on any machine that has fetched them.
"""

from __future__ import annotations

import pytest

from law_assistant import settings
from law_assistant.parse.checks import check_structure, compare_skeletons, coverage_ratio
from law_assistant.parse.eu_oj import parse_eu_oj, source_characters
from law_assistant.parse.run_eu import DOCUMENTS, LANGUAGES, UNIT_WORDS

RAW = settings.RAW_DIR / "eur_lex_cellar"

pytestmark = pytest.mark.skipif(
    not (RAW / "eu-gdpr-oj-en.xhtml").exists(),
    reason="the EU files are not downloaded (run: python -m law_assistant.fetch.eu)",
)


@pytest.fixture(scope="module")
def parsed():
    out = {}
    for key, instrument, expected, allowed_diff in DOCUMENTS:
        for lang in LANGUAGES:
            data = (RAW / f"{key}-{lang}.xhtml").read_bytes()
            out[(key, lang)] = (
                parse_eu_oj(data, instrument=instrument, language=lang),
                source_characters(data),
                expected,
                allowed_diff,
            )
    return out


@pytest.mark.parametrize("key", [d[0] for d in DOCUMENTS])
@pytest.mark.parametrize("lang", LANGUAGES)
def test_known_totals_and_structure_hold(parsed, key, lang):
    provisions, _, expected, _ = parsed[(key, lang)]
    assert check_structure(provisions, **expected) == []


@pytest.mark.parametrize("key", [d[0] for d in DOCUMENTS])
@pytest.mark.parametrize("lang", LANGUAGES)
def test_nothing_is_lost_or_duplicated(parsed, key, lang):
    provisions, source_chars, _, _ = parsed[(key, lang)]
    ratio = coverage_ratio(provisions, source_characters=source_chars, unit_words=UNIT_WORDS[lang])
    assert 0.995 <= ratio <= 1.001


def test_the_gdpr_has_exactly_the_same_skeleton_in_english_and_spanish(parsed):
    en, es = parsed[("eu-gdpr-oj", "en")][0], parsed[("eu-gdpr-oj", "es")][0]
    assert compare_skeletons(en, es) == []


def test_the_ai_act_skeletons_differ_only_in_annex_x_where_english_leaves_single_items_unlabelled(parsed):
    en, es = parsed[("eu-ai-act-oj", "en")][0], parsed[("eu-ai-act-oj", "es")][0]
    diffs = compare_skeletons(en, es)
    assert diffs and all("anx-X/" in d for d in diffs) and len(diffs) <= 4


def provision(parsed, key, lang, id_):
    return next(p for p in parsed[(key, lang)][0] if p.id == id_)


def test_gdpr_article_6_1_f_legitimate_interests_in_english(parsed):
    p = provision(parsed, "eu-gdpr-oj", "en", "eu-gdpr/art-6/1/f")
    assert p.text == (
        "processing is necessary for the purposes of the legitimate interests pursued by the controller or by "
        "a third party, except where such interests are overridden by the interests or fundamental rights and "
        "freedoms of the data subject which require protection of personal data, in particular where the data "
        "subject is a child."
    )
    assert (p.heading, p.chapter) == ("Lawfulness of processing", "CHAPTER II — Principles")


def test_gdpr_article_6_1_f_in_spanish_has_the_same_place_in_the_law(parsed):
    p = provision(parsed, "eu-gdpr-oj", "es", "eu-gdpr/art-6/1/f")
    assert p.text.startswith("el tratamiento es necesario para la satisfacción de intereses legítimos")
    assert p.text.endswith("en particular cuando el interesado sea un niño.")
    assert (p.heading, p.chapter) == ("Licitud del tratamiento", "CAPÍTULO II — Principios")


def test_gdpr_article_6_1_closing_sentence_is_kept(parsed):
    p = provision(parsed, "eu-gdpr-oj", "en", "eu-gdpr/art-6/1~closing")
    assert p.text == (
        "Point (f) of the first subparagraph shall not apply to processing carried out by public authorities "
        "in the performance of their tasks."
    )


def test_gdpr_definition_of_personal_data_in_both_languages(parsed):
    en = provision(parsed, "eu-gdpr-oj", "en", "eu-gdpr/art-4/1")
    es = provision(parsed, "eu-gdpr-oj", "es", "eu-gdpr/art-4/1")
    assert en.text.startswith(
        "‘personal data’ means any information relating to an identified or identifiable"
    )
    assert en.text.endswith("genetic, mental, economic, cultural or social identity of that natural person;")
    assert es.text.startswith("«datos personales»: toda información sobre una persona física identificada")


def test_gdpr_recital_47_is_a_recital_with_no_article_context(parsed):
    p = provision(parsed, "eu-gdpr-oj", "en", "eu-gdpr/rct-47")
    assert (p.unit, p.kind, p.heading, p.chapter) == ("recital", "recital", None, None)
    assert p.text.startswith("The legitimate interests of a controller")
    assert p.text.endswith("may be regarded as carried out for a legitimate interest.")


def test_gdpr_final_article_gives_the_application_date(parsed):
    assert (
        provision(parsed, "eu-gdpr-oj", "en", "eu-gdpr/art-99/2").text == "It shall apply from 25 May 2018."
    )


def test_ai_act_article_5_prohibits_subliminal_techniques_and_annex_iii_lists_biometrics(parsed):
    a = provision(parsed, "eu-ai-act-oj", "en", "eu-ai-act/art-5/1/a")
    assert a.text.startswith("the placing on the market, the putting into service or the use of an AI system")
    assert "subliminal techniques" in a.text
    annex = provision(parsed, "eu-ai-act-oj", "en", "eu-ai-act/anx-III")
    assert (
        annex.text
        == "High-risk AI systems pursuant to Article 6(2) are the AI systems listed in any of the following areas:"
    )
    biometrics = provision(parsed, "eu-ai-act-oj", "en", "eu-ai-act/anx-III/1/a")
    assert biometrics.text.startswith("remote biometric identification systems.")


def test_ai_act_official_journal_text_still_says_2_august_2026_the_omnibus_moves_it(parsed):
    original = provision(parsed, "eu-ai-act-oj", "en", "eu-ai-act/art-113")
    assert "It shall apply from 2 August 2026." in original.text
    omnibus = [p for p in parsed[("eu-ai-omnibus-oj", "en")][0] if "2 December 2027" in p.text]
    assert any(p.unit == "article" for p in omnibus)
