"""
Index version policies (R8) and duplicate collapsing (R10).

The index holds some texts twice: the GDPR and the AI Act as first published (version "oj") and as
consolidated. A question about today's law should not retrieve superseded wording, and a question about the
past needs it.

- current_text_only: drop the first-published articles and annexes of a text that also has a consolidated
  version; keep its recitals (only the published text has them) and every text that has a single version;
- original_text_only: keep the first-published chunks and drop the consolidated ones of such texts;
- AsOfRetriever: send a question dated before the cutoff to one retriever and any other to another. It reads
  the date from the gold question, so it is an upper bound on what a router that must infer the date can do;
- CollapsedRetriever: ask a retriever for more results than needed, keep the best-ranked chunk of each group
  of copies, and cut to k, so copies of one provision stop using up the top slots.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from law_assistant.chunk.chunker import Chunk
from law_assistant.evaluation.gold import GoldQuestion
from law_assistant.retrieval.base import Retriever

ORIGINAL = "oj"


def _versions(chunks: Sequence[Chunk]) -> dict[str, set[str]]:
    found: dict[str, set[str]] = {}
    for c in chunks:
        found.setdefault(c.instrument, set()).add(c.version)
    return found


def _has_both(versions: set[str]) -> bool:
    return ORIGINAL in versions and any(v != ORIGINAL for v in versions)


def current_text_only(chunks: Sequence[Chunk]) -> list[Chunk]:
    both = {i for i, v in _versions(chunks).items() if _has_both(v)}
    return [c for c in chunks if not (c.instrument in both and c.version == ORIGINAL and c.unit != "recital")]


def original_text_only(chunks: Sequence[Chunk]) -> list[Chunk]:
    both = {i for i, v in _versions(chunks).items() if _has_both(v)}
    return [c for c in chunks if not (c.instrument in both and c.version != ORIGINAL)]


class AsOfRetriever:
    def __init__(
        self, questions: Sequence[GoldQuestion], *, early: Retriever, late: Retriever, cutoff: str
    ) -> None:
        self.name = f"as-of({early.name}|{late.name})"
        self._as_of = {q.text: q.as_of for q in questions}
        self._early, self._late, self._cutoff = early, late, cutoff

    def search(self, query: str, k: int) -> list[str]:
        as_of = self._as_of.get(query)
        chosen = self._early if as_of is not None and as_of < self._cutoff else self._late
        return chosen.search(query, k)


class CollapsedRetriever:
    """by = "copies": one chunk per piece of a provision whatever its version and language;
    by = "units": one chunk per article, section, annex or recital, whichever piece."""

    def __init__(
        self, base: Retriever, chunks_by_id: Mapping[str, Chunk], *, by: str, depth: int = 50
    ) -> None:
        if by not in ("copies", "units"):
            raise ValueError(f"by must be 'copies' or 'units', not {by!r}")
        self.name = f"{base.name}+collapse-{by}"
        self._base, self._chunks, self._by, self._depth = base, chunks_by_id, by, depth

    def _key(self, chunk: Chunk) -> tuple:
        unit = (chunk.instrument, chunk.unit, chunk.unit_path)
        return (*unit, chunk.part) if self._by == "copies" else unit

    def search(self, query: str, k: int) -> list[str]:
        seen: set[tuple] = set()
        out: list[str] = []
        for chunk_id in self._base.search(query, max(self._depth, k)):
            key = self._key(self._chunks[chunk_id])
            if key not in seen:
                seen.add(key)
                out.append(chunk_id)
        return out[:k]
