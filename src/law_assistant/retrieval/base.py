"""What every retriever offers the runner: a name and a ranked list of chunk ids for a question's text."""

from __future__ import annotations

from typing import Protocol


class Retriever(Protocol):
    name: str

    def search(self, query: str, k: int) -> list[str]: ...
