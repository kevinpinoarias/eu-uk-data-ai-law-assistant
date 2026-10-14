"""
Parse the downloaded UK texts, check them, and write them to data/parsed/.

    python -m law_assistant.parse.run_uk

For each of the UK GDPR, the Data Protection Act 2018 and the Data (Use and Access) Act 2025 this writes
`<key>-en.jsonl` and prints a report: provisions by unit and kind, how many repealed, not-yet-in-force and
omitted elements were left out, structural problems and coverage of the source text. Article and section
numbers that are missing must be exactly those of the repealed, not-yet-in-force or omitted ones skipped.
Exit code 1 if any check fails.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from law_assistant import settings
from law_assistant.parse.checks import check_structure, coverage_ratio
from law_assistant.parse.store import write_jsonl
from law_assistant.parse.uk import parse_uk, skipped_provisions, source_characters

UNIT_WORDS = {"article": "Article", "section": "", "schedule": "Schedule", "annex": "ANNEX"}
MIN_COVERAGE = 0.995


@dataclass(frozen=True)
class Spec:
    key: str
    expected: dict[str, int]


SPECS = (
    Spec("uk-gdpr", {"expected_articles": 61, "expected_recitals": 173, "expected_annexes": 2}),
    Spec("uk-dpa-2018", {"expected_sections": 202, "expected_schedules": 21}),
    Spec("uk-duaa-2025", {"expected_sections": 134, "expected_schedules": 15}),
)


def version_of(raw_dir: Path, key: str) -> str:
    """`revised-YYYYMMDD` from the retrieval date in the cache record (the site serves the latest text)."""
    meta = json.loads((raw_dir / "legislation_gov_uk" / f"{key}.meta.json").read_text(encoding="utf-8"))
    return "revised-" + meta["retrieved_at"][:10].replace("-", "")


def run(raw_dir: Path, parsed_dir: Path, say: Callable[[str], None] = print) -> int:
    failures = 0
    for spec in SPECS:
        data = (raw_dir / "legislation_gov_uk" / f"{spec.key}.xml").read_bytes()
        provisions = parse_uk(
            data, instrument=spec.key, version=version_of(raw_dir, spec.key), source_key=spec.key
        )
        write_jsonl(parsed_dir / f"{spec.key}-en.jsonl", provisions)
        skipped = skipped_provisions(data)
        known_gaps = [*skipped["numbers"], *skipped["omitted_numbers"]]
        problems = check_structure(provisions, **spec.expected, allowed_gaps=known_gaps)
        ratio = coverage_ratio(provisions, source_characters=source_characters(data), unit_words=UNIT_WORDS)
        if ratio < MIN_COVERAGE:
            problems.append(f"coverage {ratio:.3f} is below {MIN_COVERAGE}")
        units = dict(sorted(Counter(p.unit for p in provisions).items()))
        kinds = dict(sorted(Counter(p.kind for p in provisions).items()))
        say(f"{spec.key}: {len(provisions)} provisions {units} {kinds}")
        say(
            f"    left out: {skipped['repealed']} repealed, {skipped['prospective']} not yet in force "
            f"(numbers {skipped['numbers']}), {skipped['omitted']} omitted "
            f"(numbers {skipped['omitted_numbers']}) | coverage {ratio:.4f} | problems {len(problems)}"
        )
        for problem in problems[:10]:
            say(f"    {problem}")
        failures += len(problems)
    say("all checks passed" if failures == 0 else f"{failures} problem(s)")
    return 1 if failures else 0


def main() -> int:
    return run(settings.RAW_DIR, settings.PARSED_DIR)


if __name__ == "__main__":
    sys.exit(main())
