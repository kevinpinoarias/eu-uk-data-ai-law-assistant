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
