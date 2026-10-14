"""The EU manifest: five Tier 1 acts in English and Spanish, fetched through Cellar by CELEX number."""

from __future__ import annotations

from law_assistant.fetch.eu import EU_DOCUMENTS

CELEX = {
    "gdpr-oj": "32016R0679",
    "gdpr-consolidated": "02016R0679-20160504",
    "ai-act-oj": "32024R1689",
    "ai-act-consolidated-20260727": "02024R1689-20260727",
    "ai-omnibus-oj": "32026R1744",
}


def test_the_manifest_holds_five_acts_in_two_languages():
    keys = {d.key for d in EU_DOCUMENTS}
    assert keys == {f"eu-{act}-{lang}" for act in CELEX for lang in ("en", "es")}
    assert len(EU_DOCUMENTS) == 10


def test_each_url_is_the_cellar_resource_for_its_celex_number():
    for d in EU_DOCUMENTS:
        act = d.key.removeprefix("eu-").rsplit("-", 1)[0]
        assert d.url == f"https://publications.europa.eu/resource/celex/{CELEX[act]}"


def test_each_document_asks_for_xhtml_in_the_right_language_and_is_saved_as_xhtml():
    for d in EU_DOCUMENTS:
        assert d.accept == "application/xhtml+xml"
        assert d.suffix == ".xhtml"
        assert d.source == "eur_lex_cellar"
        assert d.accept_language == ("eng" if d.key.endswith("-en") else "spa")


def test_every_document_carries_the_eur_lex_credit_and_authenticity_notice():
    for d in EU_DOCUMENTS:
        assert "EUR-Lex" in d.credit and "© European Union" in d.credit
        assert "Official Journal" in d.credit


def test_consolidated_texts_are_marked_as_having_no_legal_effect_and_cc_by():
    for d in EU_DOCUMENTS:
        if "consolidated" in d.key:
            assert "no legal effect" in d.credit
            assert "CC BY 4.0" in d.licence
