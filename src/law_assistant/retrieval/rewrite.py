"""
R6: search with a rewritten question. People ask in everyday words ("name a person responsible for data
protection") and the law is written in legal terms ("designate a data protection officer"); a rewrite restates
the question in the law's own vocabulary before it is searched. The rewrites are made beforehand (by a
language model that sees only the question text) and read from a file, so the experiment is repeatable and
needs no network.

Two modes: `replace` searches with the rewrite alone; `append` searches with the question followed by the
rewrite, so nothing of the original is lost. A question with no stored rewrite is an error, never a silent
fallback to the original, because that would quietly score the baseline under the rewrite's name.
"""

from __future__ import annotations

import json
from collections.abc import Mapping, Sequence
from pathlib import Path

from law_assistant.retrieval.base import Retriever

MODES = ("replace", "append")


def read_rewrites(path: Path, questions: Sequence) -> dict[str, str]:
    """Map each question's text to its stored rewrite; every question must have one."""
    by_id = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            by_id[row["id"]] = row["rewrite"]
    missing = [q.id for q in questions if q.id not in by_id]
    if missing:
        raise ValueError(f"no stored rewrite for {', '.join(missing)}")
    return {q.text: by_id[q.id] for q in questions}


class RewriteRetriever:
    def __init__(self, inner: Retriever, rewrites: Mapping[str, str], *, mode: str) -> None:
        if mode not in MODES:
            raise ValueError(f"mode must be one of {MODES}, not {mode!r}")
        self.name = f"rewrite-{mode}({inner.name})"
        self._inner, self._rewrites, self._mode = inner, dict(rewrites), mode

    def search(self, query: str, k: int) -> list[str]:
        if query not in self._rewrites:
            raise KeyError(f"no rewrite for the question: {query[:60]!r}")
        rewrite = self._rewrites[query]
        text = rewrite if self._mode == "replace" else f"{query}\n{rewrite}"
        return self._inner.search(text, k)
