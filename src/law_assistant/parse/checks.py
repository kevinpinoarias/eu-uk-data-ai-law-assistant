"""
Structural checks for parsed documents. A parser fails quietly (a dropped article raises no error), so every
parse is checked against facts that must hold: unique ids, no empty leaves, numbering without gaps, known
totals, clean text, the same skeleton in both languages, and that nothing was lost (coverage).
"""

from __future__ import annotations

import re
from collections.abc import Iterable, Sequence

from law_assistant.model import Provision

_MARKUP = re.compile(r"</?[A-Za-z][^>]*>")
_DEFAULT_UNIT_WORDS = {"article": "Article", "annex": "ANNEX"}


def _numbers(provisions: Sequence[Provision], unit: str) -> list[int]:
    return sorted({int(p.path[0]) for p in provisions if p.unit == unit and p.path[0].isdigit()})


def _gaps(numbers: list[int]) -> list[int]:
    return [n for n in range(1, (max(numbers) if numbers else 0) + 1) if n not in numbers]


def check_structure(
    provisions: Sequence[Provision],
    *,
    expected_articles: int | None = None,
    expected_recitals: int | None = None,
    expected_annexes: int | None = None,
) -> list[str]:
    """Return a list of problems; an empty list means the document passes."""
    problems: list[str] = []

    seen: set[str] = set()
    for p in provisions:
        if p.id in seen:
            problems.append(f"duplicate id: {p.id}")
        seen.add(p.id)

    paths = [(p.unit, p.path) for p in provisions]
    for p in provisions:
        if not p.text and p.kind in ("recital", "paragraph", "point"):
            has_child = any(
                u == p.unit and len(q) > len(p.path) and q[: len(p.path)] == p.path for u, q in paths
            )
            if not has_child:
                problems.append(f"empty text: {p.id}")

    articles, recitals = _numbers(provisions, "article"), _numbers(provisions, "recital")
    if _gaps(articles):
        problems.append(f"article numbering has gaps: {_gaps(articles)}")
    if _gaps(recitals):
        problems.append(f"recital numbering has gaps: {_gaps(recitals)}")
    for name, found, expected in (
        ("articles", len(articles), expected_articles),
        ("recitals", len(recitals), expected_recitals),
        ("annexes", len({p.path[0] for p in provisions if p.unit == "annex"}), expected_annexes),
    ):
        if expected is not None and found != expected:
            problems.append(f"expected {expected} {name}, found {found}")

    headed = {p.path[0]: p.heading for p in provisions if p.unit == "article"}
    for number, heading in sorted(headed.items(), key=lambda item: int(item[0]) if item[0].isdigit() else 0):
        if not heading:
            problems.append(f"article {number} has no heading")

    for p in provisions:
        if _MARKUP.search(p.text):
            problems.append(f"leftover markup in {p.id}")
        if (
            " " in p.text
            or "  " in p.text
            or p.text != p.text.strip()
            or ("\n" in p.text and p.kind != "annex")
        ):
            problems.append(f"odd whitespace in {p.id}")
    return problems


def compare_skeletons(first: Iterable[Provision], second: Iterable[Provision]) -> list[str]:
    """Differences between two languages' ids; the same law must give the same skeleton."""
    a, b = {p.id for p in first}, {p.id for p in second}
    return [f"only in the first: {i}" for i in sorted(a - b)] + [
        f"only in the second: {i}" for i in sorted(b - a)
    ]


def coverage_ratio(
    provisions: Sequence[Provision],
    *,
    source_characters: int,
    unit_words: dict[str, str] | None = None,
) -> float:
    """Letters and digits kept (text, labels, headings once per unit, "Article N" words) over the source's."""

    def size(text: str) -> int:
        return len(re.sub(r"\W", "", text))

    words = _DEFAULT_UNIT_WORDS if unit_words is None else unit_words
    kept = sum(size(p.text) for p in provisions)
    kept += sum(size(p.path[-1]) for p in provisions if p.kind in ("point", "paragraph", "recital"))
    units = {(p.unit, p.path[0]): p for p in provisions if p.unit in ("article", "annex")}
    kept += sum(size(p.heading or "") for p in units.values())
    kept += sum(size(words.get(unit, "") + number) for unit, number in units)
    return kept / source_characters
