"""
The split and the freeze of the gold set (step 2.5).

The split puts every question in "dev" (used to tune, as often as needed) or "test" (looked at once per
decision), balanced within each type and language so that neither half is lopsided, and reproducible from a
seed. The freeze records, in a manifest, the SHA-256 fingerprint of the whole set with the date, the seed, the
counts and a plain statement of how the set was reviewed; any later edit changes the fingerprint and is
detected, and counts as a new version of the set (results from different versions are not comparable).
"""

from __future__ import annotations

import json
import random
from collections import Counter
from collections.abc import Sequence
from dataclasses import replace
from pathlib import Path

from law_assistant.evaluation.gold import GoldQuestion, freeze_hash

MANIFEST_VERSION = 1


def split_counts(questions: Sequence[GoldQuestion]) -> dict[str, int]:
    counts = Counter(q.split for q in questions)
    return {name: counts.get(name, 0) for name in ("dev", "test")}


def assign_splits(questions: Sequence[GoldQuestion], *, seed: int) -> list[GoldQuestion]:
    """A copy of the questions with `split` set, balanced within each (type, language) cell."""
    if any(q.split is not None for q in questions):
        raise ValueError("the set is already split; a new split makes a new version of the set")
    rng = random.Random(seed)
    cells: dict[tuple[str, str], list[GoldQuestion]] = {}
    for q in sorted(questions, key=lambda q: q.id):
        cells.setdefault((q.type, q.language), []).append(q)
    assigned: dict[str, str] = {}
    totals = {"dev": 0, "test": 0}
    for key in sorted(cells):
        members = cells[key][:]
        rng.shuffle(members)
        n_dev = len(members) // 2
        if len(members) % 2 and totals["dev"] <= totals["test"]:
            n_dev += 1  # an odd cell gives its extra question to the smaller half, so the halves end level
        for i, q in enumerate(members):
            assigned[q.id] = "dev" if i < n_dev else "test"
        totals["dev"] += n_dev
        totals["test"] += len(members) - n_dev
    return [replace(q, split=assigned[q.id]) for q in questions]


def build_manifest(questions: Sequence[GoldQuestion], *, date: str, seed: int, review: str) -> dict:
    retrieval = Counter(q.split for q in questions if q.route == "retrieve")
    return {
        "version": MANIFEST_VERSION,
        "frozen": date,
        "sha256": freeze_hash(questions),
        "questions": len(questions),
        "seed": seed,
        "split": split_counts(questions),
        "by_type": dict(sorted(Counter(q.type for q in questions).items())),
        "retrieval_questions": {name: retrieval.get(name, 0) for name in ("dev", "test")},
        "review": review,
    }


def write_manifest(path: Path, manifest: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")


def read_manifest(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def check_manifest(questions: Sequence[GoldQuestion], manifest: dict) -> list[str]:
    """Problems if the set no longer matches the manifest it was frozen with."""
    problems = []
    if len(questions) != manifest["questions"]:
        problems.append(f"the set has {len(questions)} questions, the manifest {manifest['questions']}")
    if any(q.split is None for q in questions):
        problems.append("a question has no split")
    elif split_counts(questions) != manifest["split"]:
        problems.append(f"the split is {split_counts(questions)}, the manifest {manifest['split']}")
    if freeze_hash(questions) != manifest["sha256"]:
        problems.append("the set has changed since it was frozen (its fingerprint differs from the manifest)")
    return problems
