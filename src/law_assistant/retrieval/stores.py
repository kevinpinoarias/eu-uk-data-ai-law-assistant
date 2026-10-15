"""
Vector search backends (R7): ways of finding the nearest stored vectors to a question's vector.

All vectors here have length 1, so "nearest" by cosine similarity is the largest dot product. The
project's first search (`DenseIndex`) multiplies the question's vector with every chunk's vector in plain
Python. At 3,831 chunks that is fast enough, so the question R7 asks is what a vector library or database
buys, and at what size it starts to matter. Five backends, one interface (`search(query_vector, k)`
returns the positions of the k nearest vectors, nearest first):

- PythonScan: the loop the project started with (the reference);
- NumpyScan: one matrix-by-vector product;
- FaissFlat: FAISS's exact index (same answers, optimised code);
- FaissHNSW: FAISS's approximate graph index (a few answers may differ; much faster on very large sets);
- SqliteVec: an embedded database (SQLite with the sqlite-vec extension), exact, with the vectors stored in a
  table that also persists to disk.

FAISS and sqlite-vec are optional; `available_backends()` lists what can be built on this machine.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from operator import mul


class PythonScan:
    def __init__(self, vectors: Sequence[Sequence[float]]) -> None:
        self._vectors = [list(v) for v in vectors]

    def search(self, query: Sequence[float], k: int) -> list[int]:
        scores = [(sum(map(mul, query, v)), i) for i, v in enumerate(self._vectors)]
        scores.sort(key=lambda s: (-s[0], s[1]))
        return [i for _, i in scores[:k]]


class NumpyScan:
    def __init__(self, vectors: Sequence[Sequence[float]]) -> None:
        import numpy as np

        self._np = np
        self._matrix = np.asarray(vectors, dtype=np.float32)

    def search(self, query: Sequence[float], k: int) -> list[int]:
        np = self._np
        scores = self._matrix @ np.asarray(query, dtype=np.float32)
        k = min(k, len(scores))
        top = np.argpartition(-scores, k - 1)[:k] if k < len(scores) else np.arange(len(scores))
        return [int(i) for i in sorted(top, key=lambda i: (-scores[i], i))]


class FaissFlat:
    def __init__(self, vectors: Sequence[Sequence[float]]) -> None:
        import faiss
        import numpy as np

        self._np = np
        matrix = np.asarray(vectors, dtype=np.float32)
        self._index = faiss.IndexFlatIP(matrix.shape[1])
        self._index.add(matrix)

    def search(self, query: Sequence[float], k: int) -> list[int]:
        _, ids = self._index.search(
            self._np.asarray([query], dtype=self._np.float32), min(k, self._index.ntotal)
        )
        return [int(i) for i in ids[0] if i >= 0]


class FaissHNSW:
    """An approximate graph index: M neighbours per node, `ef_search` candidates examined per question."""

    def __init__(self, vectors: Sequence[Sequence[float]], *, m: int = 32, ef_search: int = 64) -> None:
        import faiss
        import numpy as np

        self._np = np
        matrix = np.asarray(vectors, dtype=np.float32)
        self._index = faiss.IndexHNSWFlat(matrix.shape[1], m, faiss.METRIC_INNER_PRODUCT)
        self._index.hnsw.efSearch = ef_search
        self._index.add(matrix)

    def search(self, query: Sequence[float], k: int) -> list[int]:
        _, ids = self._index.search(
            self._np.asarray([query], dtype=self._np.float32), min(k, self._index.ntotal)
        )
        return [int(i) for i in ids[0] if i >= 0]


class SqliteVec:
    """SQLite with the sqlite-vec extension: a `vec0` table holding the vectors, queried with SQL."""

    def __init__(self, vectors: Sequence[Sequence[float]], path: str = ":memory:") -> None:
        import sqlite3

        import sqlite_vec

        dim = len(vectors[0])
        self._db = sqlite3.connect(path)
        self._db.enable_load_extension(True)
        sqlite_vec.load(self._db)
        self._db.enable_load_extension(False)
        self._serialize = sqlite_vec.serialize_float32
        self._db.execute(f"create virtual table v using vec0(embedding float[{dim}] distance_metric=cosine)")
        self._db.executemany(
            "insert into v(rowid, embedding) values (?, ?)",
            ((i, self._serialize(list(v))) for i, v in enumerate(vectors)),
        )
        self._db.commit()

    def close(self) -> None:
        self._db.close()

    def search(self, query: Sequence[float], k: int) -> list[int]:
        rows = self._db.execute(
            "select rowid from v where embedding match ? and k = ? order by distance",
            (self._serialize(list(query)), k),
        ).fetchall()
        return [int(r[0]) for r in rows]


def available_backends() -> dict[str, Callable[[Sequence[Sequence[float]]], object]]:
    """The backends that can be built here, by name. The pure-Python and NumPy ones always can."""
    found: dict[str, Callable] = {"python": PythonScan, "numpy": NumpyScan}
    try:
        import faiss  # noqa: F401

        found["faiss-flat"], found["faiss-hnsw"] = FaissFlat, FaissHNSW
    except ImportError:
        pass
    try:
        import sqlite_vec  # noqa: F401

        found["sqlite-vec"] = SqliteVec
    except ImportError:
        pass
    return found
