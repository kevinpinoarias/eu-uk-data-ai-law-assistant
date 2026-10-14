"""
Chunk every parsed document and check the result: `python -m law_assistant.chunk.run_chunk`.

Reads `data/parsed/*.jsonl`, writes `data/chunks/<same name>.jsonl` and a `manifest.json` with the cap,
the input hash and the counts of each file, so a rebuild can be compared with an earlier one. The same inputs
and cap always give byte-identical output files.
"""

from __future__ import annotations

import hashlib
import json
import statistics
import sys

from law_assistant import settings
from law_assistant.chunk.checks import check_chunks
from law_assistant.chunk.chunker import DEFAULT_MAX_WORDS, chunk_provisions
from law_assistant.chunk.store import write_chunks
from law_assistant.parse.store import read_jsonl


def build(max_words: int = DEFAULT_MAX_WORDS) -> tuple[dict, list[str]]:
    files: dict[str, dict] = {}
    problems: list[str] = []
    for source in sorted(settings.PARSED_DIR.glob("*.jsonl")):
        provisions = read_jsonl(source)
        chunks = chunk_provisions(provisions, max_words=max_words)
        for problem in check_chunks(provisions, chunks, max_words=max_words):
            problems.append(f"{source.stem}: {problem}")
        output = settings.CHUNKS_DIR / source.name
        write_chunks(output, chunks)
        sizes = [c.words for c in chunks]
        files[source.stem] = {
            "input_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
            "output_sha256": hashlib.sha256(output.read_bytes()).hexdigest(),
            "provisions": len(provisions),
            "chunks": len(chunks),
            "units_split": len({(c.unit, c.unit_path) for c in chunks if c.parts > 1}),
            "words_median": int(statistics.median(sizes)),
            "words_max": max(sizes),
        }
    manifest = {"max_words": max_words, "files": files}
    (settings.CHUNKS_DIR / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n"
    )
    return manifest, problems


def main() -> int:
    manifest, problems = build()
    print(f"cap {manifest['max_words']} words")
    print(f"{'document':44}{'provisions':>11}{'chunks':>8}{'split units':>12}{'median':>8}{'max':>6}")
    for name, f in manifest["files"].items():
        print(
            f"{name:44}{f['provisions']:11}{f['chunks']:8}{f['units_split']:12}{f['words_median']:8}"
            f"{f['words_max']:6}"
        )
    total = sum(f["chunks"] for f in manifest["files"].values())
    print(f"total chunks {total} | problems {len(problems)}")
    for problem in problems:
        print("  PROBLEM:", problem)
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
