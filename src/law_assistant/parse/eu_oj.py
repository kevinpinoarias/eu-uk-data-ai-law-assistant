"""
Parse an EU Official Journal text (the XHTML Cellar serves) into Provisions.

What the markup looks like (profiled on the GDPR, the AI Act and the Digital Omnibus):
- recitals are `div#rct_N`, each a two-column table: "(N)" | text;
- chapters are `div#cpt_X` (heading `p.oj-ti-section-1`, title `div.eli-title`), sections `div#cpt_X.sct_N`;
- articles are `div#art_N`: number `p.oj-ti-art`, title `div.eli-title`, then either numbered paragraphs
  `div#NNN.NNN` or plain `p` and list tables;
- lists (points, definitions) are tables too: label cell "(a)" | text cell, with nested tables for sub-points;
- annexes are `div#anx_X` with `p.oj-doc-ti` for the number and title;
- footnote markers are links to "#..." whose text is a number in brackets, and are not part of the law's text.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator

from law_assistant.model import Provision
from law_assistant.parse.text import clean, local, text_of

_RECITAL = re.compile(r"rct_(\d+)")
_ARTICLE = re.compile(r"art_(\d+)")
_ANNEX = re.compile(r"anx_([IVXLC]+)")
_CHAPTER = re.compile(r"cpt_[IVXLC\d]+(\.sct_\d+)?")
_PARAGRAPH_ID = re.compile(r"\d{3}\.(\d{3})")
_LEADING_NUMBER = re.compile(r"^\d+\.\s*")
_FOOTNOTE_TEXT = re.compile(r"^\(?\d+\)?$")
_POINT_PARAGRAPH = re.compile(r"^\(?(\d+|[a-z]|[ivxl]+)\)\s*(.*)$")  # "1) text", "(a) text"
_OPENING_QUOTES = "‘“«„'\""
_SECTION_HEADING = re.compile(
    r"^(?:section|secci[oó]n|part|parte)\s+([A-Za-z0-9]+)[\s:.—–-]*(.*)$", re.IGNORECASE
)
_NUMBERED_HEADING = re.compile(r"^(\d+)\.\s+(.*)$")
_PREFIX = {"recital": "rct", "article": "art", "annex": "anx"}


def _is_footnote_marker(element: ET.Element) -> bool:
    href = element.get("href", "")
    return (
        local(element) == "a"
        and href.startswith("#")
        and bool(_FOOTNOTE_TEXT.match(clean("".join(element.itertext()))))
    )


def _own_text(element: ET.Element) -> str:
    """Text of an element without footnote markers and without nested list tables."""
    return text_of(element, skip=lambda e: _is_footnote_marker(e) or local(e) == "table")


def _full_text(element: ET.Element) -> str:
    return text_of(element, skip=_is_footnote_marker)


def _label(raw: str) -> str:
    """'(a)' -> 'a', '1.' -> '1', '(iii)' -> 'iii'."""
    label = clean(raw).lstrip(_OPENING_QUOTES).strip("().")
    return label or clean(raw)


def _flatten(children: list[ET.Element], keep_paragraphs: bool = True) -> list[ET.Element]:
    """See through wrapper `div`s (quoted blocks in amending acts) so their paragraphs and tables are read.

    At article level, numbered-paragraph containers (`div#NNN.NNN`) are kept as they are: the article parser
    handles them. Inside a list cell they are quoted text, so `keep_paragraphs=False` flattens them too."""
    out: list[ET.Element] = []
    for child in children:
        is_paragraph = _PARAGRAPH_ID.fullmatch(child.get("id", "")) is not None
        if local(child) == "div" and not (keep_paragraphs and is_paragraph):
            out.extend(_flatten(list(child), keep_paragraphs))
        else:
            out.append(child)
    return out


def _split_lead(children: list[ET.Element]) -> tuple[list[ET.Element], list[ET.Element]]:
    """Split children into the lead `p`s and the rest (from the first table or numbered paragraph on)."""
    for index, child in enumerate(children):
        if local(child) == "table" or (local(child) == "p" and _POINT_PARAGRAPH.match(_full_text(child))):
            return children[:index], children[index:]
    return children, []


class _Parser:
    def __init__(self, instrument: str, language: str, version: str, source_key: str | None) -> None:
        self.instrument, self.language, self.version, self.source_key = (
            instrument,
            language,
            version,
            source_key,
        )
        self.provisions: list[Provision] = []
        self._ids: dict[str, int] = {}

    def emit(
        self,
        unit: str,
        kind: str,
        path: tuple[str, ...],
        text: str,
        heading: str | None,
        chapter: str | None,
    ) -> None:
        base = f"{self.instrument}/{_PREFIX[unit]}-" + "/".join(path)
        if kind == "closing":
            base += "~closing"
        count = self._ids.get(base, 0) + 1
        self._ids[base] = count
        self.provisions.append(
            Provision(
                id=base if count == 1 else f"{base}{count}",
                instrument=self.instrument,
                jurisdiction="EU",
                language=self.language,
                version=self.version,
                unit=unit,
                kind=kind,
                path=path,
                text=text,
                order=len(self.provisions),
                heading=heading,
                chapter=chapter,
                source_key=self.source_key,
            )
        )

    # --- lists: lead text, tables of points (nested), closing text ------------------------------------------

    def blocks(
        self,
        children: list[ET.Element],
        unit: str,
        path: tuple[str, ...],
        heading: str | None,
        chapter: str | None,
        as_text: bool = False,
    ) -> None:
        """Walk what follows a unit's lead text: list tables and numbered paragraphs, then closing text.

        A table attaches to the latest numbered paragraph above it (sub-points), else to the unit itself.
        With `as_text`, plain paragraphs are kept as closing text even when no list came before them.
        """
        current = path
        seen_list = as_text
        for child in children:
            tag = local(child)
            if tag == "table":
                seen_list = True
                label = _first_label(child)
                if label and not label.isdigit() and current != path:
                    # (a), (b) tables that follow a numbered table are that point's sub-points
                    self.table(child, unit, current, heading, chapter)
                else:
                    last = self.table(child, unit, path, heading, chapter)
                    if label and label.isdigit() and last:
                        current = last
            elif tag == "p":
                text = _full_text(child)
                numbered = _POINT_PARAGRAPH.match(text)
                if numbered:
                    seen_list = True
                    current = (*path, _label(numbered.group(1)))
                    self.emit(unit, "point", current, numbered.group(2), heading, chapter)
                elif text and seen_list:
                    self.emit(unit, "closing", path, text, heading, chapter)

    def table(
        self, table: ET.Element, unit: str, path: tuple[str, ...], heading: str | None, chapter: str | None
    ) -> tuple[str, ...] | None:
        """Emit one point per row; return the path of the last one."""
        last: tuple[str, ...] | None = None
        if _is_data_table(table):
            for row in _rows(table):  # a table of data: keep each row as one line of text
                line = " | ".join(t for t in (_full_text(c) for c in row if local(c) in ("td", "th")) if t)
                if line:
                    self.emit(unit, "closing", path, line, heading, chapter)
            return None
        for row in _rows(table):
            cells = [c for c in row if local(c) == "td"]
            if len(cells) == 1:  # a full-width cell: text (often a quoted block), not a list item
                children = [c for c in _flatten(list(cells[0]), False) if local(c) in ("p", "table")]
                self.blocks(children, unit, path, heading, chapter, as_text=True)
                continue
            parts = _row_parts(row)
            if parts is None:
                continue
            label_cell, content = parts
            label = _label(_full_text(label_cell))
            point_path = (*path, label)
            last = point_path
            children = [c for c in _flatten(list(content), False) if local(c) in ("p", "span", "table")]
            lead, rest = _split_lead(children)
            lead_text = " ".join(x for x in (_full_text(c) for c in lead) if x)
            self.emit(unit, "point", point_path, lead_text or _own_text(content), heading, chapter)
            self.blocks(rest, unit, point_path, heading, chapter)
        return last

    # --- the three kinds of unit ----------------------------------------------------------------------------

    def recital(self, element: ET.Element) -> None:
        number = _RECITAL.fullmatch(element.get("id", "")).group(1)  # type: ignore[union-attr]
        cells = [td for td in element.iter() if local(td) == "td"]
        text = _full_text(cells[1]) if len(cells) > 1 else _full_text(element)
        self.emit("recital", "recital", (number,), text, None, None)

    def article(self, element: ET.Element, chapter: str | None) -> None:
        number = _ARTICLE.fullmatch(element.get("id", "")).group(1)  # type: ignore[union-attr]
        title = next((_full_text(c) for c in element if "eli-title" in c.get("class", "")), None)
        body = [
            c
            for c in _flatten([c for c in element if not _is_article_head(c)])
            if local(c) in ("p", "div", "table")
        ]
        paragraph_divs = [c for c in body if local(c) == "div" and _PARAGRAPH_ID.fullmatch(c.get("id", ""))]
        if paragraph_divs:
            lead = [c for c in body[: body.index(paragraph_divs[0])] if local(c) == "p"]
            self._lead_text(lead, "article", (number,), title, chapter)
            for div in paragraph_divs:
                label = str(int(_PARAGRAPH_ID.fullmatch(div.get("id", "")).group(1)))  # type: ignore[union-attr]
                lead, rest = _split_lead([c for c in div if local(c) in ("p", "table")])
                lead_text = " ".join(t for t in (_full_text(c) for c in lead) if t)
                text = _LEADING_NUMBER.sub("", lead_text, count=1)
                self.emit("article", "paragraph", (number, label), text, title, chapter)
                self.blocks(rest, "article", (number, label), title, chapter)
        else:
            lead, rest = _split_lead([c for c in body if local(c) in ("p", "table")])
            self._lead_text(lead, "article", (number,), title, chapter)
            self.blocks(rest, "article", (number,), title, chapter)

    def _lead_text(
        self, paragraphs: list[ET.Element], unit: str, path: tuple[str, ...], heading, chapter
    ) -> None:
        text = " ".join(t for t in (_full_text(p) for p in paragraphs) if t)
        if text:
            self.emit(unit, "article" if unit == "article" else "annex", path, text, heading, chapter)

    def annex(self, element: ET.Element) -> None:
        number = _ANNEX.fullmatch(element.get("id", "")).group(1)  # type: ignore[union-attr]
        children = [c for c in element if local(c) in ("p", "table")]
        titles = [c for c in children if local(c) == "p" and "oj-doc-ti" in c.get("class", "")]
        heading = _full_text(titles[1]) if len(titles) > 1 else None
        groups = _annex_groups([c for c in children if c not in titles])
        for label, section_heading, group in groups:
            path = (number,) if label is None else (number, label)
            lead, rest = _split_lead(group)
            lead_text = " ".join(t for t in (_full_text(c) for c in lead) if t)
            text = chr(10).join(t for t in (section_heading, lead_text) if t)  # heading, then its intro line
            if label is None or text:
                self.emit("annex", "annex", path, text, heading, None)
            self.blocks(rest, "annex", path, heading, None)


def _annex_groups(children: list[ET.Element]) -> list[tuple[str | None, str, list[ET.Element]]]:
    """Group an annex's content by its sub-headings ("Section A - ...", "1. Title").

    The first group, before any sub-heading, has no label."""
    groups: list[tuple[str | None, str, list[ET.Element]]] = [(None, "", [])]
    for child in children:
        if local(child) == "p" and "oj-ti-grseq" in child.get("class", ""):
            text = _full_text(child)
            match = _SECTION_HEADING.match(text) or _NUMBERED_HEADING.match(text)
            if match:
                groups.append((_label(match.group(1)), match.group(2).strip(), []))
                continue
            label, existing, members = groups[-1]
            if label is not None and not members:  # a second heading line is the title of the section above
                groups[-1] = (label, f"{existing} {text}".strip(), members)
                continue
        groups[-1][2].append(child)
    return groups


def _rows(table: ET.Element) -> Iterator[ET.Element]:
    """The table's own rows only: rows of tables nested inside a cell belong to those inner tables."""
    for child in table:
        if local(child) == "tr":
            yield child
        elif local(child) in ("tbody", "thead", "tfoot"):
            yield from (row for row in child if local(row) == "tr")


def _row_parts(row: ET.Element) -> tuple[ET.Element, ET.Element] | None:
    """(label cell, content cell) of a list row. Some rows have an empty indent cell first: the label is the
    last non-empty cell before the content cell."""
    cells = [c for c in row if local(c) == "td"]
    if len(cells) < 2:
        return None
    content = cells[-1]
    label_cell = next((c for c in reversed(cells[:-1]) if _full_text(c)), cells[-2])
    return label_cell, content


def _is_data_table(table: ET.Element) -> bool:
    return "oj-table" in table.get("class", "")


def _first_label(table: ET.Element) -> str | None:
    if _is_data_table(table):
        return None
    for row in _rows(table):
        parts = _row_parts(row)
        if parts is not None:
            return _label(_full_text(parts[0]))
    return None


def _is_article_head(element: ET.Element) -> bool:
    cls = element.get("class", "")
    return "oj-ti-art" in cls or "eli-title" in cls


def _chapter_label(chapter: ET.Element) -> str | None:
    heading = next(
        (_full_text(c) for c in chapter if local(c) == "p" and "oj-ti-section-1" in c.get("class", "")), None
    )
    title = next((_full_text(c) for c in chapter if "eli-title" in c.get("class", "")), None)
    parts = [p for p in (heading, title) if p]
    return " — ".join(parts) if parts else None


def _walk(root: ET.Element) -> Iterator[tuple[ET.Element, str | None]]:
    """Every recital, article and annex in document order, with the chapter (and section) of each article."""

    def visit(node: ET.Element, chapter: str | None) -> Iterator[tuple[ET.Element, str | None]]:
        ident = node.get("id", "")
        if _RECITAL.fullmatch(ident) or _ARTICLE.fullmatch(ident) or _ANNEX.fullmatch(ident):
            yield node, chapter
            return
        if _CHAPTER.fullmatch(ident):
            label = _chapter_label(node)
            chapter = f"{chapter} > {label}" if chapter and label and ".sct_" in ident else (label or chapter)
        for child in node:
            yield from visit(child, chapter)

    yield from visit(root, None)


def source_characters(xhtml: str | bytes) -> int:
    """Letters and digits in the source's recitals, articles and annexes: the yardstick for coverage."""
    root = ET.fromstring(xhtml)
    return sum(len(re.sub(r"\W", "", text_of(node, skip=_is_footnote_marker))) for node, _ in _walk(root))


def parse_eu_oj(
    xhtml: str | bytes,
    *,
    instrument: str,
    language: str,
    version: str = "oj",
    source_key: str | None = None,
) -> list[Provision]:
    root = ET.fromstring(xhtml)
    parser = _Parser(instrument, language, version, source_key)
    for node, chapter in _walk(root):
        ident = node.get("id", "")
        if _RECITAL.fullmatch(ident):
            parser.recital(node)
        elif _ARTICLE.fullmatch(ident):
            parser.article(node, chapter)
        else:
            parser.annex(node)
    return parser.provisions
