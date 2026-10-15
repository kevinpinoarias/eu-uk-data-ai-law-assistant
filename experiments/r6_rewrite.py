"""
R6 (part): does searching with a rewritten question help? Everyday wording ("a person responsible for data
protection") is restated in the law's vocabulary ("data protection officer") before BGE-M3 searches.

PRE-REGISTRATION (written 15 October 2026; the 31 rewrites were produced before any of them was scored, by a
separate agent that saw only the question texts, see eval/rewrites/README.md; no rewrite has been scored)

Variants (both counted in the experiment tally), first stage BGE-M3 exactly as in R4.1:
  R6.1  search with the rewrite alone (replace).
  R6.2  search with the question followed by the rewrite as one text (append).
Data: the 3,831 chunks and the 31 development retrieval questions of the frozen gold set. Test half untouched
(it has no rewrites). Not part of this run: filters (jurisdiction, language, as-of), which stay in R6 proper.

Primary metric recall@5; also MRR, nDCG@10, hit@5, recall@10; 95 % bootstrap intervals (10,000 resamples,
seed 0). Paired bootstrap on recall@5 against R4.1. Breakdowns as in R4. Also reported, as a check on the
prompt: how many rewrites exceed the 40 words the agent was asked to stay under.

Decision rule: a variant is adopted only if the lower end of its paired interval against R4.1 on recall@5 is
above 0. If both qualify, the one with the higher recall@5 is kept. An adopted rewrite step must still be
confirmed on the test half, with rewrites made by the same prompt, before it enters the final pipeline, and it
costs one language-model call per question in the final assistant (not measured here). No prompt or rewrite
changes after seeing results.

Stated expectation (can be wrong): R6.1 raises recall@5 above 0.53, most for the lay-worded questions that
share few words with their gold text, but with 31 questions the lower paired bound may still include 0; R6.2
sits between R4.1 and R6.1. Rewrites could also hurt questions whose answer depends on a date or a version,
and questions that already use the law's words.

Run: python experiments/r6_rewrite.py [--log]
"""

from __future__ import annotations

import json
import subprocess
import sys
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
from law_assistant.retrieval.rewrite import RewriteRetriever, read_rewrites
from law_assistant.retrieval.runner import breakdown, evaluate, run_retriever, select

K = 10
BGE_DIR = settings.PROJECT_ROOT / "data" / "models" / "bge-m3"
STORE = settings.PROJECT_ROOT / "data" / "indexes" / "bge-m3"
REWRITES = settings.PROJECT_ROOT / "eval" / "rewrites" / "r6_dev.jsonl"
RUNS = settings.PROJECT_ROOT / "data" / "runs"
LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"


def main() -> int:
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")
    rewrites = read_rewrites(REWRITES, questions)

    embedder = BGEEmbedder.load(BGE_DIR, device=device, max_length=1024)
    first = DenseIndex(
        chunks, embedder, STORE, name="bge-m3",
        document_prompt_fn=document_prompt, query_prompt_fn=query_prompt,
    )  # fmt: skip
    base = evaluate(questions, run_retriever(first, questions, k=K), chunks)
    results = {"R4.1 BGE-M3": summarise_with_ci(base)}
    variants = {}
    for number, mode in ((1, "replace"), (2, "append")):
        retriever = RewriteRetriever(first, rewrites, mode=mode)
        run = run_retriever(retriever, questions, k=K)
        write_run(RUNS / f"r6_{mode}.jsonl", run)
        variants[mode] = evaluate(questions, run, chunks)
        results[f"R6.{number} {mode}"] = summarise_with_ci(variants[mode])

    corpus = Corpus.from_dir()

    def shared_words(q) -> str:
        texts = [t for g in q.gold if g.role == "primary" for t in corpus.unit_texts(g, q.language)]
        many = overlap_ratio(q.text, texts, corpus.idf(q.language)) >= 0.25
        return "shares many words" if many else "shares few words"

    words = [
        len(r["rewrite"].split()) for r in map(json.loads, REWRITES.read_text(encoding="utf-8").splitlines())
    ]
    out = [
        f"### R6 question rewriting on the development questions ({len(questions)} retrieval questions)",
        "",
        format_table(results),
        "",
    ]
    for number, mode in ((1, "replace"), (2, "append")):
        p = paired_bootstrap(metric_values(base, "recall@5"), metric_values(variants[mode], "recall@5"))
        out.append(
            f"R6.{number} ({mode}) against R4.1, recall@5: difference {p.difference:+.3f}, "
            f"95 % interval {p.low:+.3f} to {p.high:+.3f}; share of resamples in which the rewrite is not "
            f"better {p.p_not_better:.2f}."
        )
    out += [
        "",
        f"Rewrite length in words: mean {sum(words) / len(words):.1f}, longest {max(words)}; "
        f"{sum(1 for n in words if n > 40)} of {len(words)} exceed the 40 the agent was asked to stay under.",
    ]
    groupings = (
        ("question type", lambda q: q.type),
        ("question language", lambda q: q.language),
        ("shared words with its gold text", shared_words),
    )
    for title, key in groupings:
        out += ["", f"Recall@5 by {title} (R4.1, R6.1 replace, R6.2 append; number of questions):", ""]
        by0, by1, by2 = (
            breakdown(questions, s, key, "recall@5") for s in (base, variants["replace"], variants["append"])
        )
        out += [
            f"- {name}: {by0[name][0]:.2f}, {by1[name][0]:.2f}, {by2[name][0]:.2f} (n = {by0[name][1]})"
            for name in sorted(by0)
        ]
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## R6 question rewriting, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
        print(f"\nlogged to {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
