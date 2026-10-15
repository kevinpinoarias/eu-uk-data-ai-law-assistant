"""
Diagnostic (not an experiment, no decision rests on it): why did the reranker (R5.1) not beat BGE-M3 alone?
Two explanations are open: (a) the 512-token limit cuts the end of long chunks, so the reranker never sees the
part that answers; (b) the reranker prefers other relevant-looking articles to the ones the gold set requires.

Written 15 October 2026 before it was run. Development questions only. For each primary gold provision of each
development retrieval question that BGE-M3 ranks within its top 30: BGE-M3's rank, the reranker's rank among
those 30, and whether the (question, chunk) pair is longer than 512 tokens. Reported: how many such provisions
moved into the top 5, out of the top 5, or stayed on the same side, split by cut and not cut; and the median
rank change. A split that shows the reranker doing worse mainly on cut pairs would support (a); no such
difference would point to (b). Any follow-up variant (for example a longer limit) needs its own
pre-registration.

Run: python experiments/rerank_diagnostic.py [--log]
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from statistics import median

from law_assistant import settings
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.relevance import matches, targets_of
from law_assistant.retrieval.bge import BGEEmbedder, document_prompt, query_prompt
from law_assistant.retrieval.dense import DenseIndex
from law_assistant.retrieval.rerank import Reranker
from law_assistant.retrieval.runner import select

DEPTH = 30
MAX_LENGTH = 512
LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"


def main() -> int:
    import torch
    from transformers import AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    models = settings.PROJECT_ROOT / "data" / "models"
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    by_id = {c.id: c for c in chunks}
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")
    index = DenseIndex(
        chunks, BGEEmbedder.load(models / "bge-m3", device=device, max_length=1024),
        settings.PROJECT_ROOT / "data" / "indexes" / "bge-m3", name="bge-m3",
        document_prompt_fn=document_prompt, query_prompt_fn=query_prompt,
    )  # fmt: skip
    reranker = Reranker.load(models / "bge-reranker-v2-m3", device=device, max_length=MAX_LENGTH)
    tokenizer = AutoTokenizer.from_pretrained(str(models / "bge-reranker-v2-m3"))

    rows = []  # (cut, bge_rank, rerank_rank)
    for q in questions:
        head = [by_id[i] for i in index.search(q.text, DEPTH)]
        texts = [document_prompt(c) for c in head]
        scores = reranker.score_pairs(q.text, texts)
        order = sorted(range(len(head)), key=lambda i: -scores[i])
        rerank_rank = {i: place for place, i in enumerate(order, start=1)}
        for t in (t for t in targets_of(q) if t.grade == 2):
            hit = next((i for i, c in enumerate(head) if matches(c, t.gold)), None)
            if hit is None:
                continue
            cut = len(tokenizer(q.text, texts[hit])["input_ids"]) > MAX_LENGTH
            rows.append((cut, hit + 1, rerank_rank[hit]))

    def summary(label: str, subset) -> str:
        n = len(subset)
        if n == 0:
            return f"- {label}: none"
        up = sum(1 for _, b, r in subset if b > 5 >= r)
        down = sum(1 for _, b, r in subset if r > 5 >= b)
        in_before = sum(1 for _, b, _ in subset if b <= 5)
        in_after = sum(1 for _, _, r in subset if r <= 5)
        change = median(b - r for _, b, r in subset)
        return (
            f"- {label}: {n} provisions; in the top 5 before {in_before}, after {in_after} "
            f"(moved in {up}, moved out {down}); median rank gain {change:+.1f}"
        )

    out = [
        f"### Why R5.1 did not beat BGE-M3 ({len(questions)} development questions; the primary provisions "
        f"BGE-M3 ranks within its top {DEPTH}: {len(rows)})",
        "",
        summary("all", rows),
        summary(f"pair cut at {MAX_LENGTH} tokens", [r for r in rows if r[0]]),
        summary("pair not cut", [r for r in rows if not r[0]]),
    ]
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## Diagnostic: why the reranker did not help, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
