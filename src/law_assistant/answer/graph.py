"""
The answer pipeline as a LangGraph graph.

LangGraph is an optional dependency (`pip install -e ".[agent]"`): it adds nothing to what the pipeline
decides, it draws the same steps and the same conditional edges as a graph, so the flow can be inspected,
visualised and run with LangGraph's tooling. The steps and the edge rule come from `AnswerPipeline` itself
(`nodes()` and `next_step()`), so the plain loop in `AnswerPipeline.ask` and this graph cannot drift apart;
a test runs both on the same questions and compares the results.
"""

from __future__ import annotations

from typing import Any, TypedDict

from law_assistant.answer.pipeline import AnswerPipeline, Result


class State(TypedDict, total=False):
    """Every key a step may add. LangGraph merges each step's returned keys into this shared state."""

    question: str
    language: str
    jurisdictions: tuple[str, ...]
    as_of: str | None
    wants_original: bool
    route: str
    reason: str | None
    fact: Any
    fell_back: bool
    query: str
    passages: list
    draft: Any
    verification: Any
    result: Result


def build_graph(pipeline: AnswerPipeline):
    """Compile the pipeline into a LangGraph graph (imports langgraph here, not at module load)."""
    from langgraph.graph import END, START, StateGraph

    builder = StateGraph(State)
    names = list(pipeline.nodes())
    for name, step in pipeline.nodes().items():
        builder.add_node(name, step)
    builder.add_edge(START, "understand")
    for name in names:
        targets = {t: t for t in names} | {"__end__": END}
        builder.add_conditional_edges(
            name,
            lambda state, current=name: pipeline.next_step(current, state) or "__end__",
            targets,
        )
    return builder.compile()


def ask_with_graph(pipeline: AnswerPipeline, question: str) -> Result:
    """Run one question through the compiled graph and return the same Result the plain loop returns."""
    final: dict[str, Any] = build_graph(pipeline).invoke({"question": question})
    return final["result"]
