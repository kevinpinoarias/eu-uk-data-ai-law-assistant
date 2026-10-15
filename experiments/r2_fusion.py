"""
R2: hybrid retrieval. Does merging keyword search and embedding search (reciprocal rank fusion) find
more of the right law than either alone?

PRE-REGISTRATION (written 15 October 2026, before any embedding result exists; see docs/PHASE3_PLAN.md)

Needs the saved chunk vectors of an embedding model: --model bge (BGE-M3, 1,024 numbers, run locally; the
model used for the first run, because the hosted model's free tier stalled) or --model gemini
(gemini-embedding-2 at 768 numbers). It refuses to run if any chunk lacks a saved vector, so it never starts
a costly job.

Data: the 3,831 chunks and the 31 development retrieval questions of the frozen gold set. Test half untouched.

Variants (the fused ones are new; the two singles are the baselines):
  B1    BM25 plain (R1.1).           B2   embedding search alone (R1.3, or the model given by --store).
  R2.1  RRF of B1 and B2, depth 50 from each, k = 60, equal weights.
  R2.2  RRF with the embedding list weighted 2 to 1. Run only if R2.1 improves on the better single retriever
        in point estimate; otherwise recorded as not run.
  No other constants or weights are tried.

Primary metric recall@5; also MRR, nDCG@10, hit@5, recall@10; 95 % bootstrap intervals (10,000 resamples,
seed 0). Each fused variant is compared by a paired bootstrap on recall@5 with the better of B1 and B2 on
these questions (the harder comparison). Breakdowns by question type and question language.

Decision rule: a fused variant is adopted only if the lower end of its paired interval against the better
single retriever is above 0. Otherwise the better single retriever stays and the write-up says "no detectable
difference". It is not adopted for being merely "no worse".

Stated expectation (can be wrong): R2.1 beats both singles in point estimate, most on questions that mix legal
terms with lay wording; the gain over the better single is small enough that the interval may include 0.

Run: python experiments/r2_fusion.py --model bge|gemini [--log]
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date

from law_assistant import settings
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.metrics import metric_values, paired_bootstrap, write_run
from law_assistant.retrieval.bm25 import BM25Index
from law_assistant.retrieval.dense import DenseIndex, cache_key
from law_assistant.retrieval.fusion import FusedRetriever
from law_assistant.retrieval.gemini import GeminiEmbedder
from law_assistant.retrieval.report import format_table, summarise_with_ci
from law_assistant.retrieval.runner import breakdown, evaluate, run_retriever, select
from law_assistant.retrieval.vectors import VectorStore

K = 10
MODEL = sys.argv[sys.argv.index("--model") + 1] if "--model" in sys.argv else "bge"
RUNS = settings.PROJECT_ROOT / "data" / "runs"
LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"


def main() -> int:
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    if MODEL == "gemini":
        from law_assistant.retrieval.gemini import document_prompt, query_prompt

        store_path = settings.PROJECT_ROOT / "data" / "indexes" / "gemini-embedding-2"
        settings.load_env_file()
        embedder, model_name, dimensions = GeminiEmbedder.from_env(), "gemini-embedding-2", 768
    else:
        from law_assistant.retrieval.bge import BGEEmbedder, document_prompt, query_prompt

        store_path = settings.PROJECT_ROOT / "data" / "indexes" / "bge-m3"
        embedder = BGEEmbedder.load(settings.PROJECT_ROOT / "data" / "models" / "bge-m3", device="cuda")
        model_name, dimensions = "bge-m3", None
    store = VectorStore.load(store_path)
    missing = sum(1 for c in chunks if cache_key(model_name, document_prompt(c)) not in store)
    if missing:
        print(
            f"{missing} of {len(chunks)} chunks have no saved vector in {store_path}; finish embedding first"
        )
        return 1
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")

    bm25 = BM25Index(chunks, name="bm25-plain")
    dense = DenseIndex(
        chunks, embedder, store_path, dimensions=dimensions, name="embedding",
        document_prompt_fn=document_prompt, query_prompt_fn=query_prompt,
    )  # fmt: skip
    retrievers = {"B1 BM25 plain": bm25, "B2 embedding alone": dense}
    retrievers["R2.1 RRF equal weights"] = FusedRetriever([bm25, dense], name="rrf-equal")
    scores, results = {}, {}

    def run(label, retriever):
        out = run_retriever(retriever, questions, k=K)
        write_run(RUNS / f"r2_{MODEL}_{retriever.name}.jsonl", out)
        scores[label] = evaluate(questions, out, chunks)
        results[label] = summarise_with_ci(scores[label])

    for label, retriever in retrievers.items():
        run(label, retriever)
    mean = {k: sum(metric_values(v, "recall@5")) / len(questions) for k, v in scores.items()}
    best_single = max(("B1 BM25 plain", "B2 embedding alone"), key=lambda k: mean[k])
    note = "R2.2 not run (R2.1 does not improve on the better single retriever in point estimate)"
    if mean["R2.1 RRF equal weights"] > mean[best_single]:
        run(
            "R2.2 RRF embedding weighted 2 to 1",
            FusedRetriever([bm25, dense], weights=[1.0, 2.0], name="rrf-2to1"),
        )
        note = ""
    out = [
        f"### R2 hybrid retrieval ({MODEL}) on the development questions ({len(questions)} questions)",
        "",
        format_table(results),
        "",
        f"Better single retriever on recall@5: {best_single}. Fused variants against it (paired bootstrap):",
        "",
    ]
    for label in scores:
        if label.startswith("R2"):
            p = paired_bootstrap(
                metric_values(scores[best_single], "recall@5"), metric_values(scores[label], "recall@5")
            )
            out.append(
                f"- {label}: difference {p.difference:+.3f} (95 % interval {p.low:+.3f} to {p.high:+.3f}); "
                f"share of resamples in which it is not better {p.p_not_better:.2f}"
            )
    if note:
        out.append(f"- {note}")
    for title, key in (("question type", lambda q: q.type), ("question language", lambda q: q.language)):
        out += ["", f"Recall@5 by {title} ({', '.join(scores)}; number of questions):", ""]
        tables = {label: breakdown(questions, s, key, "recall@5") for label, s in scores.items()}
        first = next(iter(tables.values()))
        for name in sorted(first):
            cells = ", ".join(f"{t[name][0]:.2f}" for t in tables.values())
            out.append(f"- {name}: {cells} (n = {first[name][1]})")
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## R2 hybrid retrieval with {MODEL}, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
        print(f"\nlogged to {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
