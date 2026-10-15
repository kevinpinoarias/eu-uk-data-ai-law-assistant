"""
Tests for step 1 of the answer layer: reading a question's language, the jurisdictions it names and the date
it asks about, with plain rules (no model).
"""

from __future__ import annotations

import pytest

from law_assistant.answer.understand import (
    detect_as_of,
    detect_jurisdictions,
    detect_language,
    understand,
    wants_original_text,
)


@pytest.mark.parametrize(
    ("text", "language"),
    [
        ("Do I need to name a person responsible for data protection in my business in the EU?", "en"),
        ("En la UE, ¿puedo llevarme mis datos de un servicio a otro cuando cambio de proveedor?", "es"),
        ("consentimiento «libre» RGPD qué significa", "es"),
        ("consentimiento libre RGPD que significa", "es"),
        ("GDPR fines maximum", "en"),
        ("¿Quién vigila que se cumpla el Reglamento de IA?", "es"),
        ("What is a data protection impact assessment", "en"),
        ("derecho de acceso copia datos plazo", "es"),
    ],
)
def test_the_language_is_found_from_accents_and_common_words(text, language):
    assert detect_language(text) == language


def test_an_empty_or_unreadable_question_defaults_to_english():
    assert detect_language("") == "en" and detect_language("1234") == "en"


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Under the GDPR, what does a data breach mean?", ("EU",)),
        ("Does UK data protection law treat research differently from the EU's GDPR?", ("EU", "UK")),
        ("En el Reino Unido, ¿puedo presentar mi queja primero a la empresa?", ("UK",)),
        ("En España, ¿puedo pedir a un buscador que quite noticias antiguas?", ("ES",)),
        ("¿Qué recomienda la guía de la AEPD sobre análisis de riesgos?", ("ES",)),
        ("What is the highest fine under EU data protection law?", ("EU",)),
        ("What does the AI Act require from a business that deploys AI?", ("EU",)),
        ("Is there a list I can join in Spain to stop advertising?", ("ES",)),
        ("What rights do California residents have?", ()),
    ],
)
def test_jurisdictions_are_found_from_the_names_of_places_laws_and_regulators(text, expected):
    assert detect_jurisdictions(text) == expected


def test_uk_gdpr_names_the_uk_and_not_the_eu():
    assert detect_jurisdictions("What does the UK GDPR say about consent?") == ("UK",)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        (
            "As of the start of 2026, when were the AI Act's rules for high-risk systems due to apply?",
            "2026-01-01",
        ),
        ("What did the GDPR say on 2 February 2025?", "2025-02-02"),
        ("¿Qué decía el artículo el 1 de enero de 2024?", "2024-01-01"),
        ("Rules as of 2025-08-02 for GPAI models", "2025-08-02"),
        ("Since when can UK organisations rely on recognised legitimate interest?", None),
        ("What is the biggest fine?", None),
    ],
)
def test_a_requested_date_is_read_in_the_usual_written_forms(text, expected):
    assert detect_as_of(text) == expected


def test_understand_bundles_the_three_readings():
    u = understand("En España, ¿puedo pedir que borren mis fotos?")
    assert (u.language, u.jurisdictions, u.as_of) == ("es", ("ES",), None)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("In the GDPR as first published in the Official Journal, how was Article 37 worded?", True),
        ("How was the original text of the AI Act worded on this point?", True),
        ("¿Cómo se redactó en el texto original publicado en el Diario Oficial?", True),
        ("¿Cómo estaba redactado inicialmente el artículo?", True),
        ("What does the GDPR say about erasure?", False),
        ("¿Qué dice el RGPD sobre el derecho de acceso?", False),
    ],
)
def test_a_question_about_the_wording_as_first_published_is_recognised(text, expected):
    assert wants_original_text(text) is expected
