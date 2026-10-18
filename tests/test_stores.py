"""
Tests for the vector search backends (R7): every exact backend must return the same nearest vectors as the
plain-Python scan the project started with. FAISS and sqlite-vec are optional, so their tests skip without them.
"""

from __future__ import annotations

import random

import pytest

from law_assistant.retrieval.stores import NumpyScan, PythonScan, available_backends


def unit_vectors(n, dim, seed):
    rng = random.Random(seed)
    out = []
    for _ in range(n):
        v = [rng.gauss(0, 1) for _ in range(dim)]
        norm = sum(x * x for x in v) ** 0.5
        out.append([x / norm for x in v])
    return out


VECTORS = unit_vectors(200, 16, seed=1)
QUERIES = unit_vectors(10, 16, seed=2)


def test_the_python_scan_returns_the_nearest_vectors_best_first():
    scan = PythonScan(VECTORS)
    top = scan.search(VECTORS[7], 3)
    assert top[0] == 7 and len(top) == 3 and len(set(top)) == 3


def test_a_vector_is_its_own_nearest_neighbour_in_every_available_backend():
    for name, make in available_backends().items():
        backend = make(VECTORS)
        assert backend.search(VECTORS[42], 1) == [42], name


def test_without_numpy_only_the_backends_that_can_be_built_are_listed(monkeypatch):
    # CI installs only the dev extras, so NumPy is absent there; the list must not promise it.
    import sys

    monkeypatch.setitem(sys.modules, "numpy", None)  # makes `import numpy` raise ImportError
    monkeypatch.setitem(sys.modules, "faiss", None)
    monkeypatch.setitem(sys.modules, "sqlite_vec", None)
    found = available_backends()
    assert list(found) == ["python"]
    assert found["python"](VECTORS).search(VECTORS[3], 1) == [3]


def test_numpy_gives_the_same_ranking_as_the_python_scan():
    pytest.importorskip("numpy")
    reference, numpy_scan = PythonScan(VECTORS), NumpyScan(VECTORS)
    for q in QUERIES:
        assert numpy_scan.search(q, 10) == reference.search(q, 10)


@pytest.mark.parametrize("name", ["faiss-flat", "sqlite-vec"])
def test_the_exact_backends_agree_with_the_python_scan(name):
    backends = available_backends()
    if name not in backends:
        pytest.skip(f"{name} is not installed")
    reference, other = PythonScan(VECTORS), backends[name](VECTORS)
    for q in QUERIES:
        assert other.search(q, 10) == reference.search(q, 10)


def test_the_approximate_index_finds_nearly_the_same_neighbours():
    backends = available_backends()
    if "faiss-hnsw" not in backends:
        pytest.skip("faiss is not installed")
    reference, approx = PythonScan(VECTORS), backends["faiss-hnsw"](VECTORS)
    overlap = [len(set(reference.search(q, 10)) & set(approx.search(q, 10))) / 10 for q in QUERIES]
    assert sum(overlap) / len(overlap) >= 0.9


def test_asking_for_more_than_exists_returns_what_exists():
    assert len(PythonScan(VECTORS[:3]).search(QUERIES[0], 10)) == 3
    pytest.importorskip("numpy")
    assert len(NumpyScan(VECTORS[:3]).search(QUERIES[0], 10)) == 3
