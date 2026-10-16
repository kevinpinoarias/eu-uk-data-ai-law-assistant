"""
Pack what the service image needs but Git does not hold (the chunks and the saved BGE-M3 vectors) into one zip, so
that the deploy workflow can build the image from a clean checkout.

The Dockerfile copies data/chunks and the BGE-M3 vector file with its key list. Those are built here from the
downloaded laws (the build is slow and the downloads are rate-limited), so they are git-ignored. Run this after any
re-chunking or re-embedding, then upload the zip to a GitHub release (see docs/DEPLOYMENT.md):

    python scripts/make_data_bundle.py            # writes dist/data-bundle.zip and prints its fingerprint

The bundle carries the law texts under their publishers' reuse terms (SOURCES.md, NOTICE): publish it only
alongside those credits.
"""

from __future__ import annotations

import hashlib
import sys
import zipfile
from pathlib import Path

VECTOR_FILES = ("data/indexes/bge-m3.f32", "data/indexes/bge-m3.keys.json")
CHUNK_DIR = "data/chunks"
CREDITS = "NOTICE"  # the publishers' credit lines travel with the texts


def make_bundle(root: Path, out: Path) -> list[str]:
    """Write the zip and return the names inside it. A missing vector file or an empty chunk folder is an error."""
    for name in VECTOR_FILES:
        if not (root / name).is_file():
            raise FileNotFoundError(f"{name} is missing: embed the chunks first (see README)")
    chunk_files = sorted(p for p in (root / CHUNK_DIR).glob("*") if p.is_file())
    if not chunk_files:
        raise FileNotFoundError(f"{CHUNK_DIR} has no files: run the chunker first")
    if not (root / CREDITS).is_file():
        raise FileNotFoundError(f"{CREDITS} is missing: the texts must travel with their credit lines")
    names = [CREDITS] + [p.relative_to(root).as_posix() for p in chunk_files] + list(VECTOR_FILES)
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name in names:
            bundle.write(root / name, name)
    return names


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    out = root / "dist" / "data-bundle.zip"
    names = make_bundle(root, out)
    digest = hashlib.sha256(out.read_bytes()).hexdigest()
    print(f"{out}: {len(names)} files, {out.stat().st_size / 1e6:.1f} MB, sha256 {digest}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
