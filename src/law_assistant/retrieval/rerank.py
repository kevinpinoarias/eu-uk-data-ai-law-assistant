"""
R5: a reranker (a cross-encoder) as a second pass over the first search's top candidates.

A first search (BM25, an embedding model) turns the question and every chunk into separate summaries and
compares them, which is fast but coarse. A cross-encoder reads the question and one chunk *together* and gives
that pair a single relevance score, which is slower (one model call per candidate) and sharper. So it is used
only on the first search's top `depth` candidates, and it can only re-order what the first search already
retrieved: a right chunk ranked below `depth` stays out of reach.

`Reranker` is a thin wrapper that groups pairs of similar length into batches (less padding, and the longest
batch first so a memory problem shows at once) and returns the scores in the original order. The actual model
call is an injectable function so the wrapper can be tested without PyTorch; `load` builds the real one
(PyTorch and transformers are imported only there, because they are an optional extra of the project).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from law_assistant.chunk.chunker import Chunk
from law_assistant.retrieval.base import Retriever
from law_assistant.retrieval.bge import document_prompt

MODEL_NAME = "bge-reranker-v2-m3"
ScorePairs = Callable[[list[tuple[str, str]]], list[float]]


class Reranker:
    name = MODEL_NAME

    def __init__(self, score_pairs: ScorePairs, *, batch_size: int = 16) -> None:
        self._score, self.batch_size = score_pairs, batch_size

    def score_pairs(self, query: str, passages: Sequence[str]) -> list[float]:
        order = sorted(range(len(passages)), key=lambda i: -len(passages[i]))
        scores: dict[int, float] = {}
        for start in range(0, len(order), self.batch_size):
            indices = order[start : start + self.batch_size]
            out = self._score([(query, passages[i]) for i in indices])
            if len(out) != len(indices):
                raise RuntimeError(f"expected {len(indices)} scores, got {len(out)}")
            scores.update(zip(indices, out, strict=True))
        return [scores[i] for i in range(len(passages))]

    @classmethod
    def load(
        cls, model_dir: Path, *, device: str = "cuda", max_length: int = 512, batch_size: int = 16
    ) -> Reranker:
        """Load the downloaded model: a sequence classifier with one output, whose raw score (a logit, higher
        is more relevant) is used as it is. Half precision on a graphics card. A pair longer than
        `max_length` tokens is cut (the longer of the two is shortened first)."""
        import torch
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        dtype = torch.float16 if device == "cuda" else torch.float32
        model = AutoModelForSequenceClassification.from_pretrained(str(model_dir), torch_dtype=dtype)
        model = model.to(device).eval()

        def score_pairs(pairs: list[tuple[str, str]]) -> list[float]:
            batch = tokenizer(
                [q for q, _ in pairs], [p for _, p in pairs],
                padding=True, truncation=True, max_length=max_length, return_tensors="pt",
            ).to(device)  # fmt: skip
            with torch.no_grad():
                logits = model(**batch).logits.view(-1).float()
            return logits.cpu().tolist()

        return cls(score_pairs, batch_size=batch_size)


class RerankedRetriever:
    """The first search's top `depth`, re-ordered by the reranker; anything below `depth` follows in the first
    search's order. Equal scores keep the first search's order. A (question, chunk) pair is scored once."""

    def __init__(
        self,
        first_stage: Retriever,
        reranker: Reranker,
        chunks: Sequence[Chunk],
        *,
        depth: int = 30,
        text_fn: Callable[[Chunk], str] = document_prompt,
        name: str | None = None,
    ) -> None:
        self.name = name or f"rerank{depth}({first_stage.name})"
        self._first, self._reranker, self._depth, self._text_fn = first_stage, reranker, depth, text_fn
        self._by_id = {c.id: c for c in chunks}
        self._cache: dict[tuple[str, str], float] = {}

    def search(self, query: str, k: int) -> list[str]:
        candidates = self._first.search(query, max(self._depth, k))
        head, tail = candidates[: self._depth], candidates[self._depth :]
        missing = [cid for cid in head if (query, cid) not in self._cache]
        if missing:
            texts = [self._text_fn(self._by_id[cid]) for cid in missing]
            for cid, score in zip(missing, self._reranker.score_pairs(query, texts), strict=True):
                self._cache[(query, cid)] = score
        reranked = sorted(head, key=lambda cid: -self._cache[(query, cid)])  # stable: ties keep their order
        return (reranked + tail)[:k]
