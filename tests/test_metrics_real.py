"""
The metrics against the real chunks and the committed gold set. The central check is that every gold provision of
every retrieval question can be satisfied by at least one real chunk (otherwise a gold error would look like a
retrieval failure), and that an oracle ranking scores perfectly and an empty one scores zero. Skipped without
data/chunks/.
"""

from __future__ import annotations

import pytest

from law_assistant import settings
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.metrics import (
    retrieval_questions,
    score_question,
    summarise,
    unreachable_targets,
)
from law_assistant.evaluation.relevance import matches, targets_of

GOLD = settings.GOLD_DIR / "questions.jsonl"
FILES = sorted(settings.CHUNKS_DIR.glob("*.jsonl"))

pytestmark = pytest.mark.skipif(
    len(FILES) < 14 or not GOLD.exists(), reason="the chunks or the gold set are not available"
)


@pytest.fixture(scope="module")
def chunks():
    return [c for f in FILES if f.name != "manifest.json" for c in read_chunks(f)]


@pytest.fixture(scope="module")
def questions():
    return retrieval_questions(read_gold(GOLD))


def oracle(question, chunks):
    """The ideal ranking: for each gold provision, best grade first, the first chunk that satisfies it."""
    ranking = []
    for target in sorted(targets_of(question), key=lambda t: (-t.grade, t.index)):
        match = next(c for c in chunks if matches(c, target.gold))
        if match not in ranking:
            ranking.append(match)
    return ranking


def test_every_gold_provision_of_every_retrieval_question_is_reachable(questions, chunks):
    assert unreachable_targets(questions, chunks) == []


def test_an_oracle_ranking_scores_perfectly_on_every_question(questions, chunks):
    scores = [score_question(q, oracle(q, chunks)) for q in questions]
    assert all(s.hit[1] == 1.0 and s.reciprocal_rank == 1.0 for s in scores)
    assert all(s.recall[10] == 1.0 and s.ndcg[10] == pytest.approx(1.0) for s in scores)


def test_an_empty_ranking_scores_zero_everywhere(questions):
    summary = summarise([score_question(q, []) for q in questions])
    assert all(value == 0.0 for value in summary.values())


def test_a_version_pinned_gold_provision_is_satisfied_only_by_that_version(chunks):
    gold = read_gold(GOLD)
    q012 = next(q for q in gold if q.id == "q012")  # AI Act Article 4, consolidated text only
    hits = [c for c in chunks if any(matches(c, t.gold) for t in targets_of(q012))]
    assert hits and {c.version for c in hits} == {"consolidated-20260727"}
    assert {c.language for c in hits} == {"en", "es"}


def test_a_gold_provision_without_a_pin_is_satisfied_by_every_copy_of_the_article(chunks):
    gold = read_gold(GOLD)
    q001 = next(q for q in gold if q.id == "q001")  # GDPR Article 17, the same in both versions
    hits = [c for c in chunks if any(matches(c, t.gold) for t in targets_of(q001))]
    assert {(c.version[:3], c.language) for c in hits} >= {
        ("oj", "en"),
        ("oj", "es"),
        ("con", "en"),
        ("con", "es"),
    }


def test_pinpoints_narrow_the_hits_to_the_chunk_that_holds_the_provision(chunks):
    gold = read_gold(GOLD)
    q007 = next(q for q in gold if q.id == "q007")  # Article 28(3) of the GDPR
    target = targets_of(q007)[0]
    unit_chunks = [
        c for c in chunks if (c.instrument, c.unit, c.unit_path) == ("eu-gdpr", "article", ("28",))
    ]
    hits = [c for c in unit_chunks if matches(c, target.gold)]
    assert hits and len(hits) < len(unit_chunks)  # the chunks of Article 28 without paragraph 3 do not count
