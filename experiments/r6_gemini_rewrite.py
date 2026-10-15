"""
R6 (part 2): the same rewriting idea with a rewriter that can run inside the pipeline. R6.1/R6.2 used rewrites
written once by a separate agent; the final assistant needs a model it can call for every new question, so
here Gemini 3.1 Flash-Lite (the project's planned chat model, called with the existing key) does the
rewriting.

PRE-REGISTRATION (written 15 October 2026, before any Gemini rewrite exists or has been scored)

Rewriter: gemini-3.1-flash-lite through generateContent, temperature 0, at most 200 output tokens, the
instructions in src/law_assistant/retrieval/rewriter.py (the R6 rules, reworded as a system instruction), the
question as the user text. Answers are cached in data/llm_cache/ so a rerun makes no calls; the 31 rewrites
are also written to eval/rewrites/r6_gemini_dev.jsonl. No prompt changes after seeing a result.
Variants (both counted in the experiment tally), first stage BGE-M3 exactly as in R4.1:
  R6.3  the question followed by the Gemini rewrite (append, the working configuration of decision 83).
  R6.4  the Gemini rewrite alone (replace).
Data: the 3,831 chunks and the 31 development retrieval questions of the frozen gold set. Test half untouched.

Primary metric recall@5; also MRR, nDCG@10, hit@5, recall@10; 95 % bootstrap intervals (10,000 resamples, seed
0). Paired bootstrap on recall@5 against R4.1, and for information (no rule rests on it) against the agent's
rewrites R6.2. Reported for cost: seconds per call (mean, median, slowest), prompt and output tokens in total
and per question. No price is stated because none has been verified.

Decision rule: the Gemini rewriter replaces the agent's rewrites as the pipeline's rewrite step if the lower
end of R6.3's paired interval against R4.1 on recall@5 is above 0. If it does not, the rewrite step stays
a candidate that has not been shown to work with a cheap in-pipeline model, and the 0.70 of R6.2 is reported
as an upper bound with a stronger model, not as the system's score.

Stated expectation (can be wrong): R6.3 lands between R4.1 (0.53) and R6.2 (0.70), with a lower paired bound
above 0, because a small cheap model knows less law than the agent that wrote R6.2; the Spanish questions gain
least, as before.

Run: python experiments/r6_gemini_rewrite.py [--log]   (needs GEMINI_API_KEY in .env)
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from statistics import mean, median

from law_assistant import settings
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.metrics import metric_values, paired_bootstrap, write_run
from law_assistant.llm.gemini import CachedGenerator, GeminiGenerator
from law_assistant.retrieval.bge import BGEEmbedder, document_prompt, query_prompt
from law_assistant.retrieval.dense import DenseIndex
from law_assistant.retrieval.report import format_table, summarise_with_ci
from law_assistant.retrieval.rewrite import RewriteRetriever, read_rewrites
from law_assistant.retrieval.rewriter import LLMRewriter
from law_assistant.retrieval.runner import breakdown, evaluate, run_retriever, select

K = 10
BGE_DIR = settings.PROJECT_ROOT / "data" / "models" / "bge-m3"
STORE = settings.PROJECT_ROOT / "data" / "indexes" / "bge-m3"
AGENT_REWRITES = settings.PROJECT_ROOT / "eval" / "rewrites" / "r6_dev.jsonl"
GEMINI_REWRITES = settings.PROJECT_ROOT / "eval" / "rewrites" / "r6_gemini_dev.jsonl"
CACHE = settings.PROJECT_ROOT / "data" / "llm_cache" / "rewrites.jsonl"
RUNS = settings.PROJECT_ROOT / "data" / "runs"
LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"


def main() -> int:
    import torch

    settings.load_env_file()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")

    generator = GeminiGenerator.from_env()
    rewriter = LLMRewriter(CachedGenerator(generator, CACHE))
    rewrites = rewriter.rewrite_all([q.text for q in questions])
    GEMINI_REWRITES.parent.mkdir(parents=True, exist_ok=True)
    with GEMINI_REWRITES.open("w", encoding="utf-8", newline="\n") as f:
        for q in questions:
            row = {"id": q.id, "model": generator.model, "rewrite": rewrites[q.text]}
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    embedder = BGEEmbedder.load(BGE_DIR, device=device, max_length=1024)
    first = DenseIndex(
        chunks, embedder, STORE, name="bge-m3",
        document_prompt_fn=document_prompt, query_prompt_fn=query_prompt,
    )  # fmt: skip
    base = evaluate(questions, run_retriever(first, questions, k=K), chunks)
    agent = evaluate(
        questions,
        run_retriever(
            RewriteRetriever(first, read_rewrites(AGENT_REWRITES, questions), mode="append"), questions, k=K
        ),
        chunks,
    )
    results = {"R4.1 BGE-M3": summarise_with_ci(base), "R6.2 agent rewrite, append": summarise_with_ci(agent)}
    variants = {}
    for number, mode in ((3, "append"), (4, "replace")):
        retriever = RewriteRetriever(first, rewrites, mode=mode)
        run = run_retriever(retriever, questions, k=K)
        write_run(RUNS / f"r6_gemini_{mode}.jsonl", run)
        variants[mode] = evaluate(questions, run, chunks)
        results[f"R6.{number} Gemini rewrite, {mode}"] = summarise_with_ci(variants[mode])

    out = [
        f"### R6.3/R6.4 question rewriting with {generator.model} on the development questions "
        f"({len(questions)} retrieval questions)",
        "",
        format_table(results),
        "",
    ]
    base_values = metric_values(base, "recall@5")
    for number, mode in ((3, "append"), (4, "replace")):
        p = paired_bootstrap(base_values, metric_values(variants[mode], "recall@5"))
        out.append(
            f"R6.{number} ({mode}) against R4.1, recall@5: difference {p.difference:+.3f}, "
            f"95 % interval {p.low:+.3f} to {p.high:+.3f}; share of resamples in which the rewrite is not "
            f"better {p.p_not_better:.2f}."
        )
    p = paired_bootstrap(metric_values(agent, "recall@5"), metric_values(variants["append"], "recall@5"))
    out.append(
        f"For information, R6.3 against the agent's R6.2, recall@5: difference {p.difference:+.3f}, "
        f"95 % interval {p.low:+.3f} to {p.high:+.3f}."
    )
    calls = generator.calls
    if calls:
        times = sorted(c.seconds for c in calls)
        out += [
            "",
            f"Cost of the rewrite step ({len(calls)} model calls this run; cached answers are not counted): "
            f"{mean(times):.2f} s per call on average, median {median(times):.2f} s, "
            f"slowest {times[-1]:.2f} s; "
            f"{sum(c.prompt_tokens for c in calls)} prompt tokens and "
            f"{sum(c.output_tokens for c in calls)} output tokens in total "
            f"({sum(c.prompt_tokens for c in calls) / len(calls):.0f} and "
            f"{sum(c.output_tokens for c in calls) / len(calls):.0f} per question).",
        ]
    else:
        out += [
            "",
            "Cost of the rewrite step: all answers came from the cache this run, so no calls were timed.",
        ]
    words = [len(r.split()) for r in rewrites.values()]
    out.append(
        f"Rewrite length in words: mean {mean(words):.1f}, longest {max(words)}; "
        f"{sum(1 for n in words if n > 40)} of {len(words)} exceed 40."
    )
    for title, key in (
        ("question language", lambda q: q.language),
        ("question type", lambda q: q.type),
    ):
        out += ["", f"Recall@5 by {title} (R4.1, R6.2 agent, R6.3 Gemini append; number of questions):", ""]
        by0, by1, by2 = (breakdown(questions, s, key, "recall@5") for s in (base, agent, variants["append"]))
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
            f"\n\n## R6.3/R6.4 question rewriting with Gemini, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
        print(f"\nlogged to {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
