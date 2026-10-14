"""Read and write parsed documents as JSON Lines: one provision per line."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from law_assistant.model import Provision


def write_jsonl(path: Path, provisions: Iterable[Provision]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = (json.dumps(p.to_dict(), ensure_ascii=False) for p in provisions)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[Provision]:
    with path.open(encoding="utf-8") as f:
        return [Provision.from_dict(json.loads(line)) for line in f if line.strip()]
