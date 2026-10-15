"""
R3 (chunking), first part, run with BM25: does the chunk size, or the context line, change retrieval?

PRE-REGISTRATION (written 15 October 2026, before the first run; see docs/PHASE3_PLAN.md)

Run with BM25 because it needs no key and does not compete for the embedding quota. Any conclusion is
provisional: the experiment is repeated with embeddings, which may rank chunk sizes differently, and the
embedding model's own input limit (512 tokens for multilingual-e5, 8,192 for the others) adds a constraint.
Parent-and-child retrieval and paragraph-level chunks are not run here.

Data: the 14 parsed documents re-chunked at each cap by the existing chunker (the gold labels provisions, not
chunks, so it needs no change), and the 31 development retrieval questions of the frozen gold set. Test half
untouched. Baseline: R1.1 (cap 400, BM25 over the context line and the text, recall@5 0.24).

Variants (4, plus the baseline R3.1):
  R3.1  cap 400 words (= R1.1, the baseline).
  R3.2  cap 200 words.   R3.3  cap 300 words.   R3.4  cap 600 words.
  R3.5  cap 400 words, with the context line left out of the indexed text (law text only).

Primary metric recall@5; also MRR, nDCG@10, hit@5, recall@10; 95 % bootstrap intervals (10,000 resamples,
seed 0); each variant against R3.1 by a paired bootstrap on recall@5. Also reported: the number of chunks and
their mean length for each cap.

Decision rule: a variant is adopted only if the lower end of its paired interval for recall@5 is above 0.

Stated expectations (can be wrong): smaller chunks give BM25 a higher hit@5 on single-provision lookups but
split multi-provision answers, so recall@5 changes little; leaving the context line out lowers recall@5
slightly, because the article titles are words a lay question shares with the law.

Run: python experiments/r3_bm25.py [--log]
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date

from law_assistant import settings
from law_assistant.chunk.chunker import chunk_provisions
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.metrics import metric_values, paired_bootstrap, write_run
from law_assistant.parse.store import read_jsonl
from law_assistant.retrieval.bm25 import BM25Index
from law_assistant.retrieval.report import format_table, summarise_with_ci
from law_assistant.retrieval.runner import evaluate, run_retriever, select

K = 10
RUNS = settings.PROJECT_ROOT / "data" / "runs"
LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"


def chunk_all(cap: int):
    chunks = []
    for path in sorted(settings.PARSED_DIR.glob("*.jsonl")):
        chunks += chunk_provisions(read_jsonl(path), max_words=cap)
    return chunks


def main() -> int:
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")
    by_cap = {cap: chunk_all(cap) for cap in (200, 300, 400, 600)}
    variants = {
        "R3.1 cap 400 (baseline R1.1)": (400, True),
        "R3.2 cap 200": (200, True),
        "R3.3 cap 300": (300, True),
        "R3.4 cap 600": (600, True),
        "R3.5 cap 400, no context line": (400, False),
    }
    scores, results, sizes = {}, {}, {}
    for label, (cap, with_context) in variants.items():
        chunks = by_cap[cap]
        text_of = (lambda c: c.embed_text) if with_context else (lambda c: c.text)
        retriever = BM25Index(
            chunks, text_of=text_of, name=f"bm25-cap{cap}-{'ctx' if with_context else 'noctx'}"
        )
        run = run_retriever(retriever, questions, k=K)
        write_run(RUNS / f"r3_{retriever.name}.jsonl", run)
        scores[label] = evaluate(questions, run, chunks)
        results[label] = summarise_with_ci(scores[label])
        sizes[label] = (len(chunks), sum(c.words for c in chunks) / len(chunks))

    baseline = scores["R3.1 cap 400 (baseline R1.1)"]
    out = [
        f"### R3 (chunk size, context line) with BM25 on the development questions "
        f"({len(questions)} questions)",
        "",
        format_table(results),
        "",
        "Each variant against R3.1 on recall@5 (paired bootstrap), with the size of its index:",
        "",
    ]
    for label, s in scores.items():
        paired = paired_bootstrap(metric_values(baseline, "recall@5"), metric_values(s, "recall@5"))
        n, mean = sizes[label]
        out.append(
            f"- {label}: difference {paired.difference:+.3f} (95 % interval {paired.low:+.3f} to "
            f"{paired.high:+.3f}); {n:,} chunks, mean {mean:.0f} words"
        )
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## R3 chunk size and context line with BM25, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
        print(f"\nlogged to {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
