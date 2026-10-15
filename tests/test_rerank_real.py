"""
The real reranker, when PyTorch and the downloaded files are present (data/models/bge-reranker-v2-m3). Skipped
otherwise, as in CI. Checks the properties the experiments rely on: one score per pair, a passage that answers
the question scores above one that does not (in English, in Spanish and across the two), and the scores do not
depend on how the pairs are grouped into batches.
"""

from __future__ import annotations

import pytest

from law_assistant import settings

MODEL_DIR = settings.PROJECT_ROOT / "data" / "models" / "bge-reranker-v2-m3"
torch = pytest.importorskip("torch")
pytestmark = pytest.mark.skipif(
    not (MODEL_DIR / "model.safetensors").exists(), reason="the reranker is not downloaded"
)

ANSWER_EN = "The controller shall designate a data protection officer where the processing is carried out by a public authority."
ANSWER_ES = "El responsable designará un delegado de protección de datos cuando el tratamiento lo lleve a cabo una autoridad pública."
OTHER = "The weather is sunny and warm at the beach today."


@pytest.fixture(scope="module")
def reranker():
    from law_assistant.retrieval.rerank import Reranker

    return Reranker.load(MODEL_DIR, device="cuda" if torch.cuda.is_available() else "cpu")


def test_a_passage_that_answers_the_question_scores_above_one_that_does_not(reranker):
    good, bad = reranker.score_pairs("Does a public body need a data protection officer?", [ANSWER_EN, OTHER])
    assert good > bad + 2


def test_it_works_across_languages(reranker):
    good, bad = reranker.score_pairs(
        "¿Debe una autoridad pública nombrar un delegado de protección de datos?", [ANSWER_EN, OTHER]
    )
    assert good > bad + 2
    good, bad = reranker.score_pairs("Does a public body need a data protection officer?", [ANSWER_ES, OTHER])
    assert good > bad + 2


def test_scores_do_not_depend_on_how_the_pairs_are_batched(reranker):
    question, passages = "Does a public body need a data protection officer?", [ANSWER_EN, OTHER, "short"]
    together = reranker.score_pairs(question, passages)
    alone = [reranker.score_pairs(question, [p])[0] for p in passages]
    for a, b in zip(together, alone, strict=True):
        assert a == pytest.approx(b, abs=0.1)
