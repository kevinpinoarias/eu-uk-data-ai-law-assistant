"""
Parse the BOE's consolidated XML (open-data API, `/texto`) into Provisions: the Spanish LOPDGDD.

What the markup looks like (profiled on Ley Orgánica 3/2018):
- the text is a list of `bloque`s (`tipo` precepto, encabezado, preambulo, firma), each with a `titulo`
  ("Artículo 6", "Disposición adicional primera") and one or more dated `version`s, every one the whole
  block as it stood from `fecha_vigencia`; a date picks the version in force;
- headings (`encabezado`) give the title, chapter and section the following articles sit in;
- inside a precepto the paragraph classes are used inconsistently ("1." paragraphs, "a)" points and plain
  text all appear as `parrafo` or `parrafo_2`), so markers are recognised by their text: "1." and "Uno."
  paragraphs, "a)" points, "1.º" items and "–" bullets; indented `sangrado` paragraphs are quoted
  amendments to other laws;
- `nota_pie` paragraphs and `blockquote`s are the BOE's editorial notes on amendments, not law text;
- the preamble (exposición de motivos) is divided by Roman-numeral sections and is explanatory, like
  recitals.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date

from law_assistant.model import Provision
from law_assistant.parse.builder import ProvisionBuilder
from law_assistant.parse.text import clean, local, text_of

_ARTICLE_TITLE = re.compile(
    r"^Artículo\s+(\d+(?:\s+(?:bis|ter|quáter|quater|quinquies|sexies|septies|octies))?)$"
)
_DISPOSITION_TITLE = re.compile(r"^Disposición\s+(adicional|transitoria|derogatoria|final)\s+(.+)$")
_SPELLED = (
    "uno|dos|tres|cuatro|cinco|seis|siete|ocho|nueve|diez|once|doce|trece|catorce|quince|dieciséis|diecisiete|"
    "dieciocho|diecinueve|veinte|veintiuno|veintidós|veintitrés|veinticuatro|veinticinco|veintiséis|"
    "veintisiete|veintiocho|veintinueve|treinta"
)
# (level, pattern, group holding the label or None for bullets, group holding the text)
_MARKERS = (
    (1, re.compile(r"^(\d+)\.\s+(.*)$"), 1, 2),
    (1, re.compile(rf"^({_SPELLED})\.\s+(.*)$", re.IGNORECASE), 1, 2),
    (3, re.compile(r"^(\d+)\.º\s+(.*)$"), 1, 2),
    (2, re.compile(r"^([a-z])\)\s+(.*)$"), 1, 2),
    (2, re.compile(r"^[–—-]\s+(.*)$"), None, 1),
)
_MARKER_CLASSES = {"parrafo", "parrafo_2"}
_QUOTED_CLASSES = {"sangrado", "sangrado_2", "sangrado_articulo"}
_ROMAN = re.compile(r"^[IVXLC]+$")


def _is_note(element: ET.Element) -> bool:
    return local(element) == "blockquote" or element.get("class") == "nota_pie"


def _iso(fecha: str) -> str:
    return f"{fecha[:4]}-{fecha[4:6]}-{fecha[6:8]}"


def _pick_version(block: ET.Element, as_of: str) -> ET.Element | None:
    """The version in force on `as_of` (YYYY-MM-DD): the latest whose `fecha_vigencia` is not after it."""
    limit = as_of.replace("-", "")
    versions = [v for v in block if local(v) == "version" and v.get("fecha_vigencia", "") <= limit]
    return max(versions, key=lambda v: v.get("fecha_vigencia", ""), default=None)


def _paragraphs(version: ET.Element) -> list[ET.Element]:
    return [p for p in version if local(p) == "p" and not _is_note(p)]


def _marker(element: ET.Element, text: str) -> tuple[int, str | None, str] | None:
    """(level, label, text without the marker) for a paragraph that starts with a marker, else None."""
    if element.get("class") not in _MARKER_CLASSES:
        return None
    for level, pattern, label_group, text_group in _MARKERS:
        match = pattern.match(text)
        if match:
            label = match.group(label_group).lower() if label_group else None
            return level, label, match.group(text_group)
    return None


@dataclass
class _Open:
    level: int
    path: tuple[str, ...]


class _Parser(ProvisionBuilder):
    def preamble(self, version: ET.Element, date_: str) -> None:
        section: str | None = None
        count = 0
        for p in _paragraphs(version):
            text = clean(text_of(p))
            if p.get("class") == "centro_redonda":
                if _ROMAN.match(text):
                    section, count = text, 0
                continue
            if section and text:
                count += 1
                self.emit("recital", "recital", (section, str(count)), text, None, None, date_)

    def precepto(self, title: str, version: ET.Element, chapter: str | None, date_: str) -> None:
        article = _ARTICLE_TITLE.match(title)
        disposition = _DISPOSITION_TITLE.match(title)
        if article:
            unit, base, ctx_chapter = "article", (article.group(1).lower(),), chapter
        elif disposition:
            unit, base, ctx_chapter = (
                "disposition",
                (disposition.group(1), disposition.group(2).lower()),
                None,
            )
        else:
            return
        heading: str | None = None
        lead: list[str] = []
        started = False
        stack: list[_Open] = []
        bullets: dict[tuple[str, ...], int] = {}

        def emit_lead() -> None:
            nonlocal started
            if lead and not started:
                self.emit(unit, "article", base, " ".join(lead), heading, ctx_chapter, date_)
            started = True

        for p in _paragraphs(version):
            text = clean(text_of(p))
            cls = p.get("class")
            if cls == "articulo":
                rest = text[len(title) + 1 :].strip() if text.startswith(title + ".") else None
                heading = rest.rstrip(".").strip() if rest else None
                continue
            if not text:
                continue
            current = stack[-1].path if stack else base
            marker = _marker(p, text)
            if cls in _QUOTED_CLASSES or marker is None:
                if started:
                    self.emit(unit, "closing", current, text, heading, ctx_chapter, date_)
                elif cls in _QUOTED_CLASSES:
                    emit_lead()
                    self.emit(unit, "closing", current, text, heading, ctx_chapter, date_)
                else:
                    lead.append(text)
                continue
            emit_lead()
            level, label, rest = marker
            while stack and stack[-1].level >= level:
                stack.pop()
            parent = stack[-1].path if stack else base
            if label is None:  # a bullet: number them within their parent
                bullets[parent] = bullets.get(parent, 0) + 1
                label = f"item{bullets[parent]}"
            path = (*parent, label)
            self.emit(unit, "paragraph" if level == 1 else "point", path, rest, heading, ctx_chapter, date_)
            stack.append(_Open(level, path))
        emit_lead()


def _update_headings(levels: dict[int, str], version: ET.Element) -> None:
    """Title, chapter and section headings stack: a new one at a level drops the levels below it."""
    paragraphs = {p.get("class"): clean(text_of(p)) for p in _paragraphs(version)}
    for level, number, name in (
        (1, "titulo_num", "titulo_tit"),
        (2, "capitulo_num", "capitulo_tit"),
        (3, "seccion", None),
    ):
        if number in paragraphs:
            label = " — ".join(t for t in (paragraphs[number], paragraphs.get(name or "")) if t)
            for k in [k for k in levels if k >= level]:
                del levels[k]
            levels[level] = label
            return


def parse_boe(
    xml: str | bytes,
    *,
    instrument: str,
    version: str,
    as_of: str | None = None,
    source_key: str | None = None,
) -> list[Provision]:
    """Provisions of the text as in force on `as_of` (YYYY-MM-DD; today if omitted)."""
    as_of = as_of or date.today().isoformat()
    root = ET.fromstring(xml)
    parser = _Parser(instrument, "es", version, source_key, jurisdiction="ES")
    levels: dict[int, str] = {}
    for block in root.iter("bloque"):
        chosen = _pick_version(block, as_of)
        if chosen is None:
            continue
        kind, title = block.get("tipo"), block.get("titulo", "")
        date_ = _iso(chosen.get("fecha_vigencia", ""))
        if kind == "preambulo":
            parser.preamble(chosen, date_)
        elif kind == "encabezado":
            _update_headings(levels, chosen)
        elif kind == "precepto":
            chapter = " > ".join(levels[k] for k in sorted(levels)) or None
            parser.precepto(title, chosen, chapter, date_)
    return parser.provisions


def source_characters(xml: str | bytes, as_of: str | None = None) -> int:
    """Letters and digits the parser must account for on `as_of`: every paragraph of the articles and
    dispositions (headings and notes aside), and the preamble's paragraphs with their synthetic numbers."""
    as_of = as_of or date.today().isoformat()

    def size(text: str) -> int:
        return len(re.sub(r"\W", "", text))

    total = 0
    for block in ET.fromstring(xml).iter("bloque"):
        chosen = _pick_version(block, as_of)
        if chosen is None:
            continue
        title = block.get("titulo", "")
        if block.get("tipo") == "precepto" and (
            _ARTICLE_TITLE.match(title) or _DISPOSITION_TITLE.match(title)
        ):
            total += sum(size(clean(text_of(p))) for p in _paragraphs(chosen))
        elif block.get("tipo") == "preambulo":
            section, count = None, 0
            for p in _paragraphs(chosen):
                text = clean(text_of(p))
                if p.get("class") == "centro_redonda":
                    if _ROMAN.match(text):
                        section, count = text, 0
                elif section and text:
                    count += 1
                    total += size(text) + size(str(count))
    return total
