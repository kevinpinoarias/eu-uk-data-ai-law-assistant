"""
Parse the downloaded BOE text of the LOPDGDD, check it, and write it to data/parsed/.

    python -m law_assistant.parse.run_boe

Writes `es-lopdgdd-es.jsonl` (the text as in force on the retrieval date) and prints a report: provisions by
unit and kind, structural problems and coverage of the source text. Exit code 1 if any check fails.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from collections.abc import Callable
from pathlib import Path

from law_assistant import settings
from law_assistant.parse.boe import parse_boe, source_characters
from law_assistant.parse.checks import check_structure, coverage_ratio
from law_assistant.parse.store import write_jsonl

KEY = "es-lopdgdd-texto"
INSTRUMENT = "es-lopdgdd"
EXPECTED = {
    "expected_articles": 97,
    "expected_dispositions": 46,
}  # articles 1 to 97 (plus 53 bis); 23 + 6 + 1 + 16
UNIT_WORDS = {"article": "Artículo", "disposition": "Disposición"}
MIN_COVERAGE = 0.995


def retrieval_date(raw_dir: Path) -> str:
    """The date the text was fetched (YYYY-MM-DD): the text is parsed as in force on that day."""
    meta = json.loads((raw_dir / "boe_es" / f"{KEY}.meta.json").read_text(encoding="utf-8"))
    return meta["retrieved_at"][:10]


def run(raw_dir: Path, parsed_dir: Path, say: Callable[[str], None] = print) -> int:
    as_of = retrieval_date(raw_dir)
    data = (raw_dir / "boe_es" / f"{KEY}.xml").read_bytes()
    provisions = parse_boe(
        data, instrument=INSTRUMENT, version=f"as-of-{as_of.replace('-', '')}", as_of=as_of, source_key=KEY
    )
    write_jsonl(parsed_dir / "es-lopdgdd-es.jsonl", provisions)
    problems = check_structure(provisions, **EXPECTED)
    ratio = coverage_ratio(
        provisions, source_characters=source_characters(data, as_of), unit_words=UNIT_WORDS
    )
    if ratio < MIN_COVERAGE:
        problems.append(f"coverage {ratio:.3f} is below {MIN_COVERAGE}")
    units = dict(sorted(Counter(p.unit for p in provisions).items()))
    kinds = dict(sorted(Counter(p.kind for p in provisions).items()))
    say(f"{INSTRUMENT} as in force on {as_of}: {len(provisions)} provisions {units} {kinds}")
    say(f"    coverage {ratio:.4f} | problems {len(problems)}")
    for problem in problems[:10]:
        say(f"    {problem}")
    say("all checks passed" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


def main() -> int:
    return run(settings.RAW_DIR, settings.PARSED_DIR)


if __name__ == "__main__":
    sys.exit(main())
