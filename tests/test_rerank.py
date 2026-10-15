"""
Tests for the reranker (R5): a second-pass scorer that re-orders the first search's top candidates.
The model call is injected, so none of this needs PyTorch.
"""

from __future__ import annotations

import pytest

from law_assistant.chunk.chunker import Chunk
from law_assistant.retrieval.rerank import RerankedRetriever, Reranker


def chunk(cid: str, text: str, context: str = "") -> Chunk:
    return Chunk(
        id=cid, instrument="x", jurisdiction="eu", language="en", version="v", unit="article",
        unit_path=(cid,), citation=f"Article {cid}", heading=None, chapter=None, context=context,
        text=text, provision_ids=(cid,), part=1, parts=1, words=len(text.split()), order=0,
    )  # fmt: skip


class Fixed:
    def __init__(self, ranking, name="first"):
        self.ranking, self.name, self.asked = list(ranking), name, []

    def search(self, query, k):
        self.asked.append(k)
        return self.ranking[:k]


def score_by_length(pairs):
    """A fake model: a longer passage scores higher."""
    return [float(len(passage)) for _, passage in pairs]


def test_scores_come_back_in_the_order_the_pairs_were_given_even_though_batches_are_length_sorted():
    seen = []

    def score(pairs):
        seen.append([p for _, p in pairs])
        return [float(len(p)) for _, p in pairs]

    reranker = Reranker(score, batch_size=2)
    passages = ["aa", "a", "aaaa", "aaa", "aaaaa"]
    assert reranker.score_pairs("q", passages) == [2.0, 1.0, 4.0, 3.0, 5.0]
    assert seen[0] == ["aaaaa", "aaaa"]  # longest first, so a memory problem shows at once


def test_a_model_that_returns_the_wrong_number_of_scores_is_an_error():
    with pytest.raises(RuntimeError, match="expected 2 scores, got 1"):
        Reranker(lambda pairs: [0.0], batch_size=8).score_pairs("q", ["a", "b"])


def test_no_passages_give_no_scores_and_no_model_call():
    called = []
    assert Reranker(lambda pairs: called.append(1) or [], batch_size=8).score_pairs("q", []) == []
    assert called == []


def test_the_retriever_reorders_the_first_searchs_top_candidates_by_the_reranker_score():
    chunks = [chunk("a", "x"), chunk("b", "xxx"), chunk("c", "xx")]
    first = Fixed(["a", "b", "c"])
    retriever = RerankedRetriever(first, Reranker(score_by_length), chunks, depth=3)
    assert retriever.search("q", 3) == ["b", "c", "a"]
    assert first.asked == [3]


def test_only_the_top_depth_are_reranked_and_the_rest_keep_the_first_searchs_order_behind_them():
    chunks = [chunk(c, "x" * n) for c, n in zip("abcd", (1, 2, 3, 99), strict=True)]
    retriever = RerankedRetriever(Fixed(list("abcd")), Reranker(score_by_length), chunks, depth=3)
    assert retriever.search("q", 4) == ["c", "b", "a", "d"]  # d scores highest but was below the depth


def test_equal_scores_keep_the_first_searchs_order():
    chunks = [chunk("a", "xx"), chunk("b", "xx"), chunk("c", "xx")]
    retriever = RerankedRetriever(Fixed(["c", "a", "b"]), Reranker(score_by_length), chunks, depth=3)
    assert retriever.search("q", 3) == ["c", "a", "b"]


def test_the_reranker_reads_the_context_line_and_the_text_together():
    seen = []

    def score(pairs):
        seen.extend(pairs)
        return [0.0] * len(pairs)

    chunks = [chunk("a", "the text", context="GDPR | Article 6")]
    RerankedRetriever(Fixed(["a"]), Reranker(score), chunks, depth=5).search("my question", 1)
    assert seen == [("my question", "GDPR | Article 6\nthe text")]


def test_the_same_question_and_chunk_are_scored_once_across_depths_and_calls():
    calls = []

    def score(pairs):
        calls.extend(pairs)
        return [float(len(p)) for _, p in pairs]

    chunks = [chunk("a", "x"), chunk("b", "xx")]
    retriever = RerankedRetriever(Fixed(["a", "b"]), Reranker(score), chunks, depth=2)
    retriever.search("q", 2)
    retriever.search("q", 1)
    assert len(calls) == 2


def test_the_name_says_the_first_stage_and_the_depth():
    retriever = RerankedRetriever(Fixed([], "bge-m3"), Reranker(score_by_length), [], depth=30)
    assert retriever.name == "rerank30(bge-m3)"
