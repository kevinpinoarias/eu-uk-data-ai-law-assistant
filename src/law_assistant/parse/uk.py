"""
Parse a legislation.gov.uk XML document (UK GDPR, Data Protection Act 2018, Data (Use and Access) Act 2025)
into Provisions.

What the markup looks like (profiled on the three files):
- the ids are already citations: `article-6-1-a`, `section-6A-2`, `schedule-1-paragraph-3-2-a`, `annex-1-1`;
- numbered units are `P1` (article or section), `P2` (paragraph), `P3` to `P6` (points), each with a `P?para`
  holding `Text` and the next level down; heading `Title` is in the enclosing `P1group`;
- chapters are `Part`, `Chapter`, `Pblock` (DPA, DUAA) or `EUChapter`, `EUSection` (UK GDPR) with `Number` and
  `Title`; schedules are `Schedule` with `TitleBlock` and `ScheduleBody`;
- UK GDPR recitals are `Division`s of the `EUPreamble`;
- the text is the current wording: insertions and substitutions are wrapped in `Addition` and `Substitution`;
  commentary and footnote markers are not text; repealed (`Status="Repealed"`) and not yet in force
  (`Status="Prospective"`) provisions are left out and counted;
- `RestrictStartDate` says from when a version of a provision applies;
- quoted amendments to other texts (`BlockAmendment`) have no citation ids: they are kept as closing text.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator
from dataclasses import dataclass, replace

from law_assistant.model import Provision
from law_assistant.parse.builder import ProvisionBuilder
from law_assistant.parse.text import clean, local, text_of

_UNIT_IDS = re.compile(r"^(article|section|schedule|annex)-(.+)$")
_SKIP_STATUS = {"Repealed": "repealed", "Prospective": "prospective"}
_SUB_LEVELS = ("P2", "P3", "P4", "P5", "P6")
_TEXT_BLOCKS = {"Text", "OrderedList", "UnorderedList", "Para"}
_NOTE_MARKERS = {"CommentaryRef", "FootnoteRef"}
_BLOCK_TAGS = frozenset(
    {
        "Text", "Pnumber", "P", "P1", "P2", "P3", "P4", "P5", "P6", "P1para", "P2para", "P3para", "P4para",
        "P5para", "P6para", "Para", "Title", "Number", "ListItem", "Item", "Tabular", "Row", "Entry",
        "BlockAmendment", "OrderedList", "UnorderedList", "Division", "table", "tr", "td", "th", "tbody",
        "thead",
    }
)  # fmt: skip
_CHAPTER_TAGS = ("Part", "Chapter", "Pblock", "PsubBlock", "EUChapter", "EUSection")
_SKIPPED_TREES = ("Metadata", "Footnotes", "Commentaries")


def _is_note_marker(element: ET.Element) -> bool:
    return local(element) in _NOTE_MARKERS


def _text(element: ET.Element) -> str:
    return text_of(element, skip=_is_note_marker, block_tags=_BLOCK_TAGS)


def _child(element: ET.Element, tag: str) -> ET.Element | None:
    return next((c for c in element if local(c) == tag), None)


def _citation(element: ET.Element) -> tuple[str, tuple[str, ...]] | None:
    """Unit and path from the element's id: `schedule-1-paragraph-3-2-a` is schedule 1, paragraph 3, 2, a."""
    match = _UNIT_IDS.match(element.get("id", ""))
    if not match:
        return None
    unit, rest = match.groups()
    labels = tuple(t.strip(".") for t in rest.split("-") if t.strip(".") and t != "paragraph")
    return unit, labels


@dataclass(frozen=True)
class _Context:
    chapters: tuple[str, ...] = ()
    heading: str | None = None
    date: str | None = None

    @property
    def chapter(self) -> str | None:
        return " > ".join(self.chapters) or None


def _content(element: ET.Element) -> list[ET.Element]:
    """What follows a unit's number, in order: the children of its `P?para` and any siblings (tables)."""
    items: list[ET.Element] = []
    for child in element:
        if local(child).endswith("para"):
            items.extend(child)
        elif local(child) != "Pnumber":
            items.append(child)
    return items


def _table_lines(tabular: ET.Element) -> list[str]:
    """One line per table row, cells separated by " | "."""
    lines = []
    for row in tabular.iter():
        if local(row) == "tr":
            cells = [_text(c) for c in row if local(c) in ("td", "th")]
            line = " | ".join(c for c in cells if c)
            if line:
                lines.append(line)
    return lines


def _chapter_label(element: ET.Element) -> str | None:
    number, title = _child(element, "Number"), _child(element, "Title")
    parts = [_text(x) for x in (number, title) if x is not None]
    label = " — ".join(p for p in parts if p)
    return label or None


class _Parser(ProvisionBuilder):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    # --- the walk: containers that carry context, then the units themselves ------------------------------

    def walk(self, node: ET.Element, ctx: _Context) -> None:
        tag = local(node)
        if tag in _SKIPPED_TREES or node.get("Status") in _SKIP_STATUS:
            return
        if node.get("RestrictStartDate") and tag in ("P1group", "Schedule"):
            ctx = replace(ctx, date=node.get("RestrictStartDate"))
        if tag == "EUPreamble":
            self.recitals(node)
            return
        if tag == "Schedule":
            self.schedule(node)
            return
        if tag in _CHAPTER_TAGS:
            label = _chapter_label(node)
            ctx = replace(ctx, chapters=(*ctx.chapters, label) if label else ctx.chapters)
        elif tag == "P1group":
            title = _child(node, "Title")
            ctx = replace(ctx, heading=_text(title) if title is not None else None)
        elif tag == "P1" and _citation(node):
            self.unit_element(node, ctx)
            return
        for child in node:
            if local(child) != "BlockAmendment":
                self.walk(child, ctx)

    def recitals(self, preamble: ET.Element) -> None:
        for division in preamble:
            if local(division) != "Division":
                continue
            number = _child(division, "Number")
            label = clean(_text(number)).strip("().") if number is not None else ""
            body = " ".join(t for t in (_text(p) for p in division if local(p) in ("Title", "P")) if t)
            if label and body:
                self.emit("recital", "recital", (label,), body, None, None)

    def schedule(self, element: ET.Element) -> None:
        citation = _citation(element)
        if citation is None:
            return
        unit, labels = citation
        unit = "annex" if unit == "annex" else "schedule"
        date = element.get("RestrictStartDate")
        block = _child(element, "TitleBlock")
        title = _child(block, "Title") if block is not None else None
        heading = _text(title) if title is not None else None
        body = _child(element, "ScheduleBody")
        intro = [c for c in body if local(c) == "P"] if body is not None else []
        text = " ".join(t for t in (_text(p) for p in intro) if t)
        self.emit(unit, "annex", labels, text, heading, None, date)
        ctx = _Context(date=date)
        if body is not None:
            for child in body:
                if child not in intro:
                    self.walk(child, ctx)

    # --- a citable unit (P1) and its levels ----------------------------------------------------------------

    def unit_element(self, element: ET.Element, ctx: _Context) -> None:
        self.provision(element, ctx)

    def provision(self, element: ET.Element, ctx: _Context) -> None:
        citation = _citation(element)
        if citation is None or element.get("Status") in _SKIP_STATUS:
            return
        unit, path = citation
        unit = "annex" if unit == "annex" else unit
        tag = local(element)
        date = element.get("RestrictStartDate") or ctx.date
        if tag == "P1":
            kind = "article" if unit in ("article", "section") else "paragraph"
        else:
            kind = "paragraph" if tag == "P2" else "point"
        lead: list[str] = []
        started = False

        def emit_self() -> None:
            nonlocal started
            if not started:
                text = " ".join(t for t in lead if t)
                if text or kind != "article":
                    self.emit(unit, kind, path, text, ctx.heading, ctx.chapter, date)
            started = True

        for child in _content(element):
            tag_c = local(child)
            if tag_c == "Tabular":
                emit_self()
                for line in _table_lines(child):
                    self.emit(unit, "closing", path, line, ctx.heading, ctx.chapter, date)
            elif tag_c in _SUB_LEVELS:
                emit_self()
                self.provision(child, replace(ctx, date=date))
            elif tag_c == "BlockAmendment":
                emit_self()
                quoted = _text(child)
                if quoted:
                    self.emit(unit, "closing", path, quoted, ctx.heading, ctx.chapter, date)
            elif tag_c in _TEXT_BLOCKS:
                text = _text(child)
                if not text:
                    continue
                if started:
                    self.emit(unit, "closing", path, text, ctx.heading, ctx.chapter, date)
                else:
                    lead.append(text)
        emit_self()


def _count_skipped(node: ET.Element, counts: dict[str, int], numbers: set[int]) -> None:
    status = node.get("Status")
    if status in _SKIP_STATUS and local(node) in (
        "P1group",
        "P1",
        "P2",
        "P3",
        "P4",
        "P5",
        "P6",
        "Schedule",
        "Part",
    ):
        counts[_SKIP_STATUS[status]] += 1
        for element in node.iter():  # the article or section numbers inside, which become known gaps
            citation = _citation(element) if local(element) == "P1" else None
            if (
                citation
                and citation[0] in ("article", "section")
                and citation[1]
                and citation[1][0].isdigit()
            ):
                numbers.add(int(re.match(r"\d+", citation[1][0]).group()))
        return
    if local(node) in _SKIPPED_TREES:
        return
    for child in node:
        _count_skipped(child, counts, numbers)


def skipped_provisions(xml: str | bytes) -> dict:
    """How many top-level repealed and not-yet-in-force elements were left out, and their numbers."""
    counts = {"repealed": 0, "prospective": 0}
    numbers: set[int] = set()
    _count_skipped(ET.fromstring(xml), counts, numbers)
    return {**counts, "numbers": sorted(numbers)}


def _source_roots(node: ET.Element) -> Iterator[ET.Element]:
    """The elements the parser must account for: recitals, article and section groups, schedules."""
    if local(node) in _SKIPPED_TREES or node.get("Status") in _SKIP_STATUS or local(node) == "BlockAmendment":
        return
    if local(node) == "EUPreamble":
        yield from (d for d in node if local(d) == "Division")
        return
    if local(node) in ("P1group", "P1"):  # a P1 reached here is not inside a P1group (schedule paragraphs)
        yield node
        return
    if local(node) == "Schedule":
        yield from (c for c in node if local(c) in ("Number", "TitleBlock"))
        body = _child(node, "ScheduleBody")
        for child in body if body is not None else []:
            if local(child) == "P":
                yield child
            else:
                yield from _source_roots(child)
        return
    for child in node:
        yield from _source_roots(child)


def source_characters(xml: str | bytes) -> int:
    """Letters and digits in the source's recitals, article and section groups, schedules (live text only)."""

    def skip(element: ET.Element) -> bool:
        return _is_note_marker(element) or element.get("Status") in _SKIP_STATUS

    root = ET.fromstring(xml)
    return sum(
        len(re.sub(r"\W", "", text_of(r, skip=skip, block_tags=_BLOCK_TAGS))) for r in _source_roots(root)
    )


def parse_uk(
    xml: str | bytes,
    *,
    instrument: str,
    version: str,
    source_key: str | None = None,
    language: str = "en",
) -> list[Provision]:
    root = ET.fromstring(xml)
    parser = _Parser(instrument, language, version, source_key, jurisdiction="UK")
    parser.walk(root, _Context())
    return parser.provisions
