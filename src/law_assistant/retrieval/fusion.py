"""
Reciprocal rank fusion (R2): merge several ranked lists into one using only each result's place.

Every list gives each result `weight / (k + place)` points (place 1 is the top, k = 60 is the usual constant)
and a result's points are added over the lists it appears in. Scores from different searches are on different
scales (BM25 runs from about 18 to 36 here, cosine similarity from 0 to 1), so they cannot be added; places
can. A result near the top of several lists beats one that is first in a single list. Ties are broken by id
for reproducibility.
"""

from __future__ import annotations

from collections.abc import Sequence

from law_assistant.retrieval.base import Retriever


def rrf(
    rankings: Sequence[Sequence[str]], *, k: int = 60, weights: Sequence[float] | None = None
) -> list[tuple[str, float]]:
    if weights is not None and len(weights) != len(rankings):
        raise ValueError("weights must have one number per ranking")
    scores: dict[str, float] = {}
    for position, ranking in enumerate(rankings):
        weight = 1.0 if weights is None else weights[position]
        for place, item in enumerate(ranking, start=1):
            scores[item] = scores.get(item, 0.0) + weight / (k + place)
    return sorted(scores.items(), key=lambda pair: (-pair[1], pair[0]))


class FusedRetriever:
    """Ask each retriever for its top `depth` results, fuse them, and return the top k."""

    def __init__(
        self,
        retrievers: Sequence[Retriever],
        *,
        depth: int = 50,
        k_constant: int = 60,
        weights: Sequence[float] | None = None,
        name: str | None = None,
    ) -> None:
        self.name = name or "rrf(" + "+".join(r.name for r in retrievers) + ")"
        self._retrievers, self._depth, self._k, self._weights = list(retrievers), depth, k_constant, weights

    def search(self, query: str, k: int) -> list[str]:
        rankings = [r.search(query, max(self._depth, k)) for r in self._retrievers]
        return [item for item, _ in rrf(rankings, k=self._k, weights=self._weights)[:k]]
