"""
Diagnostic (not an experiment, no decision rests on it): how deep in BGE-M3's ranking do the required
provisions sit? A reranker can only lift a provision that is already among the candidates it re-scores, so the
share of primary provisions found within the top 10, 20, 30, 50 and 100 bounds what a reranker (R5) could
achieve.

Written 15 October 2026 before it was run. Development questions only. For each primary gold provision of each
development retrieval question: the best rank, among all 3,831 chunks, of a chunk that satisfies it.

Run: python experiments/rank_depth.py [--log]
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date

from law_assistant import settings
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.relevance import matches, targets_of
from law_assistant.retrieval.bge import BGEEmbedder, document_prompt, query_prompt
from law_assistant.retrieval.dense import DenseIndex
from law_assistant.retrieval.runner import select

DEPTHS = (5, 10, 20, 30, 50, 100)
LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"


def main() -> int:
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    by_id = {c.id: c for c in chunks}
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")
    embedder = BGEEmbedder.load(settings.PROJECT_ROOT / "data" / "models" / "bge-m3", device="cuda")
    index = DenseIndex(
        chunks, embedder, settings.PROJECT_ROOT / "data" / "indexes" / "bge-m3", name="bge-m3",
        document_prompt_fn=document_prompt, query_prompt_fn=query_prompt,
    )  # fmt: skip
    ranks, per_question = [], {}
    for q in questions:
        order = [by_id[i] for i, _ in index.scored(q.text, len(chunks))]
        found = []
        for t in (t for t in targets_of(q) if t.grade == 2):
            best = next((r for r, c in enumerate(order, start=1) if matches(c, t.gold)), None)
            found.append(best)
            ranks.append(best)
        per_question[q.id] = found
    total = len(ranks)
    out = [
        f"### How deep BGE-M3 ranks the required provisions ({len(questions)} development questions, "
        f"{total} primary provisions)",
        "",
    ]
    for d in DEPTHS:
        share = sum(1 for r in ranks if r is not None and r <= d) / total
        whole = sum(1 for f in per_question.values() if all(r is not None and r <= d for r in f)) / len(
            per_question
        )
        out.append(
            f"- within the top {d}: {share:.0%} of provisions; all provisions of {whole:.0%} of the questions"
        )
    ordered = sorted(r for r in ranks if r is not None)
    out.append(
        f"- median best rank {ordered[len(ordered) // 2]}, worst {ordered[-1]} of {len(chunks)} chunks"
    )
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## Diagnostic: depth of the required provisions in BGE-M3's ranking, "
            f"run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
