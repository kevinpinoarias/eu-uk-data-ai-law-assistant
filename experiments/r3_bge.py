"""
R3 (chunking), repeated with BGE-M3: does the chunk size, or the context line, change retrieval when the
retriever is an embedding model?

PRE-REGISTRATION (written 15 October 2026, before the run; see docs/PHASE3_PLAN.md and the BM25 run in
experiments/r3_bm25.py, whose variants, metrics and decision rule are repeated unchanged)

Variants: R3.1 cap 400 (the baseline, = R4.1), R3.2 cap 200, R3.3 cap 300, R3.4 cap 600, R3.5 cap 400 with
the context line left out of the embedded text. Each re-chunks the 14 parsed documents at that cap and embeds
the new chunk texts with BGE-M3 (cached by text, so identical chunks are not embedded twice). Sequences are
cut at 2,048 tokens in batches of 8. Parent-and-child retrieval and paragraph-level chunks are not run.

Data: the 31 development retrieval questions of the frozen gold set. Test half untouched.
Primary metric recall@5; also MRR, nDCG@10, hit@5, recall@10; 95 % bootstrap intervals (10,000 resamples,
seed 0); each variant against R3.1 by a paired bootstrap on recall@5. Decision rule: a variant is adopted
only if the lower end of its paired interval for recall@5 is above 0.

Stated expectations (can be wrong): smaller chunks (200, 300) raise hit@5 on single-provision lookups but
lower recall@5 on questions that need several provisions, so recall@5 does not improve detectably; cap 600
is not better; leaving the context line out lowers recall@5 (the article title is the part of a lay question
that matches the law's own heading).

Run: python experiments/r3_bge.py [--log]
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
from law_assistant.retrieval.bge import BGEEmbedder, document_prompt, query_prompt
from law_assistant.retrieval.dense import DenseIndex
from law_assistant.retrieval.report import format_table, summarise_with_ci
from law_assistant.retrieval.runner import evaluate, run_retriever, select

K = 10
MODEL_DIR = settings.PROJECT_ROOT / "data" / "models" / "bge-m3"
STORE = settings.PROJECT_ROOT / "data" / "indexes" / "bge-m3"
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
    embedder = BGEEmbedder.load(MODEL_DIR, device="cuda", max_length=2048, batch_size=8)
    by_cap = {cap: chunk_all(cap) for cap in (400, 200, 300, 600)}
    variants = {
        "R3.1 cap 400 (baseline R4.1)": (400, True),
        "R3.2 cap 200": (200, True),
        "R3.3 cap 300": (300, True),
        "R3.4 cap 600": (600, True),
        "R3.5 cap 400, no context line": (400, False),
    }
    scores, results, sizes = {}, {}, {}
    for label, (cap, with_context) in variants.items():
        chunks = by_cap[cap]
        tag = "ctx" if with_context else "noctx"
        print(f"{label}: embedding {len(chunks)} chunks ...", flush=True)
        index = DenseIndex(
            chunks, embedder, STORE, with_context=with_context, name=f"bge-cap{cap}-{tag}",
            document_prompt_fn=document_prompt, query_prompt_fn=query_prompt,
        )  # fmt: skip
        run = run_retriever(index, questions, k=K)
        write_run(RUNS / f"r3_bge-cap{cap}-{tag}.jsonl", run)
        scores[label] = evaluate(questions, run, chunks)
        results[label] = summarise_with_ci(scores[label])
        sizes[label] = (len(chunks), sum(c.words for c in chunks) / len(chunks))

    baseline = scores["R3.1 cap 400 (baseline R4.1)"]
    out = [
        f"### R3 (chunk size, context line) with BGE-M3 on the development questions "
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
            f"\n\n## R3 chunk size and context line with BGE-M3, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
        print(f"\nlogged to {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
