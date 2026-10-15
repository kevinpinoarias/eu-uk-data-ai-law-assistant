"""
Vector helpers and a small on-disk store of embeddings, in pure Python (no numerical library is installed).

- normalise: scale a vector to length 1, so that cosine similarity is just a dot product;
- truncate: keep the first n numbers and renormalise (how a shorter vector is made from a longer one);
- VectorStore: vectors by key, saved as raw 32-bit floats next to a JSON list of keys, so an interrupted
  embedding run can be resumed and a finished one is never paid for twice.
"""

from __future__ import annotations

import json
import math
import sys
from array import array
from collections.abc import Sequence
from pathlib import Path


def normalise(vector: Sequence[float]) -> list[float]:
    length = math.sqrt(sum(x * x for x in vector))
    return [x / length for x in vector] if length else [0.0] * len(vector)


def truncate(vector: Sequence[float], n: int) -> list[float]:
    return normalise(vector[:n])


class VectorStore:
    def __init__(self) -> None:
        self._vectors: dict[str, array] = {}

    def __len__(self) -> int:
        return len(self._vectors)

    def __contains__(self, key: str) -> bool:
        return key in self._vectors

    def keys(self) -> list[str]:
        return list(self._vectors)

    def add(self, key: str, vector: Sequence[float]) -> None:
        self._vectors[key] = array("f", vector)

    def get(self, key: str) -> list[float]:
        return list(self._vectors[key])

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        keys = list(self._vectors)
        lengths = {len(v) for v in self._vectors.values()}
        if len(lengths) > 1:
            raise ValueError("a store holds vectors of one length")
        flat = array("f")
        for key in keys:
            flat.extend(self._vectors[key])
        if sys.byteorder == "big":
            flat.byteswap()
        path.with_suffix(".f32").write_bytes(flat.tobytes())
        path.with_suffix(".keys.json").write_text(
            json.dumps({"keys": keys, "length": lengths.pop() if lengths else 0}), encoding="utf-8"
        )

    @classmethod
    def load(cls, path: Path) -> VectorStore:
        store = cls()
        meta_path, data_path = path.with_suffix(".keys.json"), path.with_suffix(".f32")
        if not meta_path.exists() or not data_path.exists():
            return store
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        flat = array("f")
        flat.frombytes(data_path.read_bytes())
        if sys.byteorder == "big":
            flat.byteswap()
        n = meta["length"]
        for i, key in enumerate(meta["keys"]):
            store._vectors[key] = flat[i * n : (i + 1) * n]
        return store
