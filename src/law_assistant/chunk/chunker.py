"""
Turn the provisions of one parsed document into chunks: the pieces that are embedded, searched and cited.

Rules (decided from the length profile of the parsed texts, see docs/CHUNKING.md):
- the natural unit is one article, section, annex, schedule, disposition or recital; when it fits in the cap
  it is one chunk;
- a longer unit splits at its top-level paragraphs, then (for a paragraph that is still too long) at its
  points, then at sentences, and only as a last resort by words, so the cap is a firm ceiling;
- a paragraph is never separated from its own points while the pair fits, and a closing text stays with the
  point above it;
- every chunk carries a context line (law, chapter, article and heading) that is part of what gets embedded,
  and the ids of the provisions it contains, from which exact pinpoint citations can be built later;
- the same input always gives the same chunks and ids.
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass
from typing import Any

from law_assistant.model import Provision

DEFAULT_MAX_WORDS = 400

# Display names of the laws for the context line: (instrument, language) -> name; the id is the fallback.
INSTRUMENT_NAMES = {
    ("eu-gdpr", "en"): "GDPR (Regulation (EU) 2016/679)",
    ("eu-gdpr", "es"): "RGPD (Reglamento (UE) 2016/679)",
    ("eu-ai-act", "en"): "AI Act (Regulation (EU) 2024/1689)",
    ("eu-ai-act", "es"): "Reglamento de IA (Reglamento (UE) 2024/1689)",
    ("eu-ai-omnibus", "en"): "AI Omnibus (Regulation (EU) 2026/1744)",
    ("eu-ai-omnibus", "es"): "Ómnibus de IA (Reglamento (UE) 2026/1744)",
    ("uk-gdpr", "en"): "UK GDPR",
    ("uk-dpa-2018", "en"): "Data Protection Act 2018",
    ("uk-duaa-2025", "en"): "Data (Use and Access) Act 2025",
    ("es-lopdgdd", "es"): "LOPDGDD (Ley Orgánica 3/2018)",
}
_UNIT_WORDS = {
    "en": {
        "article": "Article",
        "section": "section",
        "annex": "Annex",
        "schedule": "Schedule",
        "recital": "Recital",
    },
    "es": {
        "article": "Artículo",
        "section": "sección",
        "annex": "Anexo",
        "schedule": "Anexo",
        "recital": "Considerando",
    },
}
_BULLET = re.compile(r"^item\d+$")
_ROMAN = re.compile(r"^[ivxlc]+$")
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


@dataclass(frozen=True)
class Chunk:
    id: str  # unique across the corpus: "<version>:<language>:<first provision id>" plus "#n" for a repeat
    instrument: str
    jurisdiction: str
    language: str
    version: str  # which text: "oj", "consolidated-20260727", ...
    unit: str  # article | section | annex | schedule | disposition | recital
    unit_path: tuple[str, ...]  # which unit the chunk belongs to: ("6",) is article 6
    citation: str  # human citation of the unit: "Article 6"
    heading: str | None
    chapter: str | None
    context: str  # law | chapter | citation: heading; part of the embedded text
    text: str  # the law text, with numbering restored ("1.", "(a)")
    provision_ids: tuple[str, ...]  # the provisions the text comes from, in order
    part: int  # which piece of the unit this is (1 when the unit was not split)
    parts: int  # how many pieces the unit was cut into
    words: int
    order: int  # position among the document's chunks
    in_force_from: str | None = None  # latest date among the provisions, where the source states one
    source_key: str | None = None

    @property
    def embed_text(self) -> str:
        return f"{self.context}\n{self.text}"

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["unit_path"] = list(self.unit_path)
        data["provision_ids"] = list(self.provision_ids)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Chunk:
        return cls(
            **{**data, "unit_path": tuple(data["unit_path"]), "provision_ids": tuple(data["provision_ids"])}
        )


@dataclass(frozen=True)
class _Piece:
    provision_id: str
    path: tuple[str, ...]
    text: str  # rendered: numbering restored

    @property
    def words(self) -> int:
        return len(self.text.split())


def unit_key(p: Provision) -> tuple[str, ...]:
    """The path naming the unit a provision belongs to: article 6, schedule 1, disposición final tercera."""
    return p.path[:2] if p.unit in ("disposition", "recital") else p.path[:1]


def render_line(p: Provision, base: int) -> str:
    """The text with its numbering put back: "1." for a paragraph, "(a)" for a point, "–" for a bullet."""
    depth = len(p.path) - base
    if p.kind not in ("paragraph", "point") or depth <= 0:
        return p.text
    label = p.path[-1]
    if _BULLET.match(label):
        return f"– {p.text}"
    if (
        depth == 1
    ):  # the parser lowercased spelled-out labels ("Uno." in the BOE) to build ids; put the capital back
        spelled = label.isalpha() and label.islower() and len(label) > 1 and not _ROMAN.match(label)
        label = label.capitalize() if spelled else label
        return f"{label}. {p.text}".rstrip()
    return f"({label}) {p.text}".rstrip()


def citation_of(unit: str, path: tuple[str, ...], language: str) -> str:
    if unit == "disposition":
        return f"Disposición {' '.join(path)}"
    if unit == "recital" and len(path) == 2:
        if language == "es":
            return f"Preámbulo, sección {path[0]}, párrafo {path[1]}"
        return f"Preamble, section {path[0]}, paragraph {path[1]}"
    words = _UNIT_WORDS.get(language, _UNIT_WORDS["en"])
    return f"{words[unit]} {' '.join(path)}"


def _size(pieces: list[_Piece]) -> int:
    return sum(p.words for p in pieces)


def _segments(pieces: list[_Piece], base: int, depth: int) -> list[list[_Piece]]:
    """Cut at each new label found `depth` levels below the unit. Text before the first label (the lead) is
    its own segment; unlabelled text after a labelled one (a closing) joins the one before."""
    segments: list[list[_Piece]] = []
    current: list[_Piece] = []
    seen: str | None = None
    for piece in pieces:
        label = piece.path[base + depth] if len(piece.path) > base + depth else None
        if label is not None and label != seen:
            if current:
                segments.append(current)
            current, seen = [], label
        current.append(piece)
    if current:
        segments.append(current)
    return segments


def _cut_words(text: str, cap: int) -> list[str]:
    tokens = text.split()
    return [" ".join(tokens[i : i + cap]) for i in range(0, len(tokens), cap)]


def _split_text(piece: _Piece, cap: int) -> list[_Piece]:
    """One overlong piece into pieces of at most `cap` words: sentences first, words as the last resort."""
    units: list[str] = []
    for sentence in _SENTENCE_END.split(piece.text):
        units.extend(_cut_words(sentence, cap) if len(sentence.split()) > cap else [sentence])
    out: list[str] = []
    current: list[str] = []
    for unit in units:
        if current and sum(len(u.split()) for u in current) + len(unit.split()) > cap:
            out.append(" ".join(current))
            current = []
        current.append(unit)
    if current:
        out.append(" ".join(current))
    return [_Piece(piece.provision_id, piece.path, text) for text in out]


def _pack(groups: list[list[_Piece]], cap: int, descend) -> list[list[_Piece]]:
    """Fill chunks greedily with consecutive groups; an overlong group is split by `descend` and its last
    piece stays open for the groups that follow."""
    out: list[list[_Piece]] = []
    current: list[_Piece] = []
    for group in groups:
        if _size(current) + _size(group) <= cap:
            current = current + group
            continue
        if current and _size(current) > 0:
            out.append(current)
            current = []
        if current:  # only empty container lines so far: they travel with the next text
            group = current + group
            current = []
        if _size(group) <= cap:
            current = group
        else:
            parts = descend(group)
            out.extend(parts[:-1])
            current = parts[-1]
    if current:
        out.append(current)
    return out


def _split(pieces: list[_Piece], base: int, depth: int, cap: int) -> list[list[_Piece]]:
    if _size(pieces) <= cap:
        return [pieces]
    deepest = max(len(p.path) for p in pieces) - base
    if depth < deepest:
        segments = _segments(pieces, base, depth)
        if len(segments) == 1:  # no cut possible at this level: try the next one down
            return _split(pieces, base, depth + 1, cap)
        return _pack(segments, cap, lambda group: _split(group, base, depth + 1, cap))
    if len(pieces) > 1:  # same path throughout (repeated lines): cut between the lines
        return _pack([[p] for p in pieces], cap, lambda group: _split(group, base, depth, cap))
    return _pack([[p] for p in _split_text(pieces[0], cap)], cap, lambda group: [group])


def chunk_provisions(
    provisions: list[Provision], *, max_words: int = DEFAULT_MAX_WORDS, instrument_name: str | None = None
) -> list[Chunk]:
    """Chunks of one document (one instrument, version and language), in reading order."""
    if not provisions:
        return []
    first = provisions[0]
    if len({(p.instrument, p.version, p.language) for p in provisions}) != 1:
        raise ValueError(
            "chunk_provisions takes the provisions of one document: one instrument, version, language"
        )
    name = instrument_name or INSTRUMENT_NAMES.get((first.instrument, first.language), first.instrument)

    units: dict[tuple[str, tuple[str, ...]], list[Provision]] = {}
    for p in provisions:
        units.setdefault((p.unit, unit_key(p)), []).append(p)

    chunks: list[Chunk] = []
    seen_ids: dict[str, int] = {}
    for (unit, path), members in units.items():
        base = len(path)
        pieces = [_Piece(p.id, p.path, render_line(p, base)) for p in members]
        groups = _split(pieces, base, 0, max_words)
        citation = citation_of(unit, path, first.language)
        head = members[0]
        label = f"{citation}: {head.heading}" if head.heading else citation
        context = " | ".join(part for part in (name, head.chapter, label) if part)
        dates = [p.in_force_from for p in members if p.in_force_from]
        for number, group in enumerate(groups, start=1):
            ids = tuple(dict.fromkeys(piece.provision_id for piece in group))
            base_id = f"{first.version}:{first.language}:{ids[0]}"
            seen_ids[base_id] = seen_ids.get(base_id, 0) + 1
            text = "\n".join(piece.text for piece in group if piece.text)
            chunks.append(
                Chunk(
                    id=base_id if seen_ids[base_id] == 1 else f"{base_id}#{seen_ids[base_id]}",
                    instrument=first.instrument,
                    jurisdiction=first.jurisdiction,
                    language=first.language,
                    version=first.version,
                    unit=unit,
                    unit_path=path,
                    citation=citation,
                    heading=head.heading,
                    chapter=head.chapter,
                    context=context,
                    text=text,
                    provision_ids=ids,
                    part=number,
                    parts=len(groups),
                    words=len(text.split()),
                    order=len(chunks),
                    in_force_from=max(dates) if dates else None,
                    source_key=head.source_key,
                )
            )
    return chunks
