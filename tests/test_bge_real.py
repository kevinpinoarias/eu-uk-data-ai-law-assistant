"""
The real BGE-M3 model, when PyTorch and the downloaded files are present (data/models/bge-m3). Skipped otherwise,
as in CI. Checks the properties the experiments rely on: 1,024 numbers, unit length, and that a sentence is
closer to its own translation than to an unrelated sentence.
"""

from __future__ import annotations

import pytest

from law_assistant import settings

MODEL_DIR = settings.PROJECT_ROOT / "data" / "models" / "bge-m3"
torch = pytest.importorskip("torch")
pytestmark = pytest.mark.skipif(
    not (MODEL_DIR / "pytorch_model.bin").exists(), reason="BGE-M3 is not downloaded"
)


@pytest.fixture(scope="module")
def embedder():
    from law_assistant.retrieval.bge import BGEEmbedder

    return BGEEmbedder.load(MODEL_DIR, device="cuda" if torch.cuda.is_available() else "cpu")


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


def test_order_is_kept_when_batches_are_regrouped_by_length(embedder):
    texts = [
        "short",
        "a much longer sentence about the processing of personal data by a controller",
        "mid length text",
    ]
    together = embedder.embed_texts(texts)
    alone = [embedder.embed_texts([t])[0] for t in texts]
    for a, b in zip(together, alone, strict=True):
        assert dot(a, b) > 0.99
