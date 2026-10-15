"""
Diagnostic (not an experiment, no decision rests on it): why did question rewriting help English questions far
more than Spanish ones (recall@5 0.51 to 0.79 against 0.55 to 0.59 in R6.2)?

Written 15 October 2026 before it was run. Development retrieval questions only (17 English, 14 Spanish), BGE-M3
over all 3,831 chunks, the question as typed (R4.1) and the question followed by the blind agent's rewrite
(R6.2). No model calls: every vector is in the saved store. Three things are measured and compared by language:
1. where the required (primary) provisions rank (share within the top 5, 10 and 30, and the median best rank);
2. what language the top-5 chunks are in (a Spanish question may be answered with English text, and the reverse);
3. which instruments the Spanish questions that still miss belong to, and what the best-ranked wrong chunks are.
Three explanations are open and each predicts something different: (a) Spanish questions already did well
before rewriting, so there was less to gain (a ceiling); (b) Spanish questions often need English-only law (the
UK Acts), so rewriting in Spanish cannot help match text in English; (c) the Spanish rewrites are no richer than
the questions (shorter, less legal vocabulary). Rewrite lengths are compared for (c).
Stated expectation (can be wrong): (b) explains most of it.

Run: python experiments/spanish_diagnostic.py [--log]
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from statistics import mean, median

from law_assistant import settings
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.relevance import matches, targets_of
from law_assistant.retrieval.bge import document_prompt, query_prompt
from law_assistant.retrieval.dense import DenseIndex
from law_assistant.retrieval.rewrite import read_rewrites
from law_assistant.retrieval.runner import select

LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"
STORE = settings.PROJECT_ROOT / "data" / "indexes" / "bge-m3"
REWRITES = settings.PROJECT_ROOT / "eval" / "rewrites" / "r6_dev.jsonl"


class NoEmbedder:
    name = "bge-m3"

    def embed_texts(self, texts):
        raise RuntimeError("a vector is missing from the saved store")


def main() -> int:
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    by_id = {c.id: c for c in chunks}
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")
    rewrites = read_rewrites(REWRITES, questions)
    index = DenseIndex(
        chunks, NoEmbedder(), STORE, name="bge-m3", document_prompt_fn=document_prompt,
        query_prompt_fn=query_prompt, persist_queries=False,
    )  # fmt: skip

    rows = []  # (question, variant, target index, best rank or None, top-5 chunks)
    for q in questions:
        for variant, text in (("question", q.text), ("question+rewrite", f"{q.text}\n{rewrites[q.text]}")):
            order = [by_id[i] for i, _ in index.scored(text, len(chunks))]
            for t in (t for t in targets_of(q) if t.grade == 2):
                best = next((r for r, c in enumerate(order, start=1) if matches(c, t.gold)), None)
                rows.append((q, variant, t, best, order[:5]))

    out = ["### Why rewriting helped English more than Spanish (31 development retrieval questions)", ""]
    out += ["Share of required (primary) provisions within the top 5 / 10 / 30, and median best rank:", ""]
    for lang in ("en", "es"):
        for variant in ("question", "question+rewrite"):
            sel = [r for r in rows if r[0].language == lang and r[1] == variant]
            ranks = [r[3] for r in sel]
            shares = [sum(1 for x in ranks if x is not None and x <= n) / len(ranks) for n in (5, 10, 30)]
            med = median(x for x in ranks if x is not None)
            out.append(
                f"- {lang}, {variant}: {len(sel)} provisions; top 5 {shares[0]:.0%}, top 10 {shares[1]:.0%}, "
                f"top 30 {shares[2]:.0%}; median best rank {med}"
            )

    out += [
        "",
        "Language of the top-5 chunks (share in the question's own language / in the other language):",
        "",
    ]
    for lang in ("en", "es"):
        for variant in ("question", "question+rewrite"):
            seen = {}
            for q, v, _t, _, top in rows:
                if q.language == lang and v == variant:
                    seen[q.id] = top
            chunks_in_top = [c for top in seen.values() for c in top]
            same = sum(c.language == lang for c in chunks_in_top) / len(chunks_in_top)
            out.append(f"- {lang}, {variant}: {same:.0%} / {1 - same:.0%} over {len(seen)} questions")

    out += [
        "",
        "Does the question need law that exists only in the other language? (primary gold provisions by instrument):",
        "",
    ]
    for lang in ("en", "es"):
        counts: dict[str, int] = {}
        for q in (q for q in questions if q.language == lang):
            for t in (t for t in targets_of(q) if t.grade == 2):
                counts[t.gold.instrument] = counts.get(t.gold.instrument, 0) + 1
        total = sum(counts.values())
        english_only = sum(n for i, n in counts.items() if i.startswith("uk-"))
        spanish_only = counts.get("es-lopdgdd", 0)
        out.append(
            f"- {lang} questions: {total} primary provisions; UK law (English only) {english_only} "
            f"({english_only / total:.0%}); LOPDGDD (Spanish only) {spanish_only} ({spanish_only / total:.0%}); "
            f"EU law (both languages) {total - english_only - spanish_only}"
        )

    out += ["", "Rewrite length in words (mean) against question length:", ""]
    for lang in ("en", "es"):
        qs = [q for q in questions if q.language == lang]
        out.append(
            f"- {lang}: question {mean(len(q.text.split()) for q in qs):.1f}, "
            f"rewrite {mean(len(rewrites[q.text].split()) for q in qs):.1f}"
        )

    out += [
        "",
        "Spanish questions with a required provision still outside the top 5 after rewriting (id, best ranks):",
        "",
    ]
    for q in (q for q in questions if q.language == "es"):
        after = [r for r in rows if r[0].id == q.id and r[1] == "question+rewrite"]
        before = [r for r in rows if r[0].id == q.id and r[1] == "question"]
        if any(r[3] is None or r[3] > 5 for r in after):
            fmt = lambda rs: [(r[2].gold.instrument + " " + "/".join(r[2].gold.unit_path), r[3]) for r in rs]  # noqa: E731
            out.append(f"- {q.id}: before {fmt(before)}; after {fmt(after)}")
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## Diagnostic: Spanish against English questions, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
