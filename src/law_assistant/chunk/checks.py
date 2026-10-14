"""
Checks that a chunking is right, as the parsers' checks are for the parse: nothing lost, nothing invented,
nothing over the cap. Letters and digits are compared, not spacing: the splitter only moves whitespace.
"""

from __future__ import annotations

import re

from law_assistant.chunk.chunker import Chunk, render_line, unit_key
from law_assistant.model import Provision


def _size(text: str) -> int:
    return len(re.sub(r"\W", "", text))


def check_chunks(provisions: list[Provision], chunks: list[Chunk], *, max_words: int) -> list[str]:
    """Problems found (an empty list means the chunking is sound)."""
    problems: list[str] = []
    ids = [c.id for c in chunks]
    for duplicate in sorted({i for i in ids if ids.count(i) > 1}):
        problems.append(f"duplicate chunk id {duplicate}")
    for c in chunks:
        if not c.text.strip():
            problems.append(f"empty chunk {c.id}")
        if len(c.text.split()) > max_words:
            problems.append(f"chunk {c.id} is over the cap: {len(c.text.split())} words")
        if c.words != len(c.text.split()):
            problems.append(f"chunk {c.id} states {c.words} words but has {len(c.text.split())}")
    covered = {i for c in chunks for i in c.provision_ids}
    for p in provisions:
        if p.id not in covered:
            problems.append(f"provision lost: {p.id}")
    expected = sum(_size(render_line(p, len(unit_key(p)))) for p in provisions)
    actual = sum(_size(c.text) for c in chunks)
    if expected != actual:
        problems.append(f"letters and digits differ: provisions {expected}, chunks {actual} characters")
    return problems
