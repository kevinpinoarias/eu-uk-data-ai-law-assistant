"""
Embedding search over the chunks: embed every chunk once (cached on disk, resumable), embed the question, and
rank the chunks by cosine similarity. Brute force: the question's vector is compared with every chunk's
vector, which at 3,831 chunks takes a fraction of a second even in plain Python.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable, Sequence
from operator import mul
from pathlib import Path
from typing import Protocol

from law_assistant.chunk.chunker import Chunk
from law_assistant.retrieval.gemini import document_prompt, query_prompt
from law_assistant.retrieval.vectors import VectorStore, normalise, truncate

SAVE_EVERY = 320  # texts embedded between saves, so an interrupted run loses little


class TextEmbedder(Protocol):
    name: str

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]: ...


def cache_key(model: str, prompt: str) -> str:
    return hashlib.sha256(f"{model}\n{prompt}".encode()).hexdigest()[:32]


class DenseIndex:
    def __init__(
        self,
        chunks: Sequence[Chunk],
        embedder: TextEmbedder,
        store_path: Path,
        *,
        with_context: bool = True,
        dimensions: int | None = None,
        name: str | None = None,
        document_prompt_fn: Callable[..., str] = document_prompt,
        query_prompt_fn: Callable[[str], str] = query_prompt,
        persist_queries: bool = True,
    ) -> None:
        self.name = name or f"{embedder.name}-{dimensions or 'full'}"
        self._embedder, self._store_path, self._dimensions = embedder, store_path, dimensions
        self._query_prompt = query_prompt_fn
        self._persist_queries = persist_queries  # False for a server: question vectors stay in memory
        self._store = VectorStore.load(store_path)
        self._ids = [c.id for c in chunks]
        prompts = [document_prompt_fn(c, with_context=with_context) for c in chunks]
        keys = [cache_key(embedder.name, p) for p in prompts]
        missing = [(k, p) for k, p in zip(keys, prompts, strict=True) if k not in self._store]
        for start in range(0, len(missing), SAVE_EVERY):
            part = missing[start : start + SAVE_EVERY]
            for (key, _), vector in zip(part, embedder.embed_texts([p for _, p in part]), strict=True):
                self._store.add(key, vector)
            self._store.save(store_path)
        self._vectors = [self._unit(self._store.get(k)) for k in keys]

    def _unit(self, vector: list[float]) -> list[float]:
        return truncate(vector, self._dimensions) if self._dimensions else normalise(vector)

    def _query_vector(self, query: str) -> list[float]:
        prompt = self._query_prompt(query)
        key = cache_key(self._embedder.name, prompt)
        if key not in self._store:
            self._store.add(key, self._embedder.embed_texts([prompt])[0])
            if self._persist_queries:
                self._store.save(self._store_path)
        return self._unit(self._store.get(key))

    def scored(self, query: str, k: int) -> list[tuple[str, float]]:
        q = self._query_vector(query)
        scores = [
            (chunk_id, sum(map(mul, q, v))) for chunk_id, v in zip(self._ids, self._vectors, strict=True)
        ]
        scores.sort(key=lambda item: (-item[1], item[0]))
        return scores[:k]

    def search(self, query: str, k: int) -> list[str]:
        return [chunk_id for chunk_id, _ in self.scored(query, k)]
