"""
Checks of the EU parsers against the real downloaded files (Official Journal and consolidated texts): known
totals, the structural checks, the same skeleton in English and Spanish, near-complete coverage, the
consolidated texts against the Official Journal texts, and golden provisions whose exact text was compared
with the official text.

These need the files in data/raw/ (run `python -m law_assistant.fetch.eu`). They are skipped when the files are
absent, as in CI, and run on any machine that has fetched them.
"""

from __future__ import annotations

import re

import pytest

from law_assistant import settings
from law_assistant.parse.checks import check_structure, compare_skeletons, compare_texts, coverage_ratio
from law_assistant.parse.run_eu import LANGUAGES, SPECS, UNIT_WORDS, parse_spec

RAW = settings.RAW_DIR / "eur_lex_cellar"

pytestmark = pytest.mark.skipif(
    not (RAW / "eu-gdpr-oj-en.xhtml").exists(),
    reason="the EU files are not downloaded (run: python -m law_assistant.fetch.eu)",
)

SPEC_KEYS = [spec.key for spec in SPECS]


@pytest.fixture(scope="module")
def parsed():
    """{(cache key, language): Parsed} for every text and language."""
    out = {}
    for spec in SPECS:
        for lang, doc in parse_spec(settings.RAW_DIR, spec).items():
            out[(spec.key, lang)] = doc
    return out


def spec_of(key):
    return next(s for s in SPECS if s.key == key)


@pytest.mark.parametrize("key", SPEC_KEYS)
@pytest.mark.parametrize("lang", LANGUAGES)
def test_known_totals_and_structure_hold(parsed, key, lang):
    assert check_structure(parsed[(key, lang)].provisions, **spec_of(key).expected) == []


@pytest.mark.parametrize("key", SPEC_KEYS)
@pytest.mark.parametrize("lang", LANGUAGES)
def test_nothing_is_lost_or_duplicated(parsed, key, lang):
    doc = parsed[(key, lang)]
    ratio = coverage_ratio(doc.provisions, source_characters=doc.source_chars, unit_words=UNIT_WORDS[lang])
    assert 0.995 <= ratio <= 1.001


@pytest.mark.parametrize("key", [s.key for s in SPECS if s.allowed_diff is not None])
def test_english_and_spanish_have_the_same_skeleton_up_to_the_known_differences(parsed, key):
    diffs = compare_skeletons(
        parsed[(key, "en")].provisions, parsed[(key, "es")].provisions, normalise_inserted_labels=True
    )
    assert len(diffs) <= spec_of(key).allowed_diff


def test_the_gdpr_has_exactly_the_same_skeleton_in_english_and_spanish_in_both_versions(parsed):
    for key in ("eu-gdpr-oj", "eu-gdpr-consolidated"):
        assert compare_skeletons(parsed[(key, "en")].provisions, parsed[(key, "es")].provisions) == []


def test_the_ai_act_official_journal_skeletons_differ_only_in_annex_x(parsed):
    en, es = parsed[("eu-ai-act-oj", "en")].provisions, parsed[("eu-ai-act-oj", "es")].provisions
    diffs = compare_skeletons(en, es)
    assert diffs and all("anx-X/" in d for d in diffs)


def test_the_new_annex_xiv_is_the_only_skeleton_difference_in_the_consolidated_ai_act(parsed):
    key = "eu-ai-act-consolidated-20260727"
    diffs = compare_skeletons(
        parsed[(key, "en")].provisions, parsed[(key, "es")].provisions, normalise_inserted_labels=True
    )
    assert diffs and all("anx-XIV/" in d for d in diffs)


def provision(parsed, key, lang, id_):
    return next(p for p in parsed[(key, lang)].provisions if p.id == id_)


# --- the consolidated GDPR against the Official Journal text ---------------------------------------------------


@pytest.mark.parametrize("lang", LANGUAGES)
def test_the_consolidated_gdpr_has_the_same_provisions_as_the_official_journal_text(parsed, lang):
    oj = [p for p in parsed[("eu-gdpr-oj", lang)].provisions if p.unit != "recital"]
    diff = compare_texts(oj, parsed[("eu-gdpr-consolidated", lang)].provisions)
    assert diff["only_first"] == [] and diff["only_second"] == []
    assert 0 < len(diff["changed"]) <= 45  # the 2018 corrigendum


def test_the_consolidated_gdpr_carries_the_corrigendum_in_article_37_1_c(parsed):
    oj = provision(parsed, "eu-gdpr-oj", "en", "eu-gdpr/art-37/1/c").text
    consolidated = provision(parsed, "eu-gdpr-consolidated", "en", "eu-gdpr/art-37/1/c").text
    assert "special categories of data pursuant to Article 9 and personal data" in oj
    assert "special categories of data pursuant to Article 9 or personal data" in consolidated


# --- the consolidated AI Act against the Official Journal text and the Omnibus -----------------------------------


def test_the_consolidated_ai_act_has_the_articles_and_the_annex_the_omnibus_inserted(parsed):
    consolidated = parsed[("eu-ai-act-consolidated-20260727", "en")].provisions
    articles = {p.path[0] for p in consolidated if p.unit == "article"}
    assert {"4a", "60a", "75a", "75b", "75c", "75d"} <= articles
    assert "XIV" in {p.path[0] for p in consolidated if p.unit == "annex"}
    original = {p.path[0] for p in parsed[("eu-ai-act-oj", "en")].provisions if p.unit == "article"}
    assert "4a" not in original


def test_the_consolidated_ai_act_carries_the_new_application_dates(parsed):
    key = "eu-ai-act-consolidated-20260727"
    annex_iii = provision(parsed, key, "en", "eu-ai-act/art-113/c/i")
    annex_i = provision(parsed, key, "en", "eu-ai-act/art-113/c/ii")
    assert annex_iii.text.startswith(
        "2 December 2027 as regards AI systems classified as high-risk pursuant to"
    )
    assert annex_i.text.startswith("2 August 2028 as regards AI systems classified as high-risk pursuant to")
    assert not any("2 December 2027" in p.text for p in parsed[("eu-ai-act-oj", "en")].provisions)


def test_every_ai_act_article_that_changed_is_one_the_omnibus_mentions_apart_from_known_typography(parsed):
    """Changed or inserted articles must be amended by the Omnibus. Articles 103 to 109 amend other acts and quote
    them, and the two renderings differ in how the quoted passages are set (a quote mark, a capital). That is
    typography, not amendments. (Annex VI used to be listed here too; that was a parser gap, now fixed.)"""
    oj = [p for p in parsed[("eu-ai-act-oj", "en")].provisions if p.unit != "recital"]
    consolidated = parsed[("eu-ai-act-consolidated-20260727", "en")].provisions
    diff = compare_texts(oj, consolidated)
    by_id = {p.id: p for p in [*oj, *consolidated]}
    differing = {(by_id[i].unit, by_id[i].path[0]) for k in diff.values() for i in k}
    omnibus = " ".join(p.text for p in parsed[("eu-ai-omnibus-oj", "en")].provisions if p.unit != "recital")

    def mentioned(unit, number):
        word = "Article" if unit == "article" else "Annex"
        return re.search(rf"\b{word}s?\s+{re.escape(number)}\b", omnibus, re.IGNORECASE) is not None

    unexplained = {(u, n) for u, n in differing if not mentioned(u, n)}
    typography = {("article", str(n)) for n in range(103, 110)}
    assert unexplained <= typography


# --- golden provisions: exact text compared with the official text -----------------------------------------------


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


def test_the_consolidated_gdpr_gives_article_6_1_f_the_same_wording_as_the_official_journal(parsed):
    oj = provision(parsed, "eu-gdpr-oj", "en", "eu-gdpr/art-6/1/f")
    consolidated = provision(parsed, "eu-gdpr-consolidated", "en", "eu-gdpr/art-6/1/f")
    assert consolidated.text == oj.text
    assert consolidated.version == "consolidated-20160504"


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
    assert annex.text == (
        "High-risk AI systems pursuant to Article 6(2) are the AI systems listed in any of the following areas:"
    )
    biometrics = provision(parsed, "eu-ai-act-oj", "en", "eu-ai-act/anx-III/1/a")
    assert biometrics.text.startswith("remote biometric identification systems.")


def test_ai_act_official_journal_text_still_says_2_august_2026_the_omnibus_moves_it(parsed):
    original = provision(parsed, "eu-ai-act-oj", "en", "eu-ai-act/art-113")
    assert "It shall apply from 2 August 2026." in original.text
    omnibus = [p for p in parsed[("eu-ai-omnibus-oj", "en")].provisions if "2 December 2027" in p.text]
    assert any(p.unit == "article" for p in omnibus)


def test_ai_act_annex_vi_internal_control_items_are_read_in_both_languages(parsed):
    for lang in ("en", "es"):
        items = [p for p in parsed[("eu-ai-act-oj", lang)].provisions if p.id.startswith("eu-ai-act/anx-VI/")]
        assert [p.path for p in items] == [("VI", "1"), ("VI", "2"), ("VI", "3"), ("VI", "4")]
    second = provision(parsed, "eu-ai-act-oj", "en", "eu-ai-act/anx-VI/2")
    assert second.text == (
        "The provider verifies that the established quality management system is in compliance with the "
        "requirements of Article 17."
    )
