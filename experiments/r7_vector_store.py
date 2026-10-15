"""
R7: does a vector library or database beat the plain loop? The project's search multiplies the question's vector
with each of the 3,831 chunk vectors in Python. Compared here: that loop, one NumPy matrix product, FAISS (exact
and approximate) and an embedded database (SQLite with the sqlite-vec extension). No model calls and no
embedding of chunks: the saved BGE-M3 vectors and the cached question vectors are used.

PRE-REGISTRATION (written 15 October 2026 before any backend has been timed or scored)

Backends (all counted): python (the reference), numpy, faiss-flat (exact), faiss-hnsw (approximate: 32
neighbours per node, 64 candidates examined per question), sqlite-vec (exact, cosine, a vec0 table).
Part A, accuracy, real data: for the 31 development retrieval questions, the top 10 of each backend against the
python reference (overlap@10 and whether the order is identical), and recall@5 and MRR on the gold.
Part B, speed, real data (3,831 vectors of 1,024 numbers): build time and the median and 95th-percentile time of
one search over 200 searches (31 questions repeated).
Part C, scaling, synthetic: random unit vectors of 1,024 numbers, 3,831, 38,310 and 153,240 of them (the real
size, 10 times and 40 times), one search each, median of 20 (python and sqlite-vec only up to 38,310, python with
3 repetitions because it is slow). Random
vectors say nothing about accuracy, so Part C reports time only (and the approximate index's overlap with the exact
one, for information).
Decision rule: a backend replaces the plain-Python loop in the shipped pipeline if (a) for exact backends its top
10 is identical on all 31 questions, or for the approximate one overlap@10 is at least 0.99 and recall@5 is
unchanged; and (b) it is at least 5 times faster per search at the real size; and (c) its extra dependency
is justified by the size at which the plain loop becomes too slow for a 1-second answer budget. Otherwise the loop
stays. The size at which the choice starts to matter is reported either way.
Stated expectation (can be wrong): every exact backend returns the identical top 10; HNSW's overlap is at least
0.95; at 3,831 vectors NumPy and FAISS take well under 5 ms and the plain loop over 100 ms, so all the library
backends are "5 times faster" but none changes what a user sees (the embedding of the question and the model
calls take far longer); sqlite-vec is slower than NumPy at this size; the approximate index only pays off beyond
about 100,000 vectors.

Run: python experiments/r7_vector_store.py [--log]
"""

from __future__ import annotations

import os
import random
import statistics
import subprocess
import sys
import tempfile
import time
from datetime import date

from law_assistant import settings
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.metrics import metric_values
from law_assistant.retrieval.bge import document_prompt, query_prompt
from law_assistant.retrieval.dense import DenseIndex
from law_assistant.retrieval.report import summarise_with_ci
from law_assistant.retrieval.runner import evaluate, select
from law_assistant.retrieval.stores import available_backends

STORE = settings.PROJECT_ROOT / "data" / "indexes" / "bge-m3"
LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"
SIZES = (3_831, 38_310, 153_240)


class NoEmbedder:
    """Every vector is in the saved store; a call means a missing vector and is an error."""

    name = "bge-m3"

    def embed_texts(self, texts):
        raise RuntimeError("a vector is missing from the saved store")


def timed(fn, repeats):
    times = []
    for _ in range(repeats):
        start = time.perf_counter()
        fn()
        times.append((time.perf_counter() - start) * 1000)
    return times


def percentile(values, p):
    ordered = sorted(values)
    return ordered[min(len(ordered) - 1, int(p * len(ordered)))]


def random_unit_vectors(n, dim, seed):
    import numpy as np

    rng = np.random.default_rng(seed)
    matrix = rng.standard_normal((n, dim), dtype=np.float32)
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True)
    return matrix


def main() -> int:
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")
    index = DenseIndex(
        chunks, NoEmbedder(), STORE, name="bge-m3",
        document_prompt_fn=document_prompt, query_prompt_fn=query_prompt, persist_queries=False,
    )  # fmt: skip
    vectors = index._vectors
    ids = index._ids
    queries = [index._query_vector(q.text) for q in questions]
    backends = available_backends()
    out = [f"### R7 vector search backends ({len(vectors):,} vectors of {len(vectors[0])} numbers)", ""]

    built, runs, build_ms = {}, {}, {}
    for name, make in backends.items():
        start = time.perf_counter()
        built[name] = make(vectors)
        build_ms[name] = (time.perf_counter() - start) * 1000
        runs[name] = {
            q.id: [ids[i] for i in built[name].search(v, 10)] for q, v in zip(questions, queries, strict=True)
        }

    reference = runs["python"]
    out += [
        "**Part A: accuracy on the development questions** (overlap of the top 10 with the plain loop; identical order; recall@5; MRR)",
        "",
    ]
    out += ["| Backend | overlap@10 | identical order | recall@5 | MRR |", "|---|---|---|---|---|"]
    for name in backends:
        overlap = statistics.mean(len(set(runs[name][q.id]) & set(reference[q.id])) / 10 for q in questions)
        identical = sum(runs[name][q.id] == reference[q.id] for q in questions)
        scores = evaluate(questions, runs[name], chunks)
        summary = summarise_with_ci(scores)
        recall = summary["recall@5"][0] if isinstance(summary["recall@5"], tuple) else summary["recall@5"]
        mrr = statistics.mean(metric_values(scores, "mrr"))
        out.append(f"| {name} | {overlap:.3f} | {identical}/{len(questions)} | {recall:.3f} | {mrr:.3f} |")

    out += ["", "**Part B: speed on the real vectors** (milliseconds)", ""]
    out += ["| Backend | build | search median | search 95th percentile |", "|---|---|---|---|"]
    for name in backends:
        reps = 2 if name == "python" else 20
        times = []
        for _ in range(reps):
            for v in queries:
                start = time.perf_counter()
                built[name].search(v, 10)
                times.append((time.perf_counter() - start) * 1000)
        out.append(
            f"| {name} | {build_ms[name]:.0f} | {statistics.median(times):.2f} | {percentile(times, 0.95):.2f} |"
        )

    out += [
        "",
        "**Part C: speed as the set grows** (synthetic random vectors; median milliseconds per search; build in seconds)",
        "",
    ]
    header = "| Backend | " + " | ".join(f"{n:,} vectors" for n in SIZES) + " |"
    out += [header, "|---|" + "---|" * len(SIZES)]
    rows = {name: [] for name in backends}
    overlaps = []
    for n in SIZES:
        matrix = random_unit_vectors(n, 1024, seed=n)
        query = random_unit_vectors(1, 1024, seed=n + 1)[0].tolist()
        rows_here = matrix.tolist() if n <= 40_000 else None
        exact = None
        for name, make in backends.items():
            if name == "python" and n > 40_000:
                rows[name].append("not run")
                continue
            if name == "sqlite-vec" and n > 40_000:
                rows[name].append("not run")
                continue
            start = time.perf_counter()
            backend = make(rows_here if (rows_here is not None) else matrix)
            build_s = time.perf_counter() - start
            reps = 3 if name == "python" else 20
            ms = statistics.median(timed(lambda b=backend, q=query: b.search(q, 10), reps))
            rows[name].append(f"{ms:.2f} (build {build_s:.1f} s)")
            if name == "faiss-flat":
                exact = set(backend.search(query, 10))
            if name == "faiss-hnsw" and exact is not None:
                overlaps.append((n, len(exact & set(backend.search(query, 10))) / 10))
    for name in backends:
        out.append(f"| {name} | " + " | ".join(rows[name]) + " |")
    if overlaps:
        out += [
            "",
            "Approximate index overlap@10 with the exact one on random vectors (information only): "
            + ", ".join(f"{n:,}: {o:.2f}" for n, o in overlaps),
        ]

    with tempfile.TemporaryDirectory() as tmp:
        disk = (
            backends["sqlite-vec"](vectors, os.path.join(tmp, "v.db")) if "sqlite-vec" in backends else None
        )
        size = os.path.getsize(os.path.join(tmp, "v.db")) / 1e6 if disk else 0
        if disk:
            disk.close()
    out += [
        "",
        f"On disk, the sqlite-vec database for the real vectors is {size:.0f} MB; the raw float32 vectors are "
        f"{len(vectors) * len(vectors[0]) * 4 / 1e6:.0f} MB.",
    ]
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## R7 vector search backends, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    random.seed(0)
    sys.exit(main())
