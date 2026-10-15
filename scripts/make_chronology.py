"""
Write docs/CHRONOLOGY.md from the git history: every commit, oldest first, with its date, hash, subject and the
body lines that explain it. Regenerate after any commit: `python scripts/make_chronology.py`.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEPARATOR = "\x1e"


def main() -> int:
    fmt = f"%h{SEPARATOR}%ad{SEPARATOR}%s{SEPARATOR}%b{SEPARATOR}END"
    log = subprocess.run(
        ["git", "log", "--reverse", f"--pretty=format:{fmt}", "--date=format:%Y-%m-%d %H:%M"],
        capture_output=True, text=True, cwd=ROOT, check=True, encoding="utf-8",
    ).stdout  # fmt: skip
    entries = [e.strip("\n") for e in log.split(f"{SEPARATOR}END") if e.strip()]
    lines = [
        "# Chronology: every commit, oldest first",
        "",
        "Generated from the git history by `scripts/make_chronology.py`; regenerate after a commit. It answers "
        "\"what was done when\"; the reasoning is in `DECISIONS.md`, the story in `JOURNEY.md`, the results in "
        "`EXPERIMENT_INDEX.md`. Nothing is pushed by the assistant: pushing is done by the project owner.",
        "",
        "| # | When | Commit | What |",
        "|---|---|---|---|",
    ]
    details = []
    for n, entry in enumerate(entries, start=1):
        short, when, subject, body, *_ = entry.split(SEPARATOR) + [""]
        lines.append(f"| {n} | {when} | `{short.strip()}` | {subject.strip()} |")
        if body.strip():
            details.append(f"### {n}. `{short.strip()}` {subject.strip()}\n\n{body.strip()}\n")
    out = "\n".join(lines) + "\n\n## What each commit said\n\n" + "\n".join(details)
    (ROOT / "docs" / "CHRONOLOGY.md").write_text(out, encoding="utf-8", newline="\n")
    print(f"wrote docs/CHRONOLOGY.md with {len(entries)} commits")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
