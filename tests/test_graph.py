"""
The LangGraph wiring must give the same results as the plain loop. Skipped when LangGraph is not installed
(it is an optional extra), as in CI.
"""

from __future__ import annotations

import pytest

pytest.importorskip("langgraph")

from law_assistant.answer.graph import ask_with_graph, build_graph  # noqa: E402
from law_assistant.answer.router import Route  # noqa: E402
from test_pipeline import pipeline  # noqa: E402


@pytest.mark.parametrize(
    ("route", "question"),
    [
        (Route("retrieve"), "Do I need consent?"),
        (Route("table"), "What is the age of consent in the EU?"),
        (Route("refuse", "legal_advice"), "Is my shop compliant?"),
    ],
)
def test_the_graph_and_the_plain_loop_give_the_same_result(route, question):
    p, _ = pipeline(route=route)
    plain = p.ask(question)
    graphed = ask_with_graph(p, question)
    assert (graphed.kind, graphed.text, graphed.route) == (plain.kind, plain.text, plain.route)


def test_the_graph_has_a_node_for_every_step():
    p, _ = pipeline()
    nodes = set(build_graph(p).get_graph().nodes)
    assert set(p.nodes()) <= nodes


def test_the_graph_handles_a_request_for_advice_in_general_mode_like_the_plain_loop():
    p, _ = pipeline(route=Route("refuse", "legal_advice"), advice_mode="general")
    plain = p.ask("Can I use customer data to train a model?")
    graphed = ask_with_graph(p, "Can I use customer data to train a model?")
    assert plain.kind == "answer" and plain.notice
    assert (graphed.kind, graphed.text, graphed.notice) == (plain.kind, plain.text, plain.notice)
