"""
Cross-language breakdown of the R1.1 (BM25) and R4.1 (BGE-M3) runs. No new retrieval is run: this reads the
saved run files and scores them again, split by whether the question's language is available in the text it is
about.

PRE-REGISTRATION (written 15 October 2026, before the split was computed)

A question is "cross-language" if none of the languages in which its primary gold instrument is held equals
the question's language: a Spanish question about the English-only UK texts, or an English question about
the Spanish-only LOPDGDD. Every other question has a copy of its gold text in its own language
("same-language available"). Development questions only.

Reported: recall@5 and hit@5 for each retriever in each group, with the number of questions. The
cross-language group will be small, so no decision rests on it and no interval is claimed; it is a
description.

Stated expectation (can be wrong): BM25 scores 0.00 on the cross-language questions (it can only match
words, and the words differ), and BGE-M3 scores clearly above 0.

Run: python experiments/cross_language.py [--log]
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date

from law_assistant import settings
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.metrics import metric_values, read_run
from law_assistant.retrieval.runner import breakdown, evaluate, select

RUNS = settings.PROJECT_ROOT / "data" / "runs"
LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"


def main() -> int:
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    languages: dict[str, set[str]] = {}
    for c in chunks:
        languages.setdefault(c.instrument, set()).add(c.language)
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")

    def group(q) -> str:
        primaries = [g.instrument for g in q.gold if g.role == "primary"]
        own = any(q.language in languages[i] for i in primaries)
        return (
            "same-language text available" if own else "cross-language (no text in the question's language)"
        )

    runs = {"R1.1 BM25": "r1_bm25-plain.jsonl", "R4.1 BGE-M3": "r4_bge-m3.jsonl"}
    scores = {label: evaluate(questions, read_run(RUNS / file), chunks) for label, file in runs.items()}
    out = [f"### Cross-language breakdown of R1.1 and R4.1 ({len(questions)} development questions)", ""]
    for metric in ("recall@5", "hit@5"):
        out += [f"{metric} by group (R1.1 BM25, R4.1 BGE-M3; number of questions):", ""]
        tables = {label: breakdown(questions, s, group, metric) for label, s in scores.items()}
        first = next(iter(tables.values()))
        for name in sorted(first):
            cells = ", ".join(f"{t[name][0]:.2f}" for t in tables.values())
            out.append(f"- {name}: {cells} (n = {first[name][1]})")
        out.append("")
    cross = [q.id for q in questions if group(q).startswith("cross")]
    out.append(f"Cross-language development questions: {', '.join(cross) or 'none'}.")
    # which of them each retriever got right
    for label, s in scores.items():
        by_id = dict(zip((q.id for q in questions), metric_values(s, "recall@5"), strict=True))
        out.append(f"- {label} recall@5 on them: " + ", ".join(f"{i} {by_id[i]:.2f}" for i in cross))
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## Cross-language breakdown, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
        print(f"\nlogged to {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
