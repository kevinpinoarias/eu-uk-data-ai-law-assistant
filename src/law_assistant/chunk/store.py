"""Read and write chunks as JSON Lines: one chunk per line."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from law_assistant.chunk.chunker import Chunk


def write_chunks(path: Path, chunks: Iterable[Chunk]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = (json.dumps(c.to_dict(), ensure_ascii=False) for c in chunks)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def read_chunks(path: Path) -> list[Chunk]:
    with path.open(encoding="utf-8") as f:
        return [Chunk.from_dict(json.loads(line)) for line in f if line.strip()]
