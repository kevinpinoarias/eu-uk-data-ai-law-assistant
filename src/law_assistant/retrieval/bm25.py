"""
BM25: keyword search that scores each chunk by the words it shares with the question.

For each distinct word of the question that a chunk contains:

    score += idf(word) * tf * (k1 + 1) / (tf + k1 * (1 - b + b * length / average_length))

- tf is how many times the word occurs in the chunk, and length is the chunk's number of words;
- idf(word) = ln(1 + (N - n + 0.5) / (n + 0.5)) is large for a word found in few chunks (n of N) and
  small for one found nearly everywhere, and never negative;
- k1 (1.2) makes repeats count for less and less; b (0.75) discounts long chunks.

The chunk's score is the sum over the question's words, each counted once. Chunks with no word in common are
not returned. Ties are broken by chunk id so a run is reproducible. Pure Python, no dependencies.
"""

from __future__ import annotations

import math
from collections import Counter
from collections.abc import Callable, Sequence

from law_assistant.chunk.chunker import Chunk
from law_assistant.retrieval.tokenize import tokenize


def embed_text(chunk: Chunk) -> str:
    return chunk.embed_text


class BM25Index:
    def __init__(
        self,
        chunks: Sequence[Chunk],
        *,
        k1: float = 1.2,
        b: float = 0.75,
        fold_accents: bool = False,
        text_of: Callable[[Chunk], str] = embed_text,
        name: str = "bm25",
    ) -> None:
        self.name = name
        self.k1, self.b, self.fold_accents = k1, b, fold_accents
        self._ids = [c.id for c in chunks]
        self._lengths: list[int] = []
        self._postings: dict[str, list[tuple[int, int]]] = {}
        for position, chunk in enumerate(chunks):
            words = tokenize(text_of(chunk), fold_accents=fold_accents)
            self._lengths.append(len(words))
            for word, count in Counter(words).items():
                self._postings.setdefault(word, []).append((position, count))
        n = len(chunks)
        self._average = sum(self._lengths) / n if n else 0.0
        self._idf = {
            word: math.log(1 + (n - len(postings) + 0.5) / (len(postings) + 0.5))
            for word, postings in self._postings.items()
        }

    def scored(self, query: str, k: int) -> list[tuple[str, float]]:
        """The best k (chunk id, score) pairs, best first; chunks sharing no query word are left out."""
        scores: dict[int, float] = {}
        for word in set(tokenize(query, fold_accents=self.fold_accents)):
            for position, count in self._postings.get(word, ()):
                norm = 1 - self.b + self.b * self._lengths[position] / self._average
                gain = self._idf[word] * count * (self.k1 + 1) / (count + self.k1 * norm)
                scores[position] = scores.get(position, 0.0) + gain
        ranked = sorted(scores.items(), key=lambda item: (-item[1], self._ids[item[0]]))
        return [(self._ids[position], score) for position, score in ranked[:k]]

    def search(self, query: str, k: int) -> list[str]:
        return [chunk_id for chunk_id, _ in self.scored(query, k)]
