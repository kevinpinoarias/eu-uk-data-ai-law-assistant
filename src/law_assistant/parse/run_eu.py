"""
Parse the downloaded EU Official Journal texts, check them, and write them to data/parsed/.

    python -m law_assistant.parse.run_eu

For each act (GDPR, AI Act, Digital Omnibus on AI) and each language this writes `<key>-<lang>.jsonl`, then
prints a report: provisions by kind, structural problems, coverage of the source text, and the skeleton
differences between English and Spanish. Exit code 1 if any check fails.
"""

from __future__ import annotations

import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from law_assistant import settings
from law_assistant.model import Provision
from law_assistant.parse.checks import check_structure, compare_skeletons, coverage_ratio
from law_assistant.parse.eu_oj import parse_eu_oj, source_characters
from law_assistant.parse.store import write_jsonl

# cache key, instrument, expected totals, how many ids English and Spanish may differ by (None: not compared)
DOCUMENTS = (
    ("eu-gdpr-oj", "eu-gdpr", {"expected_articles": 99, "expected_recitals": 173, "expected_annexes": 0}, 0),
    (
        "eu-ai-act-oj",
        "eu-ai-act",
        {"expected_articles": 113, "expected_recitals": 180, "expected_annexes": 13},
        4,
    ),
    (
        "eu-ai-omnibus-oj",
        "eu-ai-omnibus",
        {"expected_articles": 4, "expected_recitals": 47, "expected_annexes": 0},
        None,
    ),
)
LANGUAGES = ("en", "es")
UNIT_WORDS = {
    "en": {"article": "Article", "annex": "ANNEX"},
    "es": {"article": "Artículo", "annex": "ANEXO"},
}
MIN_COVERAGE = 0.995


def parse_pair(raw_dir: Path, key: str, instrument: str) -> dict[str, tuple[list[Provision], int]]:
    """Parse one act in both languages: {language: (provisions, source characters)}."""
    out = {}
    for lang in LANGUAGES:
        data = (raw_dir / "eur_lex_cellar" / f"{key}-{lang}.xhtml").read_bytes()
        provisions = parse_eu_oj(data, instrument=instrument, language=lang, source_key=f"{key}-{lang}")
        out[lang] = (provisions, source_characters(data))
    return out


def run(raw_dir: Path, parsed_dir: Path, say: Callable[[str], None] = print) -> int:
    failures = 0
    for key, instrument, expected, allowed_diff in DOCUMENTS:
        parsed = parse_pair(raw_dir, key, instrument)
        for lang, (provisions, source_chars) in parsed.items():
            write_jsonl(parsed_dir / f"{key}-{lang}.jsonl", provisions)
            kinds = dict(sorted(Counter(p.kind for p in provisions).items()))
            problems = check_structure(provisions, **expected)
            ratio = coverage_ratio(provisions, source_characters=source_chars, unit_words=UNIT_WORDS[lang])
            if ratio < MIN_COVERAGE:
                problems.append(f"coverage {ratio:.3f} is below {MIN_COVERAGE}")
            say(
                f"{key}-{lang}: {len(provisions)} provisions {kinds} | coverage {ratio:.4f} "
                f"| problems {len(problems)}"
            )
            for problem in problems[:10]:
                say(f"    {problem}")
            failures += len(problems)
        if allowed_diff is not None:
            diffs = compare_skeletons(parsed["en"][0], parsed["es"][0])
            say(f"{key}: English and Spanish skeletons differ by {len(diffs)} ids (allowed {allowed_diff})")
            if len(diffs) > allowed_diff:
                failures += len(diffs) - allowed_diff
                for diff in diffs[:10]:
                    say(f"    {diff}")
    say("all checks passed" if failures == 0 else f"{failures} problem(s)")
    return 1 if failures else 0


def main() -> int:
    return run(settings.RAW_DIR, settings.PARSED_DIR)


if __name__ == "__main__":
    sys.exit(main())
