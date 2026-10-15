"""
P4.5: choosing the right version of the law for the question. P4.4 showed two failures of the first design
(variant A, which searches the current text unless the question states an early date, and then searches every
version): q044, asked "as of the start of 2026", was answered with the dates from the 2026 amending regulation,
which did not exist yet, and the judge wrongly passed it; q048, a question about the wording "as first
published", was searched in the current text only and answered wrongly.

PRE-REGISTRATION (written 15 October 2026 after P4.4 was scored; this variant exists because of those
development failures, so it is a tuned variant and only the test half can show whether it generalises)

AMENDMENT (same day, before D was run): the second independent review of the gold set showed that the answers to
three 'since when' questions (q049, q051 on the development half) need the date the wording took effect, which
the chunks carry as `in_force_from` but the writer was never shown (in the first run q049 was declined and q051
was judged 'partly' for lacking its date). D therefore also shows the writer each passage's 'in force from' date
and a rule for using it. The two changes are tested together as D; they cannot be separated with five version
questions and two date questions in the development half. Gold version 2 (the review's corrections) is used.

Variant D (counted in the experiment tally), otherwise identical to A (k = 5): a question dated before the
consolidated AI Act (27 July 2026) is searched in the text as first published WITHOUT the 2026 amending
regulation; a question that asks about the wording as first published ("as first published", "Official Journal",
"texto original", ...) is searched in every version, so original and current can be compared; every other
question is searched in the current text.
Data: the 40 development questions. Only the questions whose search changes get a new answer; the rest reuse
the cached answer of A (same prompt, same temperature-0 model).
Measures: correctness (model judge), compared with A with a paired bootstrap; the list of questions whose
verdict changed; and a re-read of every changed answer by a person (an AI assistant reading it, stated as such),
because the judge was too generous on q044.
Decision rule: D is kept if no question that was correct in A becomes wrong in D and at least one version
question improves on my own reading; the paired interval is reported but with five version questions in the
development half it cannot decide. The test half is read once for the chosen configuration.
Stated expectation (can be wrong): q044 and q048 improve, nothing else changes, correctness moves by about +0.03.

Run: python experiments/p4_version_aware.py [--log]   (needs GEMINI_API_KEY in .env)
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date

from p4_answers import build_pipeline, make_parts

from law_assistant import settings
from law_assistant.answer.judge import score_of
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.metrics import bootstrap_ci, paired_bootstrap
from law_assistant.facts.table import read_facts
from law_assistant.llm.gemini import GeminiGenerator
from law_assistant.retrieval.bge import BGEEmbedder

LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"
BGE_DIR = settings.PROJECT_ROOT / "data" / "models" / "bge-m3"


def main() -> int:
    import torch

    settings.load_env_file()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    by_id = {c.id: c for c in chunks}
    questions = [q for q in read_gold(settings.GOLD_DIR / "questions.jsonl") if q.split == "dev"]
    retrieve = [q for q in questions if q.route == "retrieve"]
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")
    facts = read_facts(settings.FACTS_DIR / "legal_facts.jsonl")
    generator = GeminiGenerator.from_env()
    embedder = BGEEmbedder.load(BGE_DIR, device=device, max_length=1024)
    parts = make_parts(chunks, by_id, embedder, generator, facts)
    judge = parts["judge"]
    runs = {"A": build_pipeline(parts, 5), "D": build_pipeline(parts, 5, version_aware=True, dates=True)}
    results = {}
    for name, pipe in runs.items():
        results[name] = {}
        for q in retrieve:
            r = pipe.ask(q.text)
            verdict = (
                judge.correctness(q.text, q.expected_answer, r.text) if r.kind == "answer" else ("no", "none")
            )
            results[name][q.id] = (r, verdict)
    a = [score_of(results["A"][q.id][1][0]) for q in retrieve]
    d = [score_of(results["D"][q.id][1][0]) for q in retrieve]
    ca, la, ha = bootstrap_ci(a)
    cd, ld, hd = bootstrap_ci(d)
    p = paired_bootstrap(a, d)
    out = [
        f"### P4.5 version-aware search ({len(retrieve)} development retrieve questions)",
        "",
        f"- A correctness {ca:.2f} ({la:.2f} to {ha:.2f}); D correctness {cd:.2f} ({ld:.2f} to {hd:.2f})",
        f"- D against A: difference {p.difference:+.3f}, 95 % interval {p.low:+.3f} to {p.high:+.3f}",
        "",
        "Questions whose search or verdict changed (id, A verdict, D verdict, D passages):",
        "",
    ]
    for q in retrieve:
        ra, va = results["A"][q.id]
        rd, vd = results["D"][q.id]
        if ra.trace["passages"] != rd.trace["passages"] or va[0] != vd[0]:
            out.append(
                f"- {q.id} ({q.type}, as_of {q.as_of}): A {va[0]} ({ra.kind}), D {vd[0]} ({rd.kind}); "
                f"D searched {rd.trace['version_notes']}"
            )
    out += ["", "Answers of D to the questions whose search changed:", ""]
    for q in retrieve:
        ra, _ = results["A"][q.id]
        rd, vd = results["D"][q.id]
        if ra.trace["passages"] != rd.trace["passages"]:
            out += [f"**{q.id}** {q.text}", "", rd.text.split("\n\n")[0], f"(judge: {vd[0]}: {vd[1]})", ""]
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## P4.5 version-aware search, dev half, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
