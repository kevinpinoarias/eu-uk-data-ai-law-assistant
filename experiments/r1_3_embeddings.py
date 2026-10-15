"""
R1.3: the embedding baseline. How well does embedding search retrieve the right law on the development
questions, compared with BM25 (R1.1)?

PRE-REGISTRATION (written 15 October 2026, before the first call to the model; see docs/PHASE3_PLAN.md)

Variant: gemini-embedding-2 (Google, free tier). Every chunk is embedded once at the model's full 3,072
numbers and cached in data/indexes/; the vector used is the first 768 numbers renormalised (768 is a size
Google recommends); brute-force cosine similarity. Passage prompt
"title: {context line} | text: {chunk text}";
question prompt "task: search result | query: {question text}" (Google's documented forms).
Data: the 3,831 chunks and the 31 development retrieval questions. The test half is not touched.

Preliminary check (stop if it fails): on one text, the vector from asking Google for 768 numbers must match
the first 768 numbers of the 3,072-number vector, renormalised (cosine similarity at least 0.999). If not,
report it and do not run R1.3; how to make a shorter vector then goes back to the plan.

Primary metric recall@5; also MRR, nDCG@10, hit@5, recall@10; 95 % bootstrap intervals (10,000 resamples,
seed 0). Breakdowns as in R1. Comparison with R1.1 on recall@5 by a paired bootstrap.

Decision rule: R1.3 is called better than R1.1 only if the lower end of its paired interval for recall@5 is
above 0. The "current pipeline" for later comparisons is then R1.3; otherwise it stays R1.1 (the simpler and
free of a key). Nothing else is adopted.

Stated expectation (can be wrong): R1.3 beats R1.1 on recall@5, most on the lay-worded and the cross-language
questions, and is still below 0.9.

Terms: free-tier content may be used by Google to improve its products; what is sent is public law text and
the public gold questions. Requires GEMINI_API_KEY in .env.

Run: python experiments/r1_3_embeddings.py [--log]
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
from law_assistant.retrieval.dense import DenseIndex
from law_assistant.retrieval.gemini import GeminiEmbedder
from law_assistant.retrieval.report import format_table, summarise_with_ci
from law_assistant.retrieval.runner import breakdown, evaluate, run_retriever, select
from law_assistant.retrieval.vectors import truncate

K = 10
DIMENSIONS = 768
STORE = settings.PROJECT_ROOT / "data" / "indexes" / "gemini-embedding-2"
RUNS = settings.PROJECT_ROOT / "data" / "runs"
LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"


def cosine(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def main() -> int:
    settings.load_env_file()
    embedder = GeminiEmbedder.from_env(
        batch_size=16, pause=4.0
    )  # gentle pace: the key may be shared with a live app
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")

    sample = "The data subject shall have the right to obtain the erasure of personal data."
    full = embedder.embed_texts([sample])[0]
    asked = embedder.embed_one(sample, dimensions=DIMENSIONS)
    agreement = cosine(truncate(full, DIMENSIONS), truncate(asked, DIMENSIONS))
    print(f"preliminary check: {len(full)} numbers by default; 768 asked vs truncated cosine {agreement:.5f}")
    if agreement < 0.999:
        print("check failed; stopping (see the pre-registration)")
        return 1

    index = DenseIndex(chunks, embedder, STORE, dimensions=DIMENSIONS, name="gemini-768")
    run = run_retriever(index, questions, k=K)
    write_run(RUNS / "r1_3_gemini-768.jsonl", run)
    scores = evaluate(questions, run, chunks)
    bm25 = evaluate(questions, read_run_for_bm25(chunks, questions), chunks)

    results = {
        "R1.1 BM25 plain": summarise_with_ci(bm25),
        "R1.3 Gemini embedding 768": summarise_with_ci(scores),
    }
    paired = paired_bootstrap(metric_values(bm25, "recall@5"), metric_values(scores, "recall@5"))
    corpus = Corpus.from_dir()

    def shared_words(q) -> str:
        texts = [t for g in q.gold if g.role == "primary" for t in corpus.unit_texts(g, q.language)]
        many = overlap_ratio(q.text, texts, corpus.idf(q.language)) >= 0.25
        return "shares many words" if many else "shares few words"

    out = [
        f"### R1.3 embeddings on the development questions ({len(questions)} retrieval questions)",
        "",
        format_table(results),
        "",
        f"R1.3 against R1.1, recall@5: difference {paired.difference:+.3f}, 95 % interval "
        f"{paired.low:+.3f} to {paired.high:+.3f}; share of resamples in which R1.3 is not better "
        f"{paired.p_not_better:.2f}.",
    ]
    groupings = (
        ("question type", lambda q: q.type),
        ("question language", lambda q: q.language),
        ("shared words with its gold text", shared_words),
    )
    for title, key in groupings:
        out += ["", f"Recall@5 by {title} (R1.1 BM25, R1.3 embeddings; number of questions):", ""]
        by1 = breakdown(questions, bm25, key, "recall@5")
        by2 = breakdown(questions, scores, key, "recall@5")
        out += [
            f"- {name}: {by1[name][0]:.2f}, {by2[name][0]:.2f} (n = {by1[name][1]})" for name in sorted(by1)
        ]
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## R1.3 embeddings, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
        print(f"\nlogged to {LOG}")
    return 0


def read_run_for_bm25(chunks, questions):
    return run_retriever(BM25Index(chunks, name="bm25-plain"), questions, k=K)


if __name__ == "__main__":
    sys.exit(main())
