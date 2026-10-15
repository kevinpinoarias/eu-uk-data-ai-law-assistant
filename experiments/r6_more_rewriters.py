"""
R6 (part 3): why did the cheap in-pipeline rewriter (R6.3, gemini-3.1-flash-lite) fall short of the agent's
rewrites (R6.2)? Two explanations are open: a more capable model knows more law, and the prompt asks for a
literal restatement while the agent's rewrites also named the legal terms the provision would contain.

PRE-REGISTRATION (written 15 October 2026, after R6.3/R6.4 were scored and the rewrites compared by eye; the
expanding prompt was designed AFTER seeing those development results, so it is a tuned variant: only the test
half can show whether it generalises)

Variants (all three counted in the experiment tally), first stage BGE-M3 as in R4.1, question followed by the
rewrite (append), temperature 0, at most 1,024 output tokens (a model that reasons before it answers spends
part of the limit on reasoning), the key from .env:
  R6.5  gemini-3.5-flash-lite with the plain instructions of R6.3.
  R6.6  gemini-3.1-flash-lite with the expanding instructions (same rules plus: after the restatement,
        list the specific legal terms and concepts the provision itself would contain; up to 60 words).
  R6.7  gemini-3.5-flash-lite with the expanding instructions.
AMENDMENT (same day, before any variant below was scored): the first draft named gemini-3.5-flash, the larger
model, for R6.5 and R6.7. Its free tier allows 20 requests a day, which was used up after 22 of the 62 needed
calls (nothing had been scored; those answers are ignored), and gemini-2.5-flash is closed to new accounts. A
larger Flash model therefore cannot be tested without billing; the model comparison here is between two
generations of Flash-Lite instead, and the larger-model question stays open until billing exists.
Data: the 3,831 chunks and the 31 development retrieval questions of the frozen gold set. Test half untouched.

Primary metric recall@5; also MRR, nDCG@10, hit@5, recall@10; 95 % bootstrap intervals (10,000 resamples, seed
0). Paired bootstrap on recall@5 against R4.1. Reported for cost: seconds per call and tokens per question.

Decision rule: a variant qualifies as the pipeline's rewriter if the lower end of its paired interval against
R4.1 on recall@5 is above 0. Among qualifying variants the highest recall@5 wins, but if the best is within
0.02 of a cheaper model's, the cheaper model is preferred. If none qualifies, the in-pipeline rewrite step
is not adopted and the agent's 0.70 remains an upper bound shown with a stronger writer, not the system's
score.
Whatever is chosen is confirmed once on the test half. No further prompt or model tuning on the development
half after this run.

Stated expectation (can be wrong): the newer Flash-Lite with the plain prompt (R6.5) and the older one with
the expanding prompt (R6.6) each improve on R6.3 (0.56), the combination (R6.7) is best, and at least R6.7
has a lower paired bound above 0. I put less weight on R6.5: a newer small model may know little more law.

Run: python experiments/r6_more_rewriters.py [--log]   (needs GEMINI_API_KEY in .env)
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from statistics import mean

from law_assistant import settings
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.metrics import metric_values, paired_bootstrap, write_run
from law_assistant.llm.gemini import CachedGenerator, GeminiGenerator
from law_assistant.retrieval.bge import BGEEmbedder, document_prompt, query_prompt
from law_assistant.retrieval.dense import DenseIndex
from law_assistant.retrieval.report import format_table, summarise_with_ci
from law_assistant.retrieval.rewrite import RewriteRetriever
from law_assistant.retrieval.rewriter import EXPANDING_INSTRUCTIONS, INSTRUCTIONS, LLMRewriter
from law_assistant.retrieval.runner import breakdown, evaluate, run_retriever, select

K = 10
BGE_DIR = settings.PROJECT_ROOT / "data" / "models" / "bge-m3"
STORE = settings.PROJECT_ROOT / "data" / "indexes" / "bge-m3"
REWRITES = settings.PROJECT_ROOT / "eval" / "rewrites"
CACHE = settings.PROJECT_ROOT / "data" / "llm_cache" / "rewrites.jsonl"
RUNS = settings.PROJECT_ROOT / "data" / "runs"
LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"
VARIANTS = (
    ("R6.5", "gemini-3.5-flash-lite", INSTRUCTIONS, "plain"),
    ("R6.6", "gemini-3.1-flash-lite", EXPANDING_INSTRUCTIONS, "expanding"),
    ("R6.7", "gemini-3.5-flash-lite", EXPANDING_INSTRUCTIONS, "expanding"),
)


def main() -> int:
    import torch

    settings.load_env_file()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")
    first = DenseIndex(
        chunks, BGEEmbedder.load(BGE_DIR, device=device, max_length=1024), STORE, name="bge-m3",
        document_prompt_fn=document_prompt, query_prompt_fn=query_prompt,
    )  # fmt: skip
    base = evaluate(questions, run_retriever(first, questions, k=K), chunks)
    results = {"R4.1 BGE-M3": summarise_with_ci(base)}
    scored, costs, lengths = {}, {}, {}
    for tag, model, instructions, label in VARIANTS:
        generator = GeminiGenerator.from_env(model=model)
        rewriter = LLMRewriter(
            CachedGenerator(generator, CACHE), instructions=instructions, max_output_tokens=1024
        )
        rewrites = rewriter.rewrite_all([q.text for q in questions])
        path = REWRITES / f"{tag.lower().replace('.', '_')}_dev.jsonl"
        with path.open("w", encoding="utf-8", newline="\n") as f:
            for q in questions:
                row = {"id": q.id, "model": model, "prompt": label, "rewrite": rewrites[q.text]}
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        run = run_retriever(RewriteRetriever(first, rewrites, mode="append"), questions, k=K)
        write_run(RUNS / f"{tag.lower().replace('.', '_')}.jsonl", run)
        scored[tag] = evaluate(questions, run, chunks)
        name = f"{tag} {model}, {label}"
        results[name] = summarise_with_ci(scored[tag])
        calls = generator.calls
        costs[tag] = (
            f"{mean(c.seconds for c in calls):.2f} s per call, "
            f"{sum(c.prompt_tokens for c in calls) / len(calls):.0f} "
            f"prompt and {sum(c.output_tokens for c in calls) / len(calls):.0f} output tokens per question "
            f"({len(calls)} calls)"
            if calls
            else "all answers from the cache"
        )
        lengths[tag] = [len(r.split()) for r in rewrites.values()]

    out = [
        "### R6.5 to R6.7 other rewriters on the development questions "
        f"({len(questions)} retrieval questions)",
        "",
        format_table(results),
        "",
    ]
    for tag, model, _, label in VARIANTS:
        p = paired_bootstrap(metric_values(base, "recall@5"), metric_values(scored[tag], "recall@5"))
        out.append(
            f"{tag} ({model}, {label}) against R4.1, recall@5: difference {p.difference:+.3f}, "
            f"95 % interval {p.low:+.3f} to {p.high:+.3f}; share of resamples in which the rewrite is not "
            f"better {p.p_not_better:.2f}."
        )
    out.append("")
    for tag, *_ in VARIANTS:
        out.append(
            f"Cost of {tag}: {costs[tag]}; rewrite length mean {mean(lengths[tag]):.1f} words, "
            f"longest {max(lengths[tag])}."
        )
    out += ["", "Recall@5 by question language (R4.1, then R6.5, R6.6, R6.7; number of questions):", ""]
    cols = [base, *(scored[v[0]] for v in VARIANTS)]
    by = [breakdown(questions, s, lambda q: q.language, "recall@5") for s in cols]
    out += [
        f"- {name}: " + ", ".join(f"{b[name][0]:.2f}" for b in by) + f" (n = {by[0][name][1]})"
        for name in sorted(by[0])
    ]
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## R6.5 to R6.7 other rewriters, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
        print(f"\nlogged to {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
