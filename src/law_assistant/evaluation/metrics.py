"""
Retrieval metrics for a ranked list of chunks against a question's gold provisions, and bootstrap intervals.

- hit@k: a primary gold provision is among the first k chunks;
- recall@k: the share of primary gold provisions found in the first k;
- MRR: one over the rank of the first chunk that matches a primary provision;
- nDCG@k: graded (primary 3, acceptable 1), each gold provision credited once, by its best chunk, so extra
  copies of the same article (other language, other version, other piece) neither help nor hurt; at most one
  gold provision is credited per chunk, so the ideal ranking, one chunk per provision, scores 1.

Only questions routed to retrieval are scored; numeric and refusal questions are judged by the router.
"""

from __future__ import annotations

import json
import math
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from law_assistant.chunk.chunker import Chunk
from law_assistant.evaluation.gold import GoldQuestion
from law_assistant.evaluation.relevance import matches, targets_of

KS = (1, 3, 5, 10)


@dataclass(frozen=True)
class QuestionScore:
    question_id: str
    first_rank: int | None  # rank of the first chunk matching a primary provision
    hit: dict[int, float]
    recall: dict[int, float]
    reciprocal_rank: float
    ndcg: dict[int, float]


def retrieval_questions(questions: Sequence[GoldQuestion]) -> list[GoldQuestion]:
    return [q for q in questions if q.route == "retrieve"]


def score_question(question: GoldQuestion, ranking: Sequence[Chunk], ks: Sequence[int] = KS) -> QuestionScore:
    targets = targets_of(question)
    primaries = [t for t in targets if t.grade == 2]
    if not primaries:
        raise ValueError(f"{question.id}: a retrieval question needs a primary gold provision")
    found_at: dict[int, int] = {}  # target index -> first rank at which any chunk matched it
    gain_at: dict[int, int] = {}  # rank -> nDCG gain, for the one provision a chunk is credited with
    credited: set[int] = set()
    for rank, chunk in enumerate(ranking, start=1):
        matched = [t for t in targets if matches(chunk, t.gold)]
        for t in matched:
            found_at.setdefault(t.index, rank)
        fresh = [t for t in matched if t.index not in credited]
        if fresh:
            best = max(fresh, key=lambda t: (t.grade, -t.index))
            credited.add(best.index)
            gain_at[rank] = 2**best.grade - 1
    primary_ranks = [found_at[t.index] for t in primaries if t.index in found_at]
    first_rank = min(primary_ranks) if primary_ranks else None
    ideal = sorted((2**t.grade - 1 for t in targets), reverse=True)
    ndcg = {}
    for k in ks:
        dcg = sum(g / math.log2(r + 1) for r, g in gain_at.items() if r <= k)
        best_possible = sum(g / math.log2(i + 2) for i, g in enumerate(ideal[:k]))
        ndcg[k] = dcg / best_possible
    return QuestionScore(
        question_id=question.id,
        first_rank=first_rank,
        hit={k: 1.0 if first_rank is not None and first_rank <= k else 0.0 for k in ks},
        recall={k: sum(1 for r in primary_ranks if r <= k) / len(primaries) for k in ks},
        reciprocal_rank=1 / first_rank if first_rank else 0.0,
        ndcg=ndcg,
    )


def score_run(
    questions: Sequence[GoldQuestion],
    run: Mapping[str, Sequence[str]],
    chunks_by_id: Mapping[str, Chunk],
    ks: Sequence[int] = KS,
) -> list[QuestionScore]:
    """Score a run (question id -> ranked chunk ids) on every retrieval question; the run must cover all."""
    wanted = retrieval_questions(questions)
    missing = [q.id for q in wanted if q.id not in run]
    if missing:
        raise ValueError(f"the run lacks questions: {', '.join(missing)}")
    scores = []
    for q in wanted:
        ranking = []
        for chunk_id in run[q.id]:
            if chunk_id not in chunks_by_id:
                raise ValueError(f"{q.id}: unknown chunk id {chunk_id}")
            ranking.append(chunks_by_id[chunk_id])
        scores.append(score_question(q, ranking, ks))
    return scores


def unreachable_targets(questions: Sequence[GoldQuestion], chunks: Sequence[Chunk]) -> list[tuple[str, int]]:
    """Gold provisions no chunk of the corpus can satisfy (an error in the gold, not a retrieval miss)."""
    return [
        (t.question_id, t.index)
        for q in retrieval_questions(questions)
        for t in targets_of(q)
        if not any(matches(c, t.gold) for c in chunks)
    ]


def metric_values(scores: Sequence[QuestionScore], name: str) -> list[float]:
    """One value per question for a metric named "mrr", "hit@5", "recall@10" or "ndcg@3"."""
    if name == "mrr":
        return [s.reciprocal_rank for s in scores]
    kind, _, k = name.partition("@")
    table = {"hit": "hit", "recall": "recall", "ndcg": "ndcg"}
    if kind not in table or not k.isdigit():
        raise ValueError(f"unknown metric {name!r}")
    return [getattr(s, table[kind])[int(k)] for s in scores]


def summarise(scores: Sequence[QuestionScore], ks: Sequence[int] = KS) -> dict[str, float]:
    if not scores:
        raise ValueError("no scores to summarise")
    names = [f"{kind}@{k}" for kind in ("hit", "recall", "ndcg") for k in ks] + ["mrr"]
    return {name: sum(metric_values(scores, name)) / len(scores) for name in names}


def write_run(path: Path, run: Mapping[str, Sequence[str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = (
        json.dumps({"question_id": q, "chunk_ids": list(run[q])}, ensure_ascii=False) for q in sorted(run)
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def read_run(path: Path) -> dict[str, list[str]]:
    with path.open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f if line.strip()]
    return {row["question_id"]: row["chunk_ids"] for row in rows}


# --- bootstrap ---------------------------------------------------------------------------------------------


def _percentiles(means: list[float], confidence: float) -> tuple[float, float]:
    means.sort()
    alpha = 1 - confidence
    low = means[int(alpha / 2 * len(means))]
    high = means[min(len(means) - 1, int((1 - alpha / 2) * len(means)))]
    return low, high


def bootstrap_ci(
    values: Sequence[float], *, resamples: int = 10_000, seed: int = 0, confidence: float = 0.95
) -> tuple[float, float, float]:
    """Mean of the values and a percentile interval from resampling the questions with replacement."""
    if not values:
        raise ValueError("no values")
    rng = random.Random(seed)
    n = len(values)
    means = [sum(values[rng.randrange(n)] for _ in range(n)) / n for _ in range(resamples)]
    low, high = _percentiles(means, confidence)
    return sum(values) / n, low, high


@dataclass(frozen=True)
class PairedResult:
    difference: float  # mean of (b - a) over the questions
    low: float
    high: float
    p_not_better: float  # share of resamples in which b is not better than a


def paired_bootstrap(
    a: Sequence[float],
    b: Sequence[float],
    *,
    resamples: int = 10_000,
    seed: int = 0,
    confidence: float = 0.95,
) -> PairedResult:
    """The difference between two variants on the same questions, with an interval from joint resampling."""
    if len(a) != len(b):
        raise ValueError("paired values must come from the same questions (equal length)")
    if not a:
        raise ValueError("no values")
    diffs = [y - x for x, y in zip(a, b, strict=True)]
    rng = random.Random(seed)
    n = len(diffs)
    means = [sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(resamples)]
    not_better = sum(1 for m in means if m <= 0) / resamples
    low, high = _percentiles(means, confidence)
    return PairedResult(sum(diffs) / n, low, high, not_better)
