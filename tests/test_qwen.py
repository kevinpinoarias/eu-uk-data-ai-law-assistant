"""
Tests for the second embedding model (Qwen3-Embedding-0.6B): its prompts, and that it plugs into the same
batching wrapper as BGE-M3. The model call is injected, so none of this needs PyTorch.
"""

from __future__ import annotations

from law_assistant.chunk.chunker import Chunk
from law_assistant.retrieval.qwen import INSTRUCTION, QwenEmbedder, document_prompt, query_prompt


def chunk(text="Text.", context="GDPR | Article 6"):
    return Chunk(
        id="c", instrument="eu-gdpr", jurisdiction="EU", language="en", version="v", unit="article",
        unit_path=("6",), citation="Article 6", heading=None, chapter=None, context=context, text=text,
        provision_ids=("p",), part=1, parts=1, words=1, order=0,
    )  # fmt: skip


def test_a_passage_is_its_context_line_and_text_with_no_instruction():
    assert document_prompt(chunk()) == "GDPR | Article 6\nText."
    assert document_prompt(chunk(), with_context=False) == "Text."


def test_a_question_gets_the_model_cards_instruction_template():
    prompt = query_prompt("Do I need a DPO?")
    assert prompt == f"Instruct: {INSTRUCTION}\nQuery:Do I need a DPO?"
    assert "data protection" in INSTRUCTION and INSTRUCTION.count("\n") == 0


def test_the_embedder_keeps_the_original_order_through_the_shared_batching_wrapper():
    seen = []

    def encode(batch):
        seen.append(list(batch))
        return [[float(len(t)), 1.0] for t in batch]

    vectors = QwenEmbedder(encode, batch_size=2).embed_texts(["aa", "b", "cccc"])
    assert [v[0] for v in vectors] == [2.0, 1.0, 4.0]
    assert seen[0] == ["cccc", "aa"]  # longest first
    assert QwenEmbedder.name == "qwen3-embedding-0.6b"
