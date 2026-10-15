"""
R5: does a reranker earn its latency? BGE-M3's top candidates re-scored by a cross-encoder
(BAAI/bge-reranker-v2-m3, Apache-2.0, on this machine), compared with BGE-M3 alone (R4.1).

PRE-REGISTRATION (written 15 October 2026, before the reranker has scored any candidate; see
docs/PHASE3_PLAN.md)

First stage: BGE-M3 exactly as in R4.1 (vectors cached in data/indexes/bge-m3, question as typed).
Reranker: loaded in half precision on the graphics card; the score is the model's raw output (higher is more
relevant); the pair is "question, context line + chunk text", cut at 512 tokens (the model page's example
length; the number of scored pairs that are cut is reported); batches of 16.
Variants (both counted in the experiment tally):
  R5.1  rerank the first stage's top 30 (the plan's variant).
  R5.2  rerank the first stage's top 50 (more reach, more latency).
Chunks below the depth keep the first stage's order behind the reranked ones.
Data: the 3,831 chunks and the 31 development retrieval questions of the frozen gold set. Test half untouched.

Primary metric recall@5; also MRR, nDCG@10, hit@5, recall@10; 95 % bootstrap intervals (10,000 resamples,
seed 0). Paired bootstrap on recall@5 against R4.1 (and R5.2 against R5.1). Breakdowns as in R4.
Latency: wall-clock seconds per question for the first stage alone and for first stage plus reranker, on this
machine (GTX 1060, half precision), the reranker's share being the difference. Reported, not tuned.

Decision rule: R5.1 is adopted if the lower end of its paired interval against R4.1 on recall@5 is above 0
(the cost is reported next to it and weighed in the final decision, not decided here). R5.2 replaces R5.1 only
if its paired interval against R5.1 is also above 0. Otherwise nothing is adopted and the reranker is recorded
as a candidate. No depth, length or score tuning after seeing results.

Ceiling (rank_depth.py, already run): 65 % of the required provisions are within BGE-M3's top 30 (76 % in the
top 50), so a perfect reranker could add at most about 21 points to the 44 % in the top 5 (about 32 points at
depth 50). Stated expectation (can be wrong): R5.1 raises recall@5 above 0.53 with a lower paired bound above
0, stays below the ceiling of about 0.65, and helps most where the lay wording is far from the legal wording;
R5.2 is not detectably better than R5.1.

Run: python experiments/r5_reranker.py [--log]
"""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import date

from law_assistant import settings
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.checks import Corpus, overlap_ratio
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.metrics import metric_values, paired_bootstrap, write_run
from law_assistant.retrieval.bge import BGEEmbedder, document_prompt, query_prompt
from law_assistant.retrieval.dense import DenseIndex
from law_assistant.retrieval.report import format_table, summarise_with_ci
from law_assistant.retrieval.rerank import RerankedRetriever, Reranker
from law_assistant.retrieval.runner import breakdown, evaluate, run_retriever, select

K = 10
DEPTHS = (30, 50)
BGE_DIR = settings.PROJECT_ROOT / "data" / "models" / "bge-m3"
RERANK_DIR = settings.PROJECT_ROOT / "data" / "models" / "bge-reranker-v2-m3"
STORE = settings.PROJECT_ROOT / "data" / "indexes" / "bge-m3"
RUNS = settings.PROJECT_ROOT / "data" / "runs"
LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"
MAX_LENGTH = 512


def seconds_per_question(retriever, questions) -> float:
    start = time.perf_counter()
    for q in questions:
        retriever.search(q.text, K)
    return (time.perf_counter() - start) / len(questions)


def main() -> int:
    import torch
    from transformers import AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("device:", device, torch.cuda.get_device_name(0) if device == "cuda" else "")
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    by_id = {c.id: c for c in chunks}
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")

    embedder = BGEEmbedder.load(BGE_DIR, device=device, max_length=1024)
    first = DenseIndex(
        chunks, embedder, STORE, name="bge-m3",
        document_prompt_fn=document_prompt, query_prompt_fn=query_prompt,
    )  # fmt: skip
    reranker = Reranker.load(RERANK_DIR, device=device, max_length=MAX_LENGTH)

    base_run = run_retriever(first, questions, k=K)
    base = evaluate(questions, base_run, chunks)
    results = {"R4.1 BGE-M3": summarise_with_ci(base)}
    scores_by_depth, latency, retrievers = {}, {}, {}
    for depth in DEPTHS:
        retriever = RerankedRetriever(first, reranker, chunks, depth=depth)
        retrievers[depth] = retriever
        run = run_retriever(retriever, questions, k=K)  # scores every pair once and caches them
        write_run(RUNS / f"r5_rerank{depth}.jsonl", run)
        scores_by_depth[depth] = evaluate(questions, run, chunks)
        results[f"R5.{DEPTHS.index(depth) + 1} rerank top {depth}"] = summarise_with_ci(
            scores_by_depth[depth]
        )

    # Latency: a fresh reranker object so that nothing is cached, first stage warmed up before timing.
    first_only = seconds_per_question(first, questions)
    for depth in DEPTHS:
        fresh = RerankedRetriever(first, reranker, chunks, depth=depth)
        latency[depth] = seconds_per_question(fresh, questions)

    # How many scored pairs are cut at the reranker's length limit.
    tokenizer = AutoTokenizer.from_pretrained(str(RERANK_DIR))
    pairs = [
        (q.text, document_prompt(by_id[cid])) for q in questions for cid in first.search(q.text, max(DEPTHS))
    ]
    lengths = [len(tokenizer(a, b)["input_ids"]) for a, b in pairs]
    cut = sum(1 for n in lengths if n > MAX_LENGTH)

    p1 = paired_bootstrap(metric_values(base, "recall@5"), metric_values(scores_by_depth[30], "recall@5"))
    p2 = paired_bootstrap(metric_values(base, "recall@5"), metric_values(scores_by_depth[50], "recall@5"))
    p21 = paired_bootstrap(
        metric_values(scores_by_depth[30], "recall@5"), metric_values(scores_by_depth[50], "recall@5")
    )
    corpus = Corpus.from_dir()

    def shared_words(q) -> str:
        texts = [t for g in q.gold if g.role == "primary" for t in corpus.unit_texts(g, q.language)]
        many = overlap_ratio(q.text, texts, corpus.idf(q.language)) >= 0.25
        return "shares many words" if many else "shares few words"

    def line(label, p, what):
        return (
            f"{label}, recall@5: difference {p.difference:+.3f}, "
            f"95 % interval {p.low:+.3f} to {p.high:+.3f}; "
            f"share of resamples in which {what} is not better {p.p_not_better:.2f}."
        )

    out = [
        f"### R5 reranker (bge-reranker-v2-m3) over BGE-M3 on the development questions "
        f"({len(questions)} retrieval questions)",
        "",
        format_table(results),
        "",
        line("R5.1 (top 30) against R4.1", p1, "the reranker"),
        line("R5.2 (top 50) against R4.1", p2, "the reranker"),
        line("R5.2 (top 50) against R5.1 (top 30)", p21, "depth 50"),
        "",
        f"Latency per question on this machine (GTX 1060, half precision): first stage alone "
        f"{first_only:.2f} s; with reranker over the top 30 {latency[30]:.2f} s; "
        f"over the top 50 {latency[50]:.2f} s.",
        f"Scored pairs cut at {MAX_LENGTH} tokens: {cut} of {len(pairs)} "
        f"(the top 50 candidates of {len(questions)} questions).",
    ]
    groupings = (
        ("question type", lambda q: q.type),
        ("question language", lambda q: q.language),
        ("shared words with its gold text", shared_words),
    )
    for title, key in groupings:
        out += ["", f"Recall@5 by {title} (R4.1 BGE-M3, R5.1 top 30; number of questions):", ""]
        by1 = breakdown(questions, base, key, "recall@5")
        by2 = breakdown(questions, scores_by_depth[30], key, "recall@5")
        out += [
            f"- {name}: {by1[name][0]:.2f}, {by2[name][0]:.2f} (n = {by1[name][1]})" for name in sorted(by1)
        ]
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## R5 reranker, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
        print(f"\nlogged to {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
