"""
Two retrievers that exist to calibrate the others: a random one (the floor: what no skill scores) and an
oracle built from the gold (the ceiling: what a perfect retriever scores).
"""

from __future__ import annotations

import random
from collections.abc import Sequence

from law_assistant.chunk.chunker import Chunk
from law_assistant.evaluation.gold import GoldQuestion
from law_assistant.evaluation.relevance import matches, targets_of


class RandomRetriever:
    def __init__(self, chunks: Sequence[Chunk], *, seed: int = 0) -> None:
        self.name = "random"
        self._ids = [c.id for c in chunks]
        self._seed = seed

    def search(self, query: str, k: int) -> list[str]:
        return random.Random(f"{self._seed}:{query}").sample(self._ids, min(k, len(self._ids)))


class OracleRetriever:
    """Looks the question up by its text and returns the chunks that satisfy its gold, primary ones first."""

    def __init__(self, questions: Sequence[GoldQuestion], chunks: Sequence[Chunk]) -> None:
        self.name = "oracle"
        self._questions = {q.text: q for q in questions}
        self._chunks = list(chunks)

    def search(self, query: str, k: int) -> list[str]:
        question = self._questions[query]
        ranking: list[str] = []
        for target in sorted(targets_of(question), key=lambda t: (-t.grade, t.index)):
            match = next((c.id for c in self._chunks if matches(c, target.gold)), None)
            if match is not None and match not in ranking:
                ranking.append(match)
        return ranking[:k]
