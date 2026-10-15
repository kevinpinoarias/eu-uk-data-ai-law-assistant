"""Run a retriever over the gold questions, score the run, and break the scores down by group."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Callable, Mapping, Sequence

from law_assistant.chunk.chunker import Chunk
from law_assistant.evaluation.gold import GoldQuestion
from law_assistant.evaluation.metrics import KS, QuestionScore, metric_values, retrieval_questions, score_run
from law_assistant.retrieval.base import Retriever


def select(questions: Sequence[GoldQuestion], split: str | None = None) -> list[GoldQuestion]:
    """The retrieval questions, optionally of one split ("dev" or "test")."""
    return [q for q in retrieval_questions(questions) if split is None or q.split == split]


def run_retriever(
    retriever: Retriever, questions: Sequence[GoldQuestion], *, k: int = 10
) -> dict[str, list[str]]:
    return {q.id: retriever.search(q.text, k) for q in questions}


def evaluate(
    questions: Sequence[GoldQuestion],
    run: Mapping[str, Sequence[str]],
    chunks: Sequence[Chunk],
    ks: Sequence[int] = KS,
) -> list[QuestionScore]:
    return score_run(questions, run, {c.id: c for c in chunks}, ks)


def breakdown(
    questions: Sequence[GoldQuestion],
    scores: Sequence[QuestionScore],
    key: Callable[[GoldQuestion], str],
    metric: str,
) -> dict[str, tuple[float, int]]:
    """For each group of questions, the mean of a metric and the number of questions in the group."""
    values = dict(zip((q.id for q in questions), metric_values(scores, metric), strict=True))
    groups: dict[str, list[float]] = defaultdict(list)
    for q in questions:
        groups[key(q)].append(values[q.id])
    return {name: (sum(v) / len(v), len(v)) for name, v in groups.items()}
