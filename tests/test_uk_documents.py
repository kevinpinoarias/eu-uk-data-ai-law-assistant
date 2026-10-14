"""The UK manifest: three documents, official URLs, the licence and credit line SOURCES.md requires."""

from __future__ import annotations

from law_assistant.fetch.uk import UK_DOCUMENTS

CREDIT = "Contains public sector information licensed under the Open Government Licence v3.0."


def test_the_manifest_holds_the_three_tier_1_uk_documents():
    assert {d.key for d in UK_DOCUMENTS} == {"uk-gdpr", "uk-dpa-2018", "uk-duaa-2025"}


def test_every_document_comes_from_legislation_gov_uk_as_xml():
    for d in UK_DOCUMENTS:
        assert d.url.startswith("https://www.legislation.gov.uk/")
        assert d.url.endswith("/data.xml")
        assert d.source == "legislation_gov_uk"
        assert d.suffix == ".xml"


def test_every_document_carries_the_required_licence_and_credit():
    for d in UK_DOCUMENTS:
        assert d.licence == "Open Government Licence v3.0"
        assert d.credit == CREDIT


def test_the_urls_match_the_manifest_in_sources_md():
    urls = {d.key: d.url for d in UK_DOCUMENTS}
    assert urls["uk-gdpr"].endswith("/eur/2016/679/data.xml")
    assert urls["uk-dpa-2018"].endswith("/ukpga/2018/12/data.xml")
    assert urls["uk-duaa-2025"].endswith("/ukpga/2025/18/data.xml")
