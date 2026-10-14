"""
Parse an EU consolidated text (the XHTML Cellar serves for CELEX numbers starting with 0) into Provisions.

What the markup looks like (profiled on the consolidated GDPR and AI Act):
- chapters are `div#cpt_X` with headings `p.title-division-1` ("CHAPTER II") and `p.title-division-2`;
- articles are `div#art_N` (inserted articles keep their letter: `art_4a`): number `p.title-article-norm`,
  title `div.eli-title`;
- a numbered paragraph is `div.norm` with a `span.no-parag` ("1.") and its text in a following `div` or `p`;
- lists (points, definitions) are `div.grid-container.grid-list`: label in `grid-list-column-1`, text in
  `grid-list-column-2`, with nested lists inside that cell;
- annexes are `div#anx_X` with `p.title-annex-1` and `p.title-annex-2`;
- amendment markers (`p.modref` "▼C1", `p.arrow` "►B"), footnote markers and the disclaimer are not law text.
Consolidated texts hold no recitals: those exist only in the Official Journal text.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from collections.abc import Iterator

from law_assistant.model import Provision
from law_assistant.parse.builder import ProvisionBuilder
from law_assistant.parse.text import clean, local, text_of

_ARTICLE = re.compile(r"art_(\d+[a-z]*)")
_ANNEX = re.compile(r"anx_([IVXLC]+)")
_CHAPTER = re.compile(r"cpt_[IVXLC\d]+(\.sct_\d+)?")
_MARKER_TEXT = re.compile(r"^\(?\s*\d+\s*\)?$")
_EMPTY_BRACKETS = re.compile(r"\s*\(\s*\)")  # what is left of "(1)" once the footnote marker is removed
_INLINE_MARKS = re.compile(r"[►▼]\s*[A-Z]\d*|◄|—{3,}")  # "►C1 ... ◄" brackets and "▼M1 -----" lines
_SECTION_HEADING = re.compile(
    r"^(?:section|secci[oó]n|part|parte)\s+([A-Za-z0-9]+)[\s:.—–-]*(.*)$", re.IGNORECASE
)
_NUMBERED_HEADING = re.compile(r"^(\d+)\.\s+(.*)$")
_POINT_TEXT = re.compile(
    r"^(?:\(([0-9a-z]+)\)|([a-z])\)|(\d+(?:\.\d+)*)[.)])\s+(\S.*)$"
)  # (a) | a) | 1. | 1)
_OPENING_QUOTES = "‘“«„'\""
_LABEL_ONLY = re.compile(r"^\(?([0-9]+|[a-z]|[ivxl]+)\)?[.)]?$")  # "16)", "a)", "(a)", "1."

Node = tuple[str, "str | ET.Element"]  # ("text", string) or ("el", element), in document order


def _classes(element: ET.Element) -> set[str]:
    return set(element.get("class", "").split())


def _is_marker(element: ET.Element) -> bool:
    """Amendment markers, footnote markers, footnotes and the disclaimer: not part of the law's text."""
    classes = _classes(element)
    if local(element) == "p" and classes & {"modref", "arrow", "disclaimer", "footnote"}:
        return True
    is_note_link = classes & {"superscript"} or element.get("href", "").startswith("#")
    if local(element) in ("span", "a", "sup") and is_note_link:
        return bool(_MARKER_TEXT.match(clean("".join(element.itertext()))))
    return False


def _is_list_item(element: ET.Element) -> bool:
    return local(element) == "div" and {"grid-container", "grid-list"} <= _classes(element)


def _is_numbered_paragraph(element: ET.Element) -> bool:
    return (
        local(element) == "div"
        and "norm" in _classes(element)
        and any(local(c) == "span" and "no-parag" in _classes(c) for c in element)
    )


def _is_wrapper(element: ET.Element) -> bool:
    """A div that only wraps content (`norm`, `inline-element`) and is read through, not as a unit."""
    return (
        local(element) == "div"
        and bool(_classes(element) & {"norm", "inline-element"})
        and not _is_list_item(element)
        and not _is_numbered_paragraph(element)
    )


def _rows(table: ET.Element) -> list[ET.Element]:
    """The table's own rows (directly or inside tbody), not those of tables nested in its cells."""
    rows: list[ET.Element] = []
    for child in table:
        if local(child) == "tr":
            rows.append(child)
        elif local(child) in ("tbody", "thead", "tfoot"):
            rows.extend(r for r in child if local(r) == "tr")
    return rows


def _cells(row: ET.Element) -> list[ET.Element]:
    return [c for c in row if local(c) in ("td", "th")]


def _is_list_table(table: ET.Element) -> bool:
    """A label | text table (definitions, points) as opposed to a table of data."""
    rows = _rows(table)
    return bool(rows) and all(
        len(_cells(r)) >= 2 and _LABEL_ONLY.match(_text(_cells(r)[0]).lower()) for r in rows
    )


def _is_head(element: ET.Element) -> bool:
    return bool(_classes(element) & {"title-article-norm", "eli-title", "title-annex-1", "title-annex-2"})


def _strip_marks(text: str) -> str:
    return clean(_INLINE_MARKS.sub(" ", _EMPTY_BRACKETS.sub("", text)))


def _text(element: ET.Element) -> str:
    return _strip_marks(text_of(element, skip=_is_marker))


def _label(raw: str) -> str:
    label = clean(raw).lstrip(_OPENING_QUOTES).strip("().")
    return label or clean(raw)


def _nodes(container: ET.Element, exclude: frozenset[int] = frozenset()) -> Iterator[Node]:
    """The container's content in order, reading through wrapper divs. `exclude` holds ids to skip."""
    if container.text:
        yield "text", container.text
    for child in container:
        if id(child) in exclude:
            pass
        elif _is_wrapper(child):
            yield from _nodes(child)
        else:
            yield "el", child
        if child.tail:
            yield "text", child.tail


def _lead_and_rest(nodes: Iterator[Node]) -> tuple[str, list[ET.Element]]:
    """Text before the first list, and everything from that list on (lists and closing paragraphs)."""
    parts: list[str] = []
    rest: list[ET.Element] = []
    seen_list = False
    for kind, value in nodes:
        if kind == "text":
            if not seen_list:
                parts.append(str(value))
            continue
        element = value  # type: ignore[assignment]
        if _is_list_item(element):  # type: ignore[arg-type]
            seen_list = True
            rest.append(element)  # type: ignore[arg-type]
        elif seen_list:
            rest.append(element)  # type: ignore[arg-type]
        elif not _is_marker(element):  # type: ignore[arg-type]
            text = _text(element)  # type: ignore[arg-type]
            block = local(element) in ("p", "div")  # type: ignore[arg-type]
            parts.append(f" {text} " if block else text)
    return _strip_marks("".join(parts)), rest


class _Context:
    """The unit (article, annex or annex section) whose lead text is being collected."""

    def __init__(self, path: tuple[str, ...], kind: str, head: str = "", emitted: bool = False) -> None:
        self.path, self.kind, self.head, self.emitted = path, kind, head, emitted
        self.lead: list[str] = []


class _Paragraph:
    """A numbered paragraph held back until we know whether a following paragraph continues it."""

    def __init__(self, path: tuple[str, ...], text: str, rest: list[ET.Element]) -> None:
        self.path, self.text, self.rest = path, text, rest


class _Parser(ProvisionBuilder):
    def closing_and_points(
        self,
        rest: list[ET.Element],
        unit: str,
        path: tuple[str, ...],
        heading: str | None,
        chapter: str | None,
    ) -> None:
        """Lists become points (nested lists go deeper); other text after a list is closing text of `path`."""
        for element in rest:
            if _is_marker(element):
                continue
            if _is_list_item(element):
                self.point(element, unit, path, heading, chapter)
            elif local(element) == "table":
                self.table(element, unit, path, heading, chapter)
            elif _is_wrapper(element):
                inner = [v for k, v in _nodes(element) if k == "el"]
                self.closing_and_points(inner, unit, path, heading, chapter)  # type: ignore[arg-type]
            else:
                text = _text(element)
                if text:
                    self.emit(unit, "closing", path, text, heading, chapter)

    def table(
        self, table: ET.Element, unit: str, path: tuple[str, ...], heading: str | None, chapter: str | None
    ) -> None:
        """A label | text table gives points; any other table is data, kept row by row as closing text."""
        if _is_list_table(table):
            for row in _rows(table):
                cells = _cells(row)
                point_path = (*path, _label(_text(cells[0])))
                lead, rest = _lead_and_rest(_nodes(cells[-1]))
                self.emit(unit, "point", point_path, lead, heading, chapter)
                self.closing_and_points(rest, unit, point_path, heading, chapter)
            return
        for row in _rows(table):
            line = " | ".join(t for t in (_text(c) for c in _cells(row)) if t)
            if line:
                self.emit(unit, "closing", path, line, heading, chapter)

    def point(
        self, item: ET.Element, unit: str, path: tuple[str, ...], heading: str | None, chapter: str | None
    ) -> None:
        label_cell = next((c for c in item if "grid-list-column-1" in _classes(c)), None)
        content = next((c for c in item if "grid-list-column-2" in _classes(c)), None)
        if label_cell is None or content is None:
            return
        point_path = (*path, _label(_text(label_cell)))
        lead, rest = _lead_and_rest(_nodes(content))
        self.emit(unit, "point", point_path, lead, heading, chapter)
        self.closing_and_points(rest, unit, point_path, heading, chapter)

    def body(
        self,
        nodes: Iterator[Node],
        unit: str,
        path: tuple[str, ...],
        heading: str | None,
        chapter: str | None,
    ) -> None:
        """An article's or annex's content: lead text, paragraphs, lists, annex sections, closing text."""
        ctx = _Context(path, "article" if unit == "article" else "annex")
        pending: _Paragraph | None = None
        last = path  # where closing text goes: the latest paragraph, else the unit or section
        current_point: tuple[str, ...] | None = None  # latest "1) text" point, which grid sub-items attach to

        def flush_ctx() -> None:
            if not ctx.emitted:
                text = chr(10).join(
                    t for t in (ctx.head, " ".join(ctx.lead)) if t
                )  # heading, then its intro line
                if text or ctx.kind == "annex":
                    self.emit(unit, ctx.kind, ctx.path, text, heading, chapter)
                ctx.emitted = True

        def flush_pending() -> None:
            nonlocal pending
            if pending is not None:
                self.emit(unit, "paragraph", pending.path, pending.text, heading, chapter)
                self.closing_and_points(pending.rest, unit, pending.path, heading, chapter)
                pending = None

        for kind, value in nodes:
            if kind == "text":
                continue
            element = value  # type: ignore[assignment]
            if _is_marker(element) or _is_head(element):  # type: ignore[arg-type]
                continue
            if unit == "annex" and "title-gr-seq-level-1" in _classes(element):  # type: ignore[arg-type]
                flush_pending()
                heading_text = _text(element)  # type: ignore[arg-type]
                match = _SECTION_HEADING.match(heading_text) or _NUMBERED_HEADING.match(heading_text)
                if match:
                    flush_ctx()
                    ctx = _Context(
                        (*path, _label(match.group(1))), "annex", match.group(2).strip(), emitted=False
                    )
                    last, current_point = ctx.path, None
                elif not ctx.emitted and ctx.path != path and not ctx.lead:
                    ctx.head = (
                        f"{ctx.head} {heading_text}".strip()
                    )  # a second heading line: the section's title
                else:
                    ctx.lead.append(heading_text)
                continue
            if _is_numbered_paragraph(element):  # type: ignore[arg-type]
                flush_ctx()
                flush_pending()
                span = next(c for c in element if local(c) == "span" and "no-parag" in _classes(c))  # type: ignore[union-attr]
                last = (*ctx.path, _label(_text(span)))
                text, rest = _lead_and_rest(_nodes(element, frozenset({id(span)})))  # type: ignore[arg-type]
                pending = _Paragraph(last, text, rest)
                current_point = None
            elif _is_list_item(element):  # type: ignore[arg-type]
                flush_ctx()
                flush_pending()
                self.point(element, unit, current_point or last, heading, chapter)  # type: ignore[arg-type]
            elif local(element) == "table":  # type: ignore[arg-type]
                flush_ctx()
                flush_pending()
                self.table(element, unit, ctx.path if _is_list_table(element) else last, heading, chapter)  # type: ignore[arg-type]
            else:
                text = _text(element)  # type: ignore[arg-type]
                if not text:
                    continue
                numbered = _POINT_TEXT.match(text)
                if numbered:
                    flush_ctx()
                    flush_pending()
                    label = _label(numbered.group(1) or numbered.group(2) or numbered.group(3))
                    if not label.isdigit() and current_point is not None and current_point[-1].isdigit():
                        point_path = (*current_point, label)  # "a)" under the numbered point above
                    else:
                        point_path = (*ctx.path, label)
                        current_point = point_path
                    self.emit(unit, "point", point_path, numbered.group(4), heading, chapter)
                    last = ctx.path
                elif not ctx.emitted and pending is None:
                    ctx.lead.append(text)
                elif pending is not None and not any(_is_list_item(e) for e in pending.rest):
                    pending.text = f"{pending.text} {text}"  # a second subparagraph continues the paragraph
                else:
                    flush_ctx()
                    flush_pending()
                    self.emit(unit, "closing", last, text, heading, chapter)
        flush_ctx()
        flush_pending()

    def article(self, element: ET.Element, chapter: str | None) -> None:
        number = _ARTICLE.fullmatch(element.get("id", "")).group(1)  # type: ignore[union-attr]
        title = next((_text(c) for c in element if "eli-title" in _classes(c)), None)
        self.body(_nodes(element), "article", (number,), title, chapter)

    def annex(self, element: ET.Element) -> None:
        number = _ANNEX.fullmatch(element.get("id", "")).group(1)  # type: ignore[union-attr]
        title = next((_text(c) for c in element if "title-annex-2" in _classes(c)), None)
        self.body(_nodes(element), "annex", (number,), title, None)


def _chapter_label(chapter: ET.Element) -> str | None:
    parts = [_text(c) for c in chapter if _classes(c) & {"title-division-1", "title-division-2"}]
    parts = [p for p in parts if p]
    return " — ".join(parts) if parts else None


def _walk(root: ET.Element) -> Iterator[tuple[ET.Element, str | None]]:
    """Every article and annex in document order, with the chapter (and section) each article sits in."""

    def visit(node: ET.Element, chapter: str | None) -> Iterator[tuple[ET.Element, str | None]]:
        ident = node.get("id", "")
        if _ARTICLE.fullmatch(ident) or _ANNEX.fullmatch(ident):
            yield node, chapter
            return
        if _CHAPTER.fullmatch(ident):
            label = _chapter_label(node)
            chapter = f"{chapter} > {label}" if chapter and label and ".sct_" in ident else (label or chapter)
        for child in node:
            yield from visit(child, chapter)

    yield from visit(root, None)


def source_characters(xhtml: str | bytes) -> int:
    """Letters and digits in the source's articles and annexes, minus markers: the yardstick for coverage."""
    root = ET.fromstring(xhtml)
    return sum(len(re.sub(r"\W", "", _text(node))) for node, _ in _walk(root))


def parse_eu_consolidated(
    xhtml: str | bytes,
    *,
    instrument: str,
    language: str,
    version: str,
    source_key: str | None = None,
) -> list[Provision]:
    root = ET.fromstring(xhtml)
    parser = _Parser(instrument, language, version, source_key)
    for node, chapter in _walk(root):
        if _ARTICLE.fullmatch(node.get("id", "")):
            parser.article(node, chapter)
        else:
            parser.annex(node)
    return parser.provisions
