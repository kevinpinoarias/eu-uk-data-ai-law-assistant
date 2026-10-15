"""
Tests for dense (embedding) retrieval: the prompts Google's model expects, the HTTP client (against a fake
transport: no network and no key), retries, vector storage, and brute-force cosine search. The first real call
happens only when the project owner has supplied a key.
"""

from __future__ import annotations

import json
import math

import pytest

from law_assistant.chunk.chunker import Chunk
from law_assistant.retrieval.dense import DenseIndex
from law_assistant.retrieval.gemini import (
    BASE_URL,
    EmbeddingError,
    GeminiEmbedder,
    document_prompt,
    query_prompt,
)
from law_assistant.retrieval.vectors import VectorStore, normalise, truncate


def chunk(id_, text, context="GDPR | Article 17: Erasure"):
    return Chunk(
        id=id_, instrument="eu-gdpr", jurisdiction="EU", language="en", version="oj", unit="article",
        unit_path=("17",), citation="x", heading=None, chapter=None, context=context, text=text,
        provision_ids=(), part=1, parts=1, words=len(text.split()), order=0,
    )  # fmt: skip


# --- prompts ------------------------------------------------------------------------------------------------


def test_a_document_is_sent_as_title_and_text_with_the_context_line_as_the_title():
    c = chunk("a", "The data subject has the right.")
    assert document_prompt(c) == "title: GDPR | Article 17: Erasure | text: The data subject has the right."
    assert document_prompt(c, with_context=False) == "title: none | text: The data subject has the right."
    assert document_prompt(chunk("b", "x", context=""), with_context=True) == "title: none | text: x"


def test_a_query_is_sent_with_the_search_task_prefix():
    assert query_prompt("what is erasure?") == "task: search result | query: what is erasure?"


# --- vectors ------------------------------------------------------------------------------------------------


def test_normalising_gives_unit_length_and_truncating_keeps_the_first_numbers_then_renormalises():
    assert math.isclose(math.sqrt(sum(x * x for x in normalise([3.0, 4.0]))), 1.0)
    assert normalise([3.0, 4.0]) == pytest.approx([0.6, 0.8])
    cut = truncate([3.0, 4.0, 12.0], 2)
    assert cut == pytest.approx([0.6, 0.8])
    assert normalise([0.0, 0.0]) == [0.0, 0.0]


def test_a_vector_store_remembers_vectors_by_key_and_survives_a_round_trip(tmp_path):
    store = VectorStore()
    store.add("k1", [0.5, -1.0, 2.0])
    store.add("k2", [1.0, 0.0, 0.25])
    path = tmp_path / "idx" / "vectors"
    store.save(path)
    loaded = VectorStore.load(path)
    assert "k1" in loaded and "zzz" not in loaded and len(loaded) == 2
    assert loaded.get("k1") == pytest.approx([0.5, -1.0, 2.0])
    assert VectorStore.load(tmp_path / "missing").keys() == []


# --- the HTTP client, against a fake transport ---------------------------------------------------------------


def vec_of(text):
    return [float(len(text)), float(sum(map(ord, text)) % 7), 1.0, 0.0]


class FakeTransport:
    def __init__(self, statuses=(), bodies=None):
        self.calls, self.statuses, self.bodies = [], list(statuses), list(bodies or [])

    def __call__(self, url, headers, body):
        payload = json.loads(body)
        self.calls.append((url, headers, payload))
        if self.statuses:
            status = self.statuses.pop(0)
            if status != 200:
                reply = self.bodies.pop(0) if self.bodies else b'{"error": {"message": "rate limited"}}'
                return status, reply
        if "requests" in payload:
            texts = [r["content"]["parts"][0]["text"] for r in payload["requests"]]
            return 200, json.dumps({"embeddings": [{"values": vec_of(t)} for t in texts]}).encode()
        text = payload["content"]["parts"][0]["text"]
        return 200, json.dumps({"embedding": {"values": vec_of(text)}}).encode()


def embedder(transport, **kw):
    kw.setdefault("sleep", lambda s: None)
    return GeminiEmbedder("SECRET-KEY", transport=transport, **kw)


def test_a_batch_is_posted_to_the_batch_endpoint_with_the_key_in_a_header_and_no_task_type():
    t = FakeTransport()
    out = embedder(t).embed_texts(["alpha", "beta"])
    url, headers, payload = t.calls[0]
    assert url == f"{BASE_URL}/gemini-embedding-2:batchEmbedContents"
    assert headers["x-goog-api-key"] == "SECRET-KEY" and headers["Content-Type"] == "application/json"
    assert payload["requests"][0] == {
        "model": "models/gemini-embedding-2",
        "content": {"parts": [{"text": "alpha"}]},
    }
    assert "taskType" not in json.dumps(payload) and "task_type" not in json.dumps(payload)
    assert out == [vec_of("alpha"), vec_of("beta")]


def test_texts_are_sent_in_batches_and_come_back_in_order():
    t = FakeTransport()
    texts = [f"text number {i}" for i in range(70)]
    out = embedder(t, batch_size=32).embed_texts(texts)
    assert [len(c[2]["requests"]) for c in t.calls] == [32, 32, 6]
    assert out == [vec_of(x) for x in texts]


def test_a_single_embedding_can_ask_for_a_shorter_vector():
    t = FakeTransport()
    assert embedder(t).embed_one("alpha", dimensions=768) == vec_of("alpha")
    url, _, payload = t.calls[0]
    assert url.endswith("gemini-embedding-2:embedContent") and payload["output_dimensionality"] == 768


def test_a_server_error_is_retried_with_growing_pauses():
    t = FakeTransport(statuses=[503, 503, 200])
    pauses = []
    out = embedder(t, sleep=pauses.append, pause=0.0).embed_texts(["alpha"])
    assert out == [vec_of("alpha")] and len(t.calls) == 3
    assert pauses[0] < pauses[1]


def test_a_rate_limit_waits_long_enough_for_a_per_minute_limit_to_reset_and_keeps_growing():
    t = FakeTransport(statuses=[429, 429, 200])
    pauses = []
    embedder(t, sleep=pauses.append, pause=0.0).embed_texts(["alpha"])
    assert pauses[0] >= 15 and pauses[1] > pauses[0]


def test_a_rate_limit_obeys_the_delay_google_reports():
    body = json.dumps(
        {"error": {"code": 429, "details": [{"@type": "x.RetryInfo", "retryDelay": "42s"}]}}
    ).encode()
    t = FakeTransport(statuses=[429, 200], bodies=[body])
    pauses = []
    embedder(t, sleep=pauses.append, pause=0.0).embed_texts(["alpha"])
    assert 42 <= pauses[0] <= 50


def test_an_error_message_keeps_enough_of_the_reply_to_see_which_limit_was_hit():
    long_reply = b'{"error": {"message": "' + b"x" * 900 + b' QUOTA-METRIC"}}'
    with pytest.raises(EmbeddingError, match="QUOTA-METRIC"):
        embedder(FakeTransport(statuses=[400], bodies=[long_reply])).embed_texts(["alpha"])


def test_a_request_that_keeps_failing_gives_up_and_a_bad_request_is_not_retried():
    t = FakeTransport(statuses=[429] * 10)
    with pytest.raises(EmbeddingError, match="429"):
        embedder(t, max_retries=2).embed_texts(["alpha"])
    assert len(t.calls) == 3
    bad = FakeTransport(statuses=[400])
    with pytest.raises(EmbeddingError, match="400"):
        embedder(bad).embed_texts(["alpha"])
    assert len(bad.calls) == 1


def test_the_key_never_appears_in_the_repr_or_in_an_error_message():
    t = FakeTransport(statuses=[400])
    e = embedder(t)
    assert "SECRET-KEY" not in repr(e)
    with pytest.raises(EmbeddingError) as info:
        e.embed_texts(["alpha"])
    assert "SECRET-KEY" not in str(info.value)


def test_a_reply_with_the_wrong_number_of_vectors_is_an_error():
    def short(url, headers, body):
        return 200, json.dumps({"embeddings": [{"values": [1.0]}]}).encode()

    with pytest.raises(EmbeddingError, match="expected 2"):
        embedder(short).embed_texts(["a", "b"])


def test_an_embedder_is_refused_without_a_key():
    with pytest.raises(EmbeddingError, match="GEMINI_API_KEY"):
        GeminiEmbedder.from_env({})


# --- dense search ---------------------------------------------------------------------------------------------


class FakeEmbedder:
    """Maps a prompt to a 3-number vector by its words, and counts how many texts it was asked to embed."""

    name = "fake"

    def __init__(self):
        self.asked = 0

    def embed_texts(self, texts):
        self.asked += len(texts)
        out = []
        for t in texts:
            low = t.lower()
            out.append([1.0 if "erasure" in low else 0.0, 1.0 if "breach" in low else 0.0, 1.0])
        return out


CHUNKS = [
    chunk("erase", "right to erasure of data", context=""),
    chunk("breach", "notify a personal data breach", context=""),
    chunk("other", "something unrelated", context=""),
]


def test_dense_search_ranks_by_cosine_similarity_and_breaks_ties_by_id(tmp_path):
    index = DenseIndex(CHUNKS, FakeEmbedder(), tmp_path / "v")
    assert (
        index.search("erasure", 3) == ["erase", "other", "breach"] or index.search("erasure", 3)[0] == "erase"
    )
    assert index.search("breach", 1) == ["breach"]
    top = index.scored("erasure", 3)
    assert top[0][0] == "erase" and top[0][1] > top[1][1] >= top[2][1]
    tie = DenseIndex(
        [chunk("b", "same", context=""), chunk("a", "same", context="")], FakeEmbedder(), tmp_path / "t"
    )
    assert tie.search("same", 2) == ["a", "b"]


def test_embeddings_are_cached_so_a_second_index_asks_for_nothing(tmp_path):
    first = FakeEmbedder()
    DenseIndex(CHUNKS, first, tmp_path / "v").search("erasure", 2)
    assert first.asked == 3 + 1  # three chunks and one query
    second = FakeEmbedder()
    index = DenseIndex(CHUNKS, second, tmp_path / "v")
    index.search("erasure", 2)
    assert second.asked == 0


def test_a_different_context_setting_is_a_different_prompt_and_is_embedded_again(tmp_path):
    chunks = [chunk("a", "right to erasure", context="GDPR | Article 17")]
    e1, e2 = FakeEmbedder(), FakeEmbedder()
    DenseIndex(chunks, e1, tmp_path / "v", with_context=True)
    DenseIndex(chunks, e2, tmp_path / "v", with_context=False)
    assert e1.asked == 1 and e2.asked == 1


def test_a_shorter_vector_is_made_by_truncating_and_renormalising():
    class Wide:
        name = "wide"

        def embed_texts(self, texts):
            return [[3.0, 4.0, 99.0, 99.0] for _ in texts]

    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        index = DenseIndex([chunk("a", "x", context="")], Wide(), Path(d) / "v", dimensions=2)
        assert index.scored("anything", 1)[0][1] == pytest.approx(1.0)


def test_the_embedding_client_also_fails_at_once_when_the_quota_resets_in_hours():
    from law_assistant.retrieval.gemini import EmbeddingError, GeminiEmbedder

    quota = json.dumps({"error": {"details": [{"retryDelay": "34129s"}]}}).encode()
    sleeps, calls = [], []

    def transport(url, headers, body):
        calls.append(1)
        return 429, quota

    embedder = GeminiEmbedder("k", transport=transport, sleep=sleeps.append)
    with pytest.raises(EmbeddingError, match="quota"):
        embedder.embed_texts(["a"])
    assert sleeps == [] and len(calls) == 1


def test_a_serving_index_keeps_new_question_vectors_in_memory_and_never_rewrites_the_store(tmp_path):
    DenseIndex(CHUNKS, FakeEmbedder(), tmp_path / "v")  # the chunk vectors are saved once
    saved = (tmp_path / "v.f32").read_bytes()
    index = DenseIndex(CHUNKS, FakeEmbedder(), tmp_path / "v", persist_queries=False)
    assert index.search("breach", 1) == ["breach"]
    assert index.search("breach", 1) == ["breach"]  # the second call is answered from memory
    assert (tmp_path / "v.f32").read_bytes() == saved  # nothing was written for the question


def test_by_default_a_new_question_vector_is_saved_so_experiments_can_resume(tmp_path):
    index = DenseIndex(CHUNKS, FakeEmbedder(), tmp_path / "v")
    before = (tmp_path / "v.f32").stat().st_size
    index.search("erasure", 1)
    assert (tmp_path / "v.f32").stat().st_size > before
