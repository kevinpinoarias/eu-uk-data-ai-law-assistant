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
    expected_sections: int | None = None,
    expected_recitals: int | None = None,
    expected_annexes: int | None = None,
    expected_schedules: int | None = None,
    expected_dispositions: int | None = None,
    allowed_gaps: Iterable[int] = (),
) -> list[str]:
    """Return a list of problems; an empty list means the document passes.

    `allowed_gaps` are article or section numbers known to be absent (repealed, or not yet in force).
    """
    problems: list[str] = []
    allowed = set(allowed_gaps)

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

    numbered = {unit: _numbers(provisions, unit) for unit in ("article", "section", "recital")}
    for unit, numbers in numbered.items():
        gaps = [n for n in _gaps(numbers) if n not in allowed]
        if gaps:
            problems.append(f"{unit} numbering has gaps: {gaps}")
    for unit in ("article", "section"):  # an inserted "5A" needs a "5" (or a known absence)
        labels = {p.path[0] for p in provisions if p.unit == unit}
        for label in sorted(labels):
            base = re.match(r"\d+", label)
            if base and not label.isdigit() and int(base.group()) not in set(numbered[unit]) | allowed:
                problems.append(f"{unit} {label} has no {unit} {base.group()}")
    for name, found, expected in (
        ("articles", len(numbered["article"]), expected_articles),
        ("sections", len(numbered["section"]), expected_sections),
        ("recitals", len(numbered["recital"]), expected_recitals),
        ("annexes", len({p.path[0] for p in provisions if p.unit == "annex"}), expected_annexes),
        ("schedules", len({p.path[0] for p in provisions if p.unit == "schedule"}), expected_schedules),
        (
            "dispositions",
            len({p.path[:2] for p in provisions if p.unit == "disposition"}),
            expected_dispositions,
        ),
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


_LATIN_SUFFIX = {
    "bis": "a",
    "ter": "b",
    "quater": "c",
    "quinquies": "d",
    "sexies": "e",
    "septies": "f",
    "octies": "g",
}
_LATIN_LABEL = re.compile(r"\s+(" + "|".join(_LATIN_SUFFIX) + r")\b")


def _normalised_id(id_: str) -> str:
    """Spanish writes inserted provisions "14 bis", "14 ter"; English 14a, 14b. Map both to 14a, 14b."""
    return _LATIN_LABEL.sub(lambda m: _LATIN_SUFFIX[m.group(1)], id_)


def compare_skeletons(
    first: Iterable[Provision], second: Iterable[Provision], *, normalise_inserted_labels: bool = False
) -> list[str]:
    """Differences between two languages' ids; the same law must give the same skeleton."""
    fix = _normalised_id if normalise_inserted_labels else (lambda i: i)
    a, b = {fix(p.id) for p in first}, {fix(p.id) for p in second}
    return [f"only in the first: {i}" for i in sorted(a - b)] + [
        f"only in the second: {i}" for i in sorted(b - a)
    ]


def compare_texts(first: Iterable[Provision], second: Iterable[Provision]) -> dict[str, list[str]]:
    """Compare two parses of (versions of) the same law id by id, ignoring spacing.

    Returns the ids whose wording changed and the ids present on one side only. Used to check a consolidated
    text against the Official Journal text: every change should be an amendment or a corrigendum.
    """

    def squash(text: str) -> str:
        return re.sub(r"\s+", "", text)

    a, b = {p.id: p for p in first}, {p.id: p for p in second}
    return {
        "changed": sorted(i for i in a.keys() & b.keys() if squash(a[i].text) != squash(b[i].text)),
        "only_first": sorted(a.keys() - b.keys()),
        "only_second": sorted(b.keys() - a.keys()),
    }


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
    units = {
        (p.unit, *(p.path[:2] if p.unit == "disposition" else p.path[:1]))
        for p in provisions
        if p.unit in ("article", "section", "annex", "schedule", "disposition")
    }
    headings = {(p.unit, p.path[0], p.heading) for p in provisions if p.heading and p.unit != "recital"}
    kept += sum(size(heading) for _, _, heading in headings)
    kept += sum(size(words.get(unit[0], "") + "".join(unit[1:])) for unit in units)
    return kept / source_characters
