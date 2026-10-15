"""
R6 (part 4): do filters help? Search only the chunks of the jurisdictions a question can be about, and only the
question's language where a text exists in both. No language-model calls: the filters are small rules and the
search runs on the local BGE-M3 model, so this costs no quota.

PRE-REGISTRATION (written 15 October 2026 before any filtered ranking has been scored)

First stage BGE-M3 exactly as in R4.1 (all 3,831 chunks, the question as typed); a filter removes chunks from the
whole ranking before the top results are taken. Variants (all four counted in the experiment tally):
  F1  jurisdiction filter from the GOLD jurisdictions of each question: an upper bound, since a real system has
      to infer them.
  F2  jurisdiction filter from the jurisdictions the question reader finds in the question text
      (answer/understand.py: right on 35 of 40 development questions).
  F3  language filter: where a text exists in both languages keep the question's language (the language is
      detected by the same reader; 40 of 40 right).
  F4  F2 and F3 together.
Rules: a named jurisdiction restricts the search to it, except that Spain also searches EU law; naming nothing
restricts nothing.
Data: the 3,831 chunks and the 31 development retrieval questions of the frozen gold set. Test half untouched.

Primary metric recall@5; also MRR, nDCG@10, hit@5, recall@10; 95 % bootstrap intervals (10,000 resamples, seed
0). Paired bootstrap on recall@5 against R4.1. Also reported: how many questions each filter changes the
ranking of, and the breakdown by question language and by jurisdiction group.

Decision rule: a filter that works from the question text (F2, F3 or F4) is adopted if the lower end of its
paired interval against R4.1 on recall@5 is above 0; among those the highest recall@5 wins, a simpler filter
winning ties within 0.02. F1 is an upper bound only and is never adopted.
Stated expectation (can be wrong): F1 raises recall@5 by a few points (it removes UK/EU confusion and
other-language copies); F2 gets part of that; F3 changes little (collapsing copies changed nothing in R10);
no filter has a lower paired bound above 0 with 31 questions.

Run: python experiments/r6_filters.py [--log]
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date

from law_assistant import settings
from law_assistant.answer.understand import understand
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.metrics import metric_values, paired_bootstrap, write_run
from law_assistant.retrieval.bge import BGEEmbedder, document_prompt, query_prompt
from law_assistant.retrieval.dense import DenseIndex
from law_assistant.retrieval.filters import FilteredRetriever, allowed_jurisdictions, language_filter
from law_assistant.retrieval.report import format_table, summarise_with_ci
from law_assistant.retrieval.runner import breakdown, evaluate, run_retriever, select

K = 10
BGE_DIR = settings.PROJECT_ROOT / "data" / "models" / "bge-m3"
STORE = settings.PROJECT_ROOT / "data" / "indexes" / "bge-m3"
RUNS = settings.PROJECT_ROOT / "data" / "runs"
LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"


def main() -> int:
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")
    gold_juris = {q.text: q.jurisdictions for q in questions}
    index = DenseIndex(
        chunks, BGEEmbedder.load(BGE_DIR, device=device, max_length=1024), STORE, name="bge-m3",
        document_prompt_fn=document_prompt, query_prompt_fn=query_prompt,
    )  # fmt: skip
    keep_language = language_filter(chunks)

    def by_gold(query, chunk):
        allowed = allowed_jurisdictions(gold_juris[query])
        return allowed is None or chunk.jurisdiction in allowed

    def by_text(query, chunk):
        allowed = allowed_jurisdictions(understand(query).jurisdictions)
        return allowed is None or chunk.jurisdiction in allowed

    def by_language(query, chunk):
        return keep_language(understand(query).language, chunk)

    def both(query, chunk):
        return by_text(query, chunk) and by_language(query, chunk)

    retrievers = {
        "F1 gold jurisdictions (upper bound)": FilteredRetriever(index, chunks, by_gold, name="F1"),
        "F2 jurisdictions from the text": FilteredRetriever(index, chunks, by_text, name="F2"),
        "F3 language": FilteredRetriever(index, chunks, by_language, name="F3"),
        "F4 jurisdictions and language": FilteredRetriever(index, chunks, both, name="F4"),
    }
    base_run = run_retriever(index, questions, k=K)
    base = evaluate(questions, base_run, chunks)
    results = {"R4.1 BGE-M3": summarise_with_ci(base)}
    scored, changed = {}, {}
    for name, retriever in retrievers.items():
        run = run_retriever(retriever, questions, k=K)
        write_run(RUNS / f"r6_filter_{name.split()[0].lower()}.jsonl", run)
        scored[name] = evaluate(questions, run, chunks)
        changed[name] = sum(run[q.id][:5] != base_run[q.id][:5] for q in questions)
        results[name] = summarise_with_ci(scored[name])

    out = [
        f"### R6 filters on the development questions ({len(questions)} retrieval questions)",
        "",
        format_table(results),
        "",
    ]
    for name in retrievers:
        p = paired_bootstrap(metric_values(base, "recall@5"), metric_values(scored[name], "recall@5"))
        out.append(
            f"{name} against R4.1, recall@5: difference {p.difference:+.3f}, "
            f"95 % interval {p.low:+.3f} to {p.high:+.3f}; top-5 changed for {changed[name]} of {len(questions)} questions."
        )

    def juris_group(q):
        return "+".join(q.jurisdictions) or "none"

    for title, key in (("question language", lambda q: q.language), ("jurisdiction group", juris_group)):
        out += ["", f"Recall@5 by {title} (R4.1, F1, F2, F3, F4; number of questions):", ""]
        cols = [base, *scored.values()]
        by = [breakdown(questions, s, key, "recall@5") for s in cols]
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
            f"\n\n## R6 filters, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
