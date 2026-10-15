"""
R1: baselines. How well do keyword search and embedding search retrieve the right law on the development
questions?

PRE-REGISTRATION (written 15 October 2026, before the first run; see docs/PHASE3_PLAN.md sections 3 and 5)

Data: the 3,831 chunks in data/chunks/ (cap 400 words) and the 31 development retrieval questions of the
frozen gold set (eval/gold/MANIFEST.json, fingerprint 7d9a62f5...). The test half is not touched.

Variants (3 planned; this script runs the first two, R1.3 waits for the embedding decision):
  R1.1  BM25 over each chunk's context line and text; lower-cased letters and digits; no stemming or stop
        words; k1 = 1.2, b = 0.75; no tuning of the parameters.
  R1.2  The same with accents folded.
  R1.3  Embedding search, brute-force cosine, provisional model (not run here).
Reference rows: a random ranking (mean of 20 draws) and the oracle.

Primary metric: recall@5. Also reported: MRR, nDCG@10, hit@5, recall@10; 95 % bootstrap intervals over
questions (10,000 resamples, seed 0). Breakdowns by question type, by question language, and by how many of
the question's distinctive words its gold text shares (weighted overlap below or above 0.25).

Decision rule: R1 adopts nothing. It fixes the baselines. The "current pipeline" for later comparisons is the
better of R1.1 and R1.2 on recall@5, ties to the simpler (R1.1). R1.2 against R1.1 is a paired comparison; it
is called better only if the lower end of its paired interval for recall@5 is above 0.

Stated expectation (can be wrong): keyword search does well where a question uses the law's own words and
badly on lay wording; neither baseline exceeds 0.9 recall@5.

Run: python experiments/r1_baselines.py [--log]    (--log appends the result to docs/EXPERIMENTS.md)
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date

from law_assistant import settings
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.checks import Corpus, overlap_ratio
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.metrics import metric_values, paired_bootstrap, write_run
from law_assistant.retrieval.bm25 import BM25Index
from law_assistant.retrieval.reference import OracleRetriever, RandomRetriever
from law_assistant.retrieval.report import REPORTED, format_table, summarise_with_ci
from law_assistant.retrieval.runner import breakdown, evaluate, run_retriever, select

K = 10
RUNS = settings.PROJECT_ROOT / "data" / "runs"
LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"


def main() -> int:
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")
    corpus = Corpus.from_dir()

    def shared_words(q) -> str:
        texts = [t for g in q.gold if g.role == "primary" for t in corpus.unit_texts(g, q.language)]
        many = overlap_ratio(q.text, texts, corpus.idf(q.language)) >= 0.25
        return "shares many words" if many else "shares few words"

    retrievers = {
        "R1.1 BM25 plain": BM25Index(chunks, name="bm25-plain"),
        "R1.2 BM25 accents folded": BM25Index(chunks, fold_accents=True, name="bm25-folded"),
        "oracle (ceiling)": OracleRetriever(questions, chunks),
    }
    scores, results = {}, {}
    for label, retriever in retrievers.items():
        run = run_retriever(retriever, questions, k=K)
        write_run(RUNS / f"r1_{retriever.name}.jsonl", run)
        scores[label] = evaluate(questions, run, chunks)
        results[label] = summarise_with_ci(scores[label])
    draws = [
        evaluate(questions, run_retriever(RandomRetriever(chunks, seed=s), questions, k=K), chunks)
        for s in range(20)
    ]
    floor = {m: sum(sum(metric_values(d, m)) / len(questions) for d in draws) / len(draws) for m in REPORTED}
    results["random (floor, mean of 20 draws)"] = {m: (v, v, v) for m, v in floor.items()}

    out = [
        f"### R1 baselines on the development questions ({len(questions)} retrieval questions)",
        "",
        format_table(results),
        "",
    ]
    a, b = scores["R1.1 BM25 plain"], scores["R1.2 BM25 accents folded"]
    paired = paired_bootstrap(metric_values(a, "recall@5"), metric_values(b, "recall@5"))
    out.append(
        f"R1.2 against R1.1, recall@5: difference {paired.difference:+.3f}, 95 % interval "
        f"{paired.low:+.3f} to {paired.high:+.3f}; share of resamples in which R1.2 is not better "
        f"{paired.p_not_better:.2f}."
    )
    groupings = (
        ("question type", lambda q: q.type),
        ("question language", lambda q: q.language),
        ("shared words with its gold text", shared_words),
    )
    for title, key in groupings:
        out += ["", f"Recall@5 by {title} (R1.1 BM25 plain, R1.2 folded; number of questions):", ""]
        by1 = breakdown(questions, a, key, "recall@5")
        by2 = breakdown(questions, b, key, "recall@5")
        out += [
            f"- {name}: {by1[name][0]:.2f}, {by2[name][0]:.2f} (n = {by1[name][1]})" for name in sorted(by1)
        ]
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## R1 baselines, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        previous = LOG.read_text(encoding="utf-8") if LOG.exists() else "# Experiment log\n"
        LOG.write_text(previous + header + report + "\n", encoding="utf-8")
        print(f"\nlogged to {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
