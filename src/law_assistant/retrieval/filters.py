"""
Filters (R6): search only the chunks a question can be about.

A question that names the UK is not helped by the EU's GDPR text, and an English question gains nothing from
the Spanish translation of an EU law when the English one exists. A filter removes such chunks from the
ranking before the top results are taken. The whole ranking is filtered (not just the top 50), so a wanted
chunk is never lost because unwanted ones filled the list.

Two rules are provided, both small and readable:
- jurisdiction: a question naming the EU searches EU law, the UK searches UK law, Spain searches Spanish law
  and EU law (Spanish data-protection law rests on the GDPR); naming nothing searches everything;
- language: where a text exists in both languages only the question's language is kept; a text that exists in
  one language only (the UK laws in English, the Spanish law in Spanish) is always kept.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence

from law_assistant.chunk.chunker import Chunk

Allow = Callable[[str, Chunk], bool]


def allowed_jurisdictions(named: Sequence[str]) -> set[str] | None:
    """Jurisdictions to search for a question that names these; None means search everything."""
    if not named:
        return None
    allowed = set(named)
    if "ES" in allowed:
        allowed.add("EU")
    return allowed


def language_filter(chunks: Sequence[Chunk]) -> Callable[[str, Chunk], bool]:
    """`keep(language, chunk)`: the chunk is in the question's language, or its text has no other language."""
    languages: dict[str, set[str]] = {}
    for c in chunks:
        languages.setdefault(c.instrument, set()).add(c.language)

    def keep(language: str, chunk: Chunk) -> bool:
        available = languages[chunk.instrument]
        return chunk.language == language or language not in available

    return keep


class FilteredRetriever:
    """Ask `base` for its whole ranking (it needs `scored(query, k)`) and keep the chunks `allow` accepts."""

    def __init__(self, base, chunks: Sequence[Chunk], allow: Allow, *, name: str = "filtered") -> None:
        self.name = f"{base.name}+{name}"
        self._base, self._by_id, self._allow = base, {c.id: c for c in chunks}, allow
        self._total = len(chunks)

    def search(self, query: str, k: int) -> list[str]:
        kept = [i for i, _ in self._base.scored(query, self._total) if self._allow(query, self._by_id[i])]
        return kept[:k]
