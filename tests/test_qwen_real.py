"""
The real Qwen3-Embedding-0.6B, when PyTorch and the downloaded files are present. Skipped otherwise, as in CI.
Checks 1,024 numbers, unit length, that a sentence is closer to its translation than to an unrelated sentence, and
that grouping texts into batches does not change a vector.
"""

from __future__ import annotations

import pytest

from law_assistant import settings

MODEL_DIR = settings.PROJECT_ROOT / "data" / "models" / "qwen3-embedding-0.6b"
torch = pytest.importorskip("torch")
pytestmark = pytest.mark.skipif(
    not (MODEL_DIR / "model.safetensors").exists(), reason="Qwen3-Embedding is not downloaded"
)


@pytest.fixture(scope="module")
def embedder():
    from law_assistant.retrieval.qwen import QwenEmbedder

    return QwenEmbedder.load(MODEL_DIR, device="cuda" if torch.cuda.is_available() else "cpu")


def dot(a, b):
    return sum(x * y for x, y in zip(a, b, strict=True))


def test_vectors_have_1024_numbers_and_unit_length(embedder):
    (v,) = embedder.embed_texts(["The data subject has the right to erasure."])
    assert len(v) == 1024 and dot(v, v) == pytest.approx(1.0, abs=1e-3)


def test_a_sentence_is_closer_to_its_translation_than_to_an_unrelated_sentence(embedder):
    en, es, other = embedder.embed_texts(
        [
            "The data subject has the right to obtain the erasure of personal data.",
            "El interesado tendrá derecho a obtener la supresión de los datos personales.",
            "The weather is sunny and warm at the beach today.",
        ]
    )
    assert dot(en, es) > dot(en, other) + 0.2


def test_batching_does_not_change_a_vector_even_with_left_padding(embedder):
    texts = [
        "short",
        "a much longer sentence about the processing of personal data by a controller",
        "mid length text",
    ]
    together = embedder.embed_texts(texts)
    alone = [embedder.embed_texts([t])[0] for t in texts]
    for a, b in zip(together, alone, strict=True):
        assert dot(a, b) > 0.99
