"""Summaries with bootstrap intervals and the markdown tables that go into docs/EXPERIMENTS.md."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from law_assistant.evaluation.metrics import QuestionScore, bootstrap_ci, metric_values

REPORTED = ("recall@5", "mrr", "ndcg@10", "hit@5", "recall@10")  # recall@5 is the primary metric


def summarise_with_ci(
    scores: Sequence[QuestionScore],
    *,
    metrics: Sequence[str] = REPORTED,
    resamples: int = 10_000,
    seed: int = 0,
) -> dict[str, tuple[float, float, float]]:
    """For each metric: (mean, low, high) with a 95 % bootstrap interval over the questions."""
    return {m: bootstrap_ci(metric_values(scores, m), resamples=resamples, seed=seed) for m in metrics}


def format_table(results: Mapping[str, Mapping[str, tuple[float, float, float]]]) -> str:
    """One row per variant, one column per metric, each cell "mean (low to high)"."""
    header = "| Variant | " + " | ".join(REPORTED) + " |"
    lines = [header, "|---|" + "---|" * len(REPORTED)]
    for variant, summary in results.items():
        cells = [f"{summary[m][0]:.2f} ({summary[m][1]:.2f} to {summary[m][2]:.2f})" for m in REPORTED]
        lines.append(f"| {variant} | " + " | ".join(cells) + " |")
    return "\n".join(lines)
