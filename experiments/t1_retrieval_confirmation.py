"""
T1: the one confirmation on the TEST half of the retrieval decision of decision 76: BGE-M3 beats keyword search.
This is the first and only time retrieval is scored on the 31 test retrieval questions.

PRE-REGISTRATION (written 15 October 2026, before any test question has been searched; gold version 2)

Decision being confirmed (made on the development half, where recall@5 was 0.53 for BGE-M3 and 0.24 for BM25,
paired +0.288, interval +0.086 to +0.484): the retriever of the project is BGE-M3 over all 3,831 chunks, the
question as typed, the chunk text with its context line, and BM25 (plain, no accent folding) is the baseline.
Variants run, exactly the two above, no tuning of any kind: BM25 and BGE-M3. Data: the 31 retrieval questions of
the test half of gold version 2 (the first read of those questions by any retrieval experiment).
Primary metric recall@5, also MRR, nDCG@10, hit@5, recall@10; 95 % bootstrap intervals (10,000 resamples, seed 0);
paired bootstrap of BGE-M3 against BM25 on recall@5. Breakdowns by question type and language.
Confirmation rule: the decision is confirmed if the lower end of the paired interval is above 0. If it is not, the
result is reported as it is: the decision stays (it was made on the development half and rested on a detectable
gain there) but its generality on new questions is recorded as not shown. Either way the numbers go in the
README.
Stated expectation (can be wrong): recall@5 lower than on the development half because the development half
was used to look at failures (BGE-M3 about 0.40 to 0.55; BM25 about 0.15 to 0.30); the paired lower bound above 0.
Guard: this script refuses to run a second time (it looks for its own section in docs/EXPERIMENTS.md); a deliberate
second read needs --second-read and is logged as one.

Run: python experiments/t1_retrieval_confirmation.py --log   (needs the BGE-M3 model; no key, no quota)
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date

from law_assistant import settings
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.metrics import metric_values, paired_bootstrap
from law_assistant.retrieval.bge import BGEEmbedder, document_prompt, query_prompt
from law_assistant.retrieval.bm25 import BM25Index
from law_assistant.retrieval.dense import DenseIndex
from law_assistant.retrieval.report import format_table, summarise_with_ci
from law_assistant.retrieval.runner import breakdown, evaluate, run_retriever, select

LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"
MARKER = "## T1 test-half confirmation of the retriever"
BGE_DIR = settings.PROJECT_ROOT / "data" / "models" / "bge-m3"
STORE = settings.PROJECT_ROOT / "data" / "indexes" / "bge-m3"


def main() -> int:
    import torch

    if MARKER in LOG.read_text(encoding="utf-8") and "--second-read" not in sys.argv:
        print(
            "the test half has already been read for this decision; use --second-read to read it again (logged)"
        )
        return 2
    device = "cuda" if torch.cuda.is_available() else "cpu"
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "test")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")
    index = DenseIndex(
        chunks, BGEEmbedder.load(BGE_DIR, device=device, max_length=1024), STORE, name="bge-m3",
        document_prompt_fn=document_prompt, query_prompt_fn=query_prompt, persist_queries=False,
    )  # fmt: skip
    bm25 = evaluate(questions, run_retriever(BM25Index(chunks, name="bm25-plain"), questions, k=10), chunks)
    bge = evaluate(questions, run_retriever(index, questions, k=10), chunks)
    paired = paired_bootstrap(metric_values(bm25, "recall@5"), metric_values(bge, "recall@5"))
    results = {"R1.1 BM25 plain": summarise_with_ci(bm25), "R4.1 BGE-M3": summarise_with_ci(bge)}
    second = " (a SECOND read of the test half)" if "--second-read" in sys.argv else ""
    out = [
        f"### T1 retrieval on the TEST half ({len(questions)} retrieval questions, gold version "
        f"{manifest['version']}){second}",
        "",
        format_table(results),
        "",
        f"BGE-M3 against BM25, recall@5: difference {paired.difference:+.3f}, 95 % interval "
        f"{paired.low:+.3f} to {paired.high:+.3f}; share of resamples in which BGE-M3 is not better "
        f"{paired.p_not_better:.2f}. Confirmed by the pre-registered rule (lower bound above 0): "
        f"{'yes' if paired.low > 0 else 'NO'}.",
    ]
    for title, key in (("question type", lambda q: q.type), ("question language", lambda q: q.language)):
        out += ["", f"Recall@5 by {title} (BM25, BGE-M3; number of questions):", ""]
        a, b = (breakdown(questions, s, key, "recall@5") for s in (bm25, bge))
        out += [f"- {name}: {a[name][0]:.2f}, {b[name][0]:.2f} (n = {a[name][1]})" for name in sorted(a)]
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n{MARKER}, run {date.today().isoformat()} "
            f"(commit {commit}; gold version {manifest['version']}, fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
