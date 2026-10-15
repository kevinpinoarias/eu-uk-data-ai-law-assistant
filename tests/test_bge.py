"""
Tests for the open embedding model BGE-M3 (BAAI): its prompts, the batching wrapper (against a fake encoder: no
PyTorch needed), and that DenseIndex can use another model's prompt forms. The real model is checked in
test_bge_real.py when PyTorch and the downloaded files are present.
"""

from __future__ import annotations

from law_assistant.chunk.chunker import Chunk
from law_assistant.retrieval.bge import BGEEmbedder, document_prompt, query_prompt
from law_assistant.retrieval.dense import DenseIndex


def chunk(id_, text, context="GDPR | Article 17"):
    return Chunk(
        id=id_, instrument="eu-gdpr", jurisdiction="EU", language="en", version="oj", unit="article",
        unit_path=("17",), citation="x", heading=None, chapter=None, context=context, text=text,
        provision_ids=(), part=1, parts=1, words=len(text.split()), order=0,
    )  # fmt: skip


def test_bge_m3_needs_no_prefix_a_passage_is_its_context_line_and_text_and_a_question_is_itself():
    c = chunk("a", "The data subject has the right.")
    assert document_prompt(c) == "GDPR | Article 17\nThe data subject has the right."
    assert document_prompt(c, with_context=False) == "The data subject has the right."
    assert document_prompt(chunk("b", "x", context="")) == "x"
    assert query_prompt("what is erasure?") == "what is erasure?"


class FakeEncoder:
    """Records the batches it is given and returns a one-number-per-text vector (the text's length)."""

    def __init__(self):
        self.batches = []

    def __call__(self, texts):
        self.batches.append(list(texts))
        return [[float(len(t)), 1.0] for t in texts]


def test_texts_come_back_in_their_original_order_although_batches_are_grouped_by_length():
    enc = FakeEncoder()
    texts = ["aaaa", "a", "aaaaaaaa", "aa", "aaa", "aaaaaa"]
    out = BGEEmbedder(enc, batch_size=2).embed_texts(texts)
    assert [v[0] for v in out] == [4.0, 1.0, 8.0, 2.0, 3.0, 6.0]
    assert all(len(b) <= 2 for b in enc.batches) and len(enc.batches) == 3
    lengths = [[len(t) for t in b] for b in enc.batches]
    assert lengths == sorted(
        lengths, reverse=True
    )  # the longest texts go first, so a memory problem shows early


def test_an_empty_list_asks_for_nothing():
    enc = FakeEncoder()
    assert BGEEmbedder(enc).embed_texts([]) == [] and enc.batches == []


def test_a_wrong_number_of_vectors_from_the_encoder_is_an_error():
    import pytest

    with pytest.raises(RuntimeError, match="expected 2"):
        BGEEmbedder(lambda texts: [[1.0]], batch_size=8).embed_texts(["a", "b"])


# --- DenseIndex with another model's prompt forms ------------------------------------------------------------


class Words:
    name = "words"

    def __init__(self):
        self.asked = []

    def embed_texts(self, texts):
        self.asked += list(texts)
        return [[1.0 if "erasure" in t else 0.0, 1.0] for t in texts]


def test_a_dense_index_uses_the_prompt_forms_it_is_given_and_caches_by_them(tmp_path):
    emb = Words()
    chunks = [chunk("a", "right to erasure", context="GDPR | Article 17"), chunk("b", "other", context="x")]
    index = DenseIndex(
        chunks, emb, tmp_path / "v", document_prompt_fn=document_prompt, query_prompt_fn=query_prompt
    )
    assert index.search("erasure", 1) == ["a"]
    assert "GDPR | Article 17\nright to erasure" in emb.asked and "erasure" in emb.asked
    second = Words()
    DenseIndex(
        chunks, second, tmp_path / "v", document_prompt_fn=document_prompt, query_prompt_fn=query_prompt
    )
    assert second.asked == []
