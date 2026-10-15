"""
R8 (index version policy) and R10 (collapsing duplicate copies), run with BM25 as the retriever.

PRE-REGISTRATION (written 15 October 2026, before the first run; see docs/PHASE3_PLAN.md)

These are run with BM25 because it needs no key and does not compete for the embedding quota. Both questions
are asked again with embeddings once R1.3 exists, because duplicates and versions matter differently there
(an embedding search also returns the other language's copy). Any conclusion here is provisional.

Data: the 3,831 chunks and the 31 development retrieval questions of the frozen gold set. Test half untouched.
Baseline: R1.1, BM25 plain over all chunks (recall@5 0.24 on these questions).

R8, which texts are in the index (3 variants):
  R8.1  everything (= R1.1, the baseline).
  R8.2  current text only: drop the first-published articles and annexes of the GDPR and the AI Act, keep
        their recitals and every other text.
  R8.3  original text for questions dated before 27 July 2026, current text for all others. The date is read
        from the gold question, so this is an upper bound for a router that has to infer it (R6).
R10, copies in the results (2 variants on top of R1.1; each asks BM25 for 50 and keeps the best of a group):
  R10.1 one chunk per piece of a provision across versions and languages.
  R10.2 one chunk per article, section, annex or recital, whichever piece (expected to lose pieces that carry
        the pinpoint).
Not tested here: combinations of R8 and R10.

Primary metric recall@5; also MRR, nDCG@10, hit@5, recall@10; 95 % bootstrap intervals (10,000 resamples,
seed 0); each variant against R1.1 by a paired bootstrap on recall@5. Also reported: recall@5 on the
version-sensitive questions (as-of questions and questions whose gold pins a version), and how many gold
provisions each index makes unreachable.

Decision rules: a variant is adopted only if the lower end of its paired interval for recall@5 is above 0.
R8.2 is additionally not adoptable alone if it makes any gold provision unreachable (the questions about the
original text); it measures what the duplicates cost. R8.3 and R10.1 are the candidates.

Stated expectations (can be wrong): R8.2 raises recall@5 on undated questions and zeroes the questions
about the original text; R8.3 keeps both; R10.1 helps a little (copies freed from the top five); R10.2
hurts or does not help.

REPEAT WITH EMBEDDINGS (addendum written 15 October 2026, before the run): `--model bge` repeats the same
variants, metrics, comparisons and decision rules with BGE-M3 as the retriever (the dense index over each
policy's chunks reads the already saved vectors). Baseline: BGE-M3 over all chunks (R4.1, recall@5 0.53).
Stated expectations (can be wrong): with embeddings an article's other-language copy is also returned, so
R10.1 frees slots and gains a little (point estimate above 0), and R8.2 gains on undated questions while
still losing the two questions about the original text; neither interval is expected to exclude 0 on 31
questions.

Run: python experiments/r8_r10_bm25.py [--model bm25|bge] [--log]
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date

from law_assistant import settings
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.metrics import metric_values, paired_bootstrap, unreachable_targets, write_run
from law_assistant.retrieval.bm25 import BM25Index
from law_assistant.retrieval.policies import (
    AsOfRetriever,
    CollapsedRetriever,
    current_text_only,
    original_text_only,
)
from law_assistant.retrieval.report import format_table, summarise_with_ci
from law_assistant.retrieval.runner import evaluate, run_retriever, select

K = 10
MODEL = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "bm25"
CUTOFF = "2026-07-27"  # the date of the consolidated AI Act
RUNS = settings.PROJECT_ROOT / "data" / "runs"
LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"


def main() -> int:
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    by_id = {c.id: c for c in chunks}
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")

    if MODEL == "bge":
        from law_assistant.retrieval.bge import BGEEmbedder, document_prompt, query_prompt
        from law_assistant.retrieval.dense import DenseIndex

        embedder = BGEEmbedder.load(settings.PROJECT_ROOT / "data" / "models" / "bge-m3", device="cuda")
        store = settings.PROJECT_ROOT / "data" / "indexes" / "bge-m3"

        def make(subset, name):
            return DenseIndex(
                subset, embedder, store, name=name,
                document_prompt_fn=document_prompt, query_prompt_fn=query_prompt,
            )  # fmt: skip

    else:

        def make(subset, name):
            return BM25Index(subset, name=name)

    base = make(chunks, f"{MODEL}-plain")
    current = current_text_only(chunks)
    original = original_text_only(chunks)
    retrievers = {
        "R8.1 everything (baseline R1.1)": base,
        "R8.2 current text only": make(current, f"{MODEL}-current"),
        "R8.3 original for past dates, current otherwise": AsOfRetriever(
            questions,
            early=make(original, f"{MODEL}-original"),
            late=make(current, f"{MODEL}-current"),
            cutoff=CUTOFF,
        ),
        "R10.1 collapse copies of a piece": CollapsedRetriever(base, by_id, by="copies"),
        "R10.2 collapse to one chunk per unit": CollapsedRetriever(base, by_id, by="units"),
    }
    scores, results = {}, {}
    for label, retriever in retrievers.items():
        run = run_retriever(retriever, questions, k=K)
        write_run(RUNS / f"r8_r10_{MODEL}_{retriever.name.replace('|', '_')}.jsonl", run)
        scores[label] = evaluate(questions, run, chunks)
        results[label] = summarise_with_ci(scores[label])

    baseline = scores["R8.1 everything (baseline R1.1)"]
    sensitive = [
        i for i, q in enumerate(questions) if q.type == "as_of" or any(g.version is not None for g in q.gold)
    ]
    out = [
        f"### R8 and R10 with {MODEL} on the development questions ({len(questions)} retrieval questions)",
        "",
        format_table(results),
        "",
        "Each variant against R1.1 on recall@5 (paired bootstrap), and recall@5 on the "
        f"{len(sensitive)} version-sensitive questions:",
        "",
    ]
    base_sensitive = sum(metric_values(baseline, "recall@5")[i] for i in sensitive) / len(sensitive)
    for label, s in scores.items():
        paired = paired_bootstrap(metric_values(baseline, "recall@5"), metric_values(s, "recall@5"))
        mine = sum(metric_values(s, "recall@5")[i] for i in sensitive) / len(sensitive)
        out.append(
            f"- {label}: difference {paired.difference:+.3f} (95 % interval {paired.low:+.3f} to "
            f"{paired.high:+.3f}); version-sensitive recall@5 {mine:.2f} (baseline {base_sensitive:.2f})"
        )
    out += ["", "Gold provisions no chunk of the index can satisfy (of the development questions):", ""]
    for name, index_chunks in (
        ("all texts", chunks),
        ("current text only", current),
        ("original text only", original),
    ):
        lost = unreachable_targets(questions, index_chunks)
        out.append(f"- {name}: {len(lost)} ({', '.join(sorted({q for q, _ in lost})) or 'none'})")
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## R8 and R10 with {MODEL}, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
        print(f"\nlogged to {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
