"""
P4.1: how well do the plain rules of answer-layer step 1 (src/law_assistant/answer/understand.py) read a
question's language, the jurisdictions it names and a date it states? Measured against the gold labels.

PRE-REGISTRATION (written 15 October 2026 before the first run on any questions; the rules were written
knowing the development labels' general shape (EU/UK/ES as place names), so the development numbers are
what I tuned towards: the test half is read once, at the final confirmation)

Data: the 40 development questions (all types), then once the 40 test questions when the whole answer layer is
confirmed. Measures:
- language: share of questions whose detected language equals the gold language;
- jurisdictions: share with exactly the gold set; share where every gold jurisdiction is found (recall); share
  where something extra is named (precision loss). Refusal questions with no jurisdiction are counted;
- as-of: for the questions whose text states a date, share where the detected date equals the gold as_of (a
  gold as_of equal to the corpus snapshot date, 2026-10-14, is a default rather than a stated date and is
  not counted).
No decision rule: this step feeds filters and the as-of handling; the numbers say how far to trust it.
Anything below 0.9 on language is a bug to fix before the answer layer is built on it.
Stated expectation (can be wrong): language 1.00, jurisdictions exact about 0.75 (the gold labels count
Spanish law and EU law together for Spanish questions that the text only partly names), as-of correct on the
few questions that state a date.

Run: python experiments/p4_understand.py [--log] [--split dev|test]
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date

from law_assistant import settings
from law_assistant.answer.understand import understand
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold

LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"
SNAPSHOT = "2026-10-14"


def main() -> int:
    split = sys.argv[sys.argv.index("--split") + 1] if "--split" in sys.argv else "dev"
    questions = [q for q in read_gold(settings.GOLD_DIR / "questions.jsonl") if q.split == split]
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")
    rows = [(q, understand(q.text)) for q in questions]
    n = len(rows)
    language = sum(u.language == q.language for q, u in rows)
    exact = sum(set(u.jurisdictions) == set(q.jurisdictions) for q, u in rows)
    recall = sum(set(q.jurisdictions) <= set(u.jurisdictions) for q, u in rows)
    extra = sum(bool(set(u.jurisdictions) - set(q.jurisdictions)) for q, u in rows)
    dated = [(q, u) for q, u in rows if q.as_of and q.as_of != SNAPSHOT]
    dated_ok = sum(u.as_of == q.as_of for q, u in dated)
    false_dates = sum(1 for q, u in rows if u.as_of and u.as_of != q.as_of)
    out = [
        f"### P4.1 reading the question: language, jurisdictions, date ({split} half, {n} questions)",
        "",
        f"- language: {language}/{n} correct",
        f"- jurisdictions: exactly the gold set {exact}/{n}; every gold jurisdiction found {recall}/{n}; "
        f"something extra named {extra}/{n}",
        f"- as-of: {dated_ok}/{len(dated)} of the questions with a stated date read correctly; "
        f"{false_dates} questions got a date the gold does not have",
        "",
        "Misses (id, what was detected, gold):",
        "",
    ]
    for q, u in rows:
        problems = []
        if u.language != q.language:
            problems.append(f"language {u.language} (gold {q.language})")
        if set(u.jurisdictions) != set(q.jurisdictions):
            problems.append(f"jurisdictions {list(u.jurisdictions)} (gold {list(q.jurisdictions)})")
        if u.as_of and u.as_of != q.as_of:
            problems.append(f"date {u.as_of} (gold {q.as_of})")
        if problems:
            out.append(f"- {q.id}: " + "; ".join(problems))
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## P4.1 reading the question, {split} half, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
