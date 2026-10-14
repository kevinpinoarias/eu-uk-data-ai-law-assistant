"""The BOE manifest: the LOPDGDD's text, metadata and ELI record, each asked for in the right format."""

from __future__ import annotations

from law_assistant.fetch.boe import BOE_DOCUMENTS

API = "https://www.boe.es/datosabiertos/api/legislacion-consolidada/id/BOE-A-2018-16673"


def test_the_manifest_holds_the_text_the_metadata_and_the_eli_record():
    assert {d.key for d in BOE_DOCUMENTS} == {"es-lopdgdd-texto", "es-lopdgdd-metadatos", "es-lopdgdd-eli"}


def test_every_document_comes_from_the_boe_open_data_api_for_the_lopdgdd():
    urls = {d.key: d.url for d in BOE_DOCUMENTS}
    assert urls == {
        "es-lopdgdd-texto": f"{API}/texto",
        "es-lopdgdd-metadatos": f"{API}/metadatos",
        "es-lopdgdd-eli": f"{API}/metadata-eli",
    }
    assert all(d.source == "boe_es" for d in BOE_DOCUMENTS)


def test_each_document_asks_for_a_format_and_is_saved_with_the_matching_extension():
    by_key = {d.key: d for d in BOE_DOCUMENTS}
    assert (by_key["es-lopdgdd-texto"].accept, by_key["es-lopdgdd-texto"].suffix) == (
        "application/xml",
        ".xml",
    )
    assert (by_key["es-lopdgdd-metadatos"].accept, by_key["es-lopdgdd-metadatos"].suffix) == (
        "application/json",
        ".json",
    )
    assert (by_key["es-lopdgdd-eli"].accept, by_key["es-lopdgdd-eli"].suffix) == ("application/xml", ".xml")


def test_every_document_carries_the_boe_credit_lines_and_the_informative_notice():
    for d in BOE_DOCUMENTS:
        assert "Fuente de los datos: Agencia Estatal Boletín Oficial del Estado" in d.credit
        assert "Basado en datos de la Agencia Estatal Boletín Oficial del Estado" in d.credit
        assert "meramente informativo" in d.credit
