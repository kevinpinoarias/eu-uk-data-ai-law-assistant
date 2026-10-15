"""
P4.3: can a language model pick the right row of the facts table (or none)? The embedding lookup of P4.2
found the right row for 3 of the 4 development table questions (it chose the breach deadline for a question
about the deadline to answer a rights request), so a second way of picking is tried.

PRE-REGISTRATION (written 15 October 2026 after P4.2 was scored; this variant exists because of that miss,
so it is a tuned variant and the test half has to confirm it)

Variant (counted in the experiment tally): gemini-3.1-flash-lite is given the 19 fact keys with their
jurisdictions and English subjects, the question and the jurisdictions the rules found in it, temperature 0,
and answers with one key or null (JSON).
Data: all 40 development questions. For the 4 table questions the pick must equal the gold table_key; for the
other 36 the pick must be null (a figure given for a question that is not a figure question is a wrong
answer, and retrieval would have been the right route).
Measures: correct picks on table questions (of 4), wrong picks and false picks on the others (of 36).
Decision rule: the model picker replaces the embedding lookup if it gets all 4 table questions right with
at most 1 false pick on the other 36. Otherwise the embedding lookup with the P4.2 threshold stays, with its
known miss recorded.
Stated expectation (can be wrong): 4 of 4 right, 0 or 1 false picks.

Run: python experiments/p4_fact_picker.py [--log]   (needs GEMINI_API_KEY in .env)
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date

from law_assistant import settings
from law_assistant.answer.facts_lookup import LLMFactPicker
from law_assistant.answer.understand import understand
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.facts.table import read_facts
from law_assistant.llm.gemini import CachedGenerator, GeminiGenerator

LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"
CACHE = settings.PROJECT_ROOT / "data" / "llm_cache" / "fact_picker.jsonl"


def main() -> int:
    settings.load_env_file()
    questions = [q for q in read_gold(settings.GOLD_DIR / "questions.jsonl") if q.split == "dev"]
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")
    facts = read_facts(settings.FACTS_DIR / "legal_facts.jsonl")
    generator = GeminiGenerator.from_env()
    picker = LLMFactPicker(facts, CachedGenerator(generator, CACHE))
    right = wrong = false_picks = 0
    lines = []
    table = [q for q in questions if q.route == "table"]
    for q in questions:
        fact = picker.pick(q.text, understand(q.text).jurisdictions)
        key = fact.key if fact else None
        if q.route == "table":
            if key == q.table_key:
                right += 1
            else:
                wrong += 1
                lines.append(f"- {q.id}: picked {key}, gold {q.table_key}: {q.text}")
        elif key is not None:
            false_picks += 1
            lines.append(f"- {q.id} ({q.route}): picked {key} for a question that is not a figure question")
    out = [
        f"### P4.3 the model picks the table row ({len(questions)} development questions)",
        "",
        f"- table questions right: {right}/{len(table)}; wrong row: {wrong}",
        f"- false picks on the {len(questions) - len(table)} other questions: {false_picks}",
        *([""] + ["Misses:", ""] + lines if lines else []),
    ]
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## P4.3 model-picked table row, dev half, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
