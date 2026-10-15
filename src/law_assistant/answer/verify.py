"""
Step 6 of the answer layer: check an answer's citations in code before anyone sees the answer.

The model is asked to support its answer with quotations copied from numbered passages. This module checks
each one: the passage number must be one of those the model was given, and the quotation must appear in that
passage's text (after ignoring case, runs of whitespace, and the difference between typographic and plain
quotation marks and dashes). A quotation may use "..." to skip text, and the fragments must then appear in
order. A citation that fails is dropped with its reason; an answer left with no valid citation is not shown as
an answer. No language model is involved, so a fabricated quotation or a citation to a passage that was never
retrieved cannot get through.
"""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Sequence
from dataclasses import dataclass, field

from law_assistant.chunk.chunker import Chunk

MIN_QUOTE_CHARS = 12
_QUOTES = str.maketrans({"“": '"', "”": '"', "„": '"', "‘": "'", "’": "'", "«": '"', "»": '"'})
_DASHES = str.maketrans({"–": "-", "—": "-", "‐": "-", "‑": "-", "−": "-"})
_ELLIPSIS = re.compile(r"\s*(?:\.{3}|…)\s*")


def normalise(text: str) -> str:
    text = unicodedata.normalize("NFKC", text).translate(_QUOTES).translate(_DASHES)
    return re.sub(r"\s+", " ", text).strip().lower()


@dataclass(frozen=True)
class Citation:
    passage: int  # 1-based number of the passage the model was shown
    quote: str


@dataclass(frozen=True)
class ValidCitation:
    chunk: Chunk
    quote: str


@dataclass
class Verification:
    valid: list[ValidCitation] = field(default_factory=list)
    invalid: list[tuple[Citation, str]] = field(default_factory=list)

    @property
    def sources(self) -> list[Chunk]:
        """The distinct chunks that carry a valid citation, in the order they were first cited."""
        seen: dict[str, Chunk] = {}
        for citation in self.valid:
            seen.setdefault(citation.chunk.id, citation.chunk)
        return list(seen.values())


def _contains_in_order(haystack: str, fragments: Sequence[str]) -> bool:
    position = 0
    for fragment in fragments:
        found = haystack.find(fragment, position)
        if found < 0:
            return False
        position = found + len(fragment)
    return True


def verify_citations(citations: Sequence[Citation], passages: Sequence[Chunk]) -> Verification:
    result = Verification()
    for citation in citations:
        if not 1 <= citation.passage <= len(passages):
            result.invalid.append((citation, f"there is no passage {citation.passage}"))
            continue
        fragments = [normalise(f) for f in _ELLIPSIS.split(citation.quote) if f.strip()]
        if not fragments or sum(len(f) for f in fragments) < MIN_QUOTE_CHARS:
            result.invalid.append((citation, "the quote is too short to support a claim"))
            continue
        chunk = passages[citation.passage - 1]
        if _contains_in_order(normalise(chunk.embed_text), fragments):
            result.valid.append(ValidCitation(chunk, citation.quote))
        else:
            result.invalid.append((citation, "the quote is not in the passage"))
    return result
