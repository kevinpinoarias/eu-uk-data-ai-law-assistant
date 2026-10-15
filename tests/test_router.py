"""
Tests for the router (answer-layer step 2): retrieve, look up in the facts table, or refuse. The examples are
invented for these tests; none is a gold question.
"""

from __future__ import annotations

import json

import pytest

from law_assistant.answer.router import ROUTE_INSTRUCTIONS, LLMRouter, Route, RuleRouter, parse_route
from law_assistant.llm.gemini import LLMError


@pytest.mark.parametrize(
    "text",
    [
        "How much is the maximum fine for the worst GDPR breaches?",
        "En la UE, ¿cuánto tiempo hay para contestar a una solicitud de acceso?",
        "What is the minimum age of consent for children under the GDPR?",
        "¿Cuál es la multa máxima por incumplir el Reglamento de IA?",
        "How many hours does a controller have to notify a breach?",
    ],
)
def test_questions_for_an_exact_figure_go_to_the_table(text):
    assert RuleRouter().route(text).route == "table"


@pytest.mark.parametrize(
    "text",
    [
        "What rights do residents of Texas have under the CCPA?",
        "Qué dice la ley HIPAA sobre datos de salud?",
        "What does the ICO guidance recommend for small businesses?",
        "¿Qué recomienda la guía de la AEPD para las pymes?",
    ],
)
def test_other_laws_and_regulator_guides_are_refused_as_out_of_the_corpus(text):
    route = RuleRouter().route(text)
    assert (route.route, route.reason) == ("refuse", "out_of_corpus")


@pytest.mark.parametrize(
    "text",
    [
        "Is my online shop compliant with the GDPR?",
        "Please write a privacy policy for my website.",
        "Redacta una cláusula de consentimiento para mi tienda.",
        "Should we report the incident we had yesterday?",
        "Ayer perdimos un portátil con datos de clientes. ¿Tenemos que avisar?",
    ],
)
def test_requests_for_advice_on_the_users_own_situation_are_refused(text):
    route = RuleRouter().route(text)
    assert (route.route, route.reason) == ("refuse", "legal_advice")


@pytest.mark.parametrize(
    "text",
    [
        "What does the GDPR say about the right to erasure?",
        "¿Qué distingue a un encargado de un responsable del tratamiento?",
        "How do the EU and the UK differ on children's consent age?",
        "As of the start of 2026, when did the AI Act's high-risk rules apply?",
        "Do I need a data protection officer in my business?",
        "Does the GDPR apply to a US company selling to Europeans?",
    ],
)
def test_ordinary_questions_about_what_the_law_says_are_retrieved(text):
    assert RuleRouter().route(text).route == "retrieve"


def test_a_figure_question_that_compares_places_or_names_a_date_is_retrieved_not_looked_up():
    assert RuleRouter().route("What is the age of consent in the EU and in the UK?").route == "retrieve"
    assert RuleRouter().route("What was the maximum fine on 1 January 2025?").route == "retrieve"


def test_the_route_carries_a_short_reason_text():
    assert "figure" in RuleRouter().route("What is the maximum fine?").why.lower()


def test_parse_route_reads_the_models_json_and_checks_it():
    assert parse_route('{"route": "table"}') == Route("table", None, "model")
    assert parse_route('```json\n{"route": "refuse", "reason": "legal_advice"}\n```').reason == "legal_advice"
    for bad in (
        '{"route": "other"}',
        "not json",
        '{"route": "refuse"}',
        '{"route": "retrieve", "reason": "x"}',
    ):
        with pytest.raises(LLMError):
            parse_route(bad)


class FakeGenerator:
    def __init__(self, text):
        self.text, self.calls = text, []

    def generate(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        return self.text


def test_the_llm_router_sends_the_definitions_and_the_question_and_asks_for_json():
    g = FakeGenerator(json.dumps({"route": "refuse", "reason": "out_of_corpus"}))
    route = LLMRouter(g).route("What does the CCPA say?")
    assert (route.route, route.reason) == ("refuse", "out_of_corpus")
    prompt, kwargs = g.calls[0]
    assert prompt == "What does the CCPA say?"
    assert kwargs["system"] == ROUTE_INSTRUCTIONS and kwargs["json_output"] is True
    assert kwargs["temperature"] == 0.0


def test_the_instructions_define_all_three_routes_and_both_refusal_reasons():
    for word in ("retrieve", "table", "refuse", "out_of_corpus", "legal_advice"):
        assert word in ROUTE_INSTRUCTIONS
