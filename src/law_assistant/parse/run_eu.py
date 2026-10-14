"""
Parse the downloaded EU texts, check them, and write them to data/parsed/.

    python -m law_assistant.parse.run_eu

For each text (the GDPR and AI Act as published and as consolidated, and the Digital Omnibus on AI) and each
language this writes `<key>-<lang>.jsonl`, then prints a report: provisions by kind, structural problems,
coverage of the source text, the skeleton differences between English and Spanish, and for the consolidated
texts how they differ from the Official Journal text. Exit code 1 if any check fails.
"""

from __future__ import annotations

import sys
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from law_assistant import settings
from law_assistant.model import Provision
from law_assistant.parse import eu_consolidated, eu_oj
from law_assistant.parse.checks import check_structure, compare_skeletons, compare_texts, coverage_ratio
from law_assistant.parse.store import write_jsonl

LANGUAGES = ("en", "es")
UNIT_WORDS = {
    "en": {"article": "Article", "annex": "ANNEX"},
    "es": {"article": "Artículo", "annex": "ANEXO"},
}
MIN_COVERAGE = 0.995


@dataclass(frozen=True)
class Spec:
    key: str  # cache key without the language suffix
    instrument: str
    version: str
    kind: str  # "oj" (Official Journal text) or "consolidated"
    expected: dict[str, int]  # known totals for check_structure
    allowed_diff: int | None  # ids English and Spanish may differ by, after normalising inserted labels
    against: str | None = None  # key of the Official Journal text a consolidated text is compared with
    max_changed_vs_oj: int = 0  # wording changes allowed against it (amendments and corrigenda)
    max_only_sides_vs_oj: int = 0  # ids present on one side only that are allowed against it


SPECS = (
    Spec(
        "eu-gdpr-oj",
        "eu-gdpr",
        "oj",
        "oj",
        {"expected_articles": 99, "expected_recitals": 173, "expected_annexes": 0},
        0,
    ),
    Spec(
        "eu-gdpr-consolidated",
        "eu-gdpr",
        "consolidated-20160504",
        "consolidated",
        {"expected_articles": 99, "expected_recitals": 0, "expected_annexes": 0},
        0,
        against="eu-gdpr-oj",
        max_changed_vs_oj=45,  # the 2018 corrigendum: 16 changes in English, 38 in Spanish
    ),
    Spec(
        "eu-ai-act-oj",
        "eu-ai-act",
        "oj",
        "oj",
        {"expected_articles": 113, "expected_recitals": 180, "expected_annexes": 13},
        4,
    ),
    Spec(
        "eu-ai-act-consolidated-20260727",
        "eu-ai-act",
        "consolidated-20260727",
        "consolidated",
        {"expected_articles": 113, "expected_recitals": 0, "expected_annexes": 14},
        12,  # new Annex XIV: Spanish labels single items that English leaves unlabelled
        against="eu-ai-act-oj",
        max_changed_vs_oj=-1,  # many: the Omnibus amends the AI Act (reported, not limited)
        max_only_sides_vs_oj=-1,
    ),
    Spec(
        "eu-ai-omnibus-oj",
        "eu-ai-omnibus",
        "oj",
        "oj",
        {"expected_articles": 4, "expected_recitals": 47, "expected_annexes": 0},
        None,
    ),
)


@dataclass
class Parsed:
    provisions: list[Provision]
    source_chars: int = 0
    notes: list[str] = field(default_factory=list)


def parse_spec(raw_dir: Path, spec: Spec) -> dict[str, Parsed]:
    """Parse one text in both languages."""
    out = {}
    for lang in LANGUAGES:
        data = (raw_dir / "eur_lex_cellar" / f"{spec.key}-{lang}.xhtml").read_bytes()
        source_key = f"{spec.key}-{lang}"
        if spec.kind == "oj":
            provisions = eu_oj.parse_eu_oj(
                data, instrument=spec.instrument, language=lang, version=spec.version, source_key=source_key
            )
            out[lang] = Parsed(provisions, eu_oj.source_characters(data))
        else:
            provisions = eu_consolidated.parse_eu_consolidated(
                data, instrument=spec.instrument, language=lang, version=spec.version, source_key=source_key
            )
            out[lang] = Parsed(provisions, eu_consolidated.source_characters(data))
    return out


def run(raw_dir: Path, parsed_dir: Path, say: Callable[[str], None] = print) -> int:
    failures = 0
    results: dict[str, dict[str, Parsed]] = {}
    for spec in SPECS:
        parsed = results[spec.key] = parse_spec(raw_dir, spec)
        for lang, doc in parsed.items():
            write_jsonl(parsed_dir / f"{spec.key}-{lang}.jsonl", doc.provisions)
            kinds = dict(sorted(Counter(p.kind for p in doc.provisions).items()))
            problems = check_structure(doc.provisions, **spec.expected)
            ratio = coverage_ratio(
                doc.provisions, source_characters=doc.source_chars, unit_words=UNIT_WORDS[lang]
            )
            if ratio < MIN_COVERAGE:
                problems.append(f"coverage {ratio:.3f} is below {MIN_COVERAGE}")
            say(
                f"{spec.key}-{lang}: {len(doc.provisions)} provisions {kinds} | coverage {ratio:.4f} "
                f"| problems {len(problems)}"
            )
            for problem in problems[:10]:
                say(f"    {problem}")
            failures += len(problems)
        if spec.allowed_diff is not None:
            diffs = compare_skeletons(
                parsed["en"].provisions, parsed["es"].provisions, normalise_inserted_labels=True
            )
            say(
                f"{spec.key}: English and Spanish skeletons differ by {len(diffs)} ids "
                f"(allowed {spec.allowed_diff})"
            )
            if len(diffs) > spec.allowed_diff:
                failures += len(diffs) - spec.allowed_diff
                for diff in diffs[:10]:
                    say(f"    {diff}")
        if spec.against:
            for lang in LANGUAGES:
                oj = [p for p in results[spec.against][lang].provisions if p.unit != "recital"]
                diff = compare_texts(oj, parsed[lang].provisions)
                sides = len(diff["only_first"]) + len(diff["only_second"])
                say(
                    f"{spec.key}-{lang} against the Official Journal text: "
                    f"{len(diff['changed'])} wording changes, "
                    f"{sides} ids on one side only"
                )
                if spec.max_changed_vs_oj >= 0 and len(diff["changed"]) > spec.max_changed_vs_oj:
                    failures += 1
                    say(f"    more wording changes than the {spec.max_changed_vs_oj} expected")
                if spec.max_only_sides_vs_oj >= 0 and sides > spec.max_only_sides_vs_oj:
                    failures += 1
                    say(f"    ids on one side only: {(diff['only_first'] + diff['only_second'])[:6]}")
    say("all checks passed" if failures == 0 else f"{failures} problem(s)")
    return 1 if failures else 0


def main() -> int:
    return run(settings.RAW_DIR, settings.PARSED_DIR)


if __name__ == "__main__":
    sys.exit(main())
