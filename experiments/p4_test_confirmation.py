"""
P4.6: the one confirmation of the answer layer on the TEST half (gold version 2). Reads the 40 test questions
once, for ONE chosen configuration, against the memory-only baseline.

PRE-REGISTRATION (written 15 October 2026, before any test question has been answered by the answer layer)

Which configuration is confirmed (chosen by this rule from development results only, and passed on the command
line as --config; the script refuses to run without it):
  A  five passages, current text unless a date is stated (the configuration measured in P4.4);
  D  A plus version-aware search and the in-force date shown to the writer (experiment p4_version_aware.py).
Rule: D is confirmed if, on the development half under gold version 2, no question judged 'yes' under A is not
'yes' under D, and at least one of the version or date questions (q044, q048, q049, q051) improves on my own
reading of its answer; otherwise A is confirmed. If p4_version_aware.py has not been completed, A is confirmed.
The rewriting step is not part of either configuration (decision 84).
Data: the 40 test questions of gold version 2 (31 retrieve, 4 table, 5 refuse; the counts are printed).
Everything else as in p4_answers.py: the model router and table picker, BGE-M3 with copies collapsed, the writer
at temperature 0, every quotation checked in code, the same judge, the same memory baseline N (no retrieval).
Measures: routing outcomes (table rows right, refusals right, retrieve questions refused); on the retrieve
questions, answered and declined counts, judged correctness with a 95 % bootstrap interval, support of the
claims by their quotations, citation hit and coverage, strict precision; the paired difference in correctness
against N; seconds and tokens per question (all calls are real here, none cached); a breakdown by type and by
language; every retrieve question not judged correct.
Rule for the claim: the project's claim stays "checked quotations, named sources and versions, refusals", and it
claims an accuracy gain over memory only if the lower end of the paired interval against N is above 0. Whatever
comes out is reported in the README next to the development numbers, including a failure.
Stated expectation (can be wrong): correctness 0.45 to 0.65 (lower than on the development half, which was looked
at); the interval of the difference from N includes 0; 15 to 30 percent of retrieve questions declined; the four
table questions right; the five refusals right; the judge generous as before.
Cost: about 200 model calls; run it on a day with at least that much of the cheap model's allowance left.
Guard: refuses a second read (it looks for its own section in docs/EXPERIMENTS.md); --second-read overrides, logged.

Run: python experiments/p4_test_confirmation.py --config A|D --log   (needs GEMINI_API_KEY in .env)
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date
from statistics import mean, median

from p4_answers import MEMORY_INSTRUCTIONS, build_pipeline, cited_stats, make_parts

from law_assistant import settings
from law_assistant.answer.generate import LANGUAGE_NAMES
from law_assistant.answer.judge import score_of
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.metrics import bootstrap_ci, paired_bootstrap
from law_assistant.facts.table import read_facts
from law_assistant.llm.gemini import GeminiGenerator
from law_assistant.retrieval.bge import BGEEmbedder

LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"
MARKER = "## P4.6 test-half confirmation of the answer layer"
BGE_DIR = settings.PROJECT_ROOT / "data" / "models" / "bge-m3"


def main() -> int:
    import torch

    if "--config" not in sys.argv or sys.argv[sys.argv.index("--config") + 1] not in ("A", "D"):
        print("choose the configuration by the pre-registered rule: --config A or --config D")
        return 2
    config = sys.argv[sys.argv.index("--config") + 1]
    if MARKER in LOG.read_text(encoding="utf-8") and "--second-read" not in sys.argv:
        print(
            "the test half has already been read for the answer layer; --second-read to read it again (logged)"
        )
        return 2
    settings.load_env_file()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    by_id = {c.id: c for c in chunks}
    questions = [q for q in read_gold(settings.GOLD_DIR / "questions.jsonl") if q.split == "test"]
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")
    facts = read_facts(settings.FACTS_DIR / "legal_facts.jsonl")
    generator = GeminiGenerator.from_env()
    parts = make_parts(
        chunks, by_id, BGEEmbedder.load(BGE_DIR, device=device, max_length=1024), generator, facts
    )
    pipeline = build_pipeline(parts, 5, version_aware=(config == "D"), dates=(config == "D"))
    judge, memory = parts["judge"], parts["memory"]

    rows = {}
    for q in questions:
        before = len(generator.calls)
        result = pipeline.ask(q.text)
        calls = generator.calls[before:]
        row = {"result": result, "seconds": sum(c.seconds for c in calls), "calls": calls}
        row["correct"] = (
            judge.correctness(q.text, q.expected_answer, result.text)
            if result.kind in ("answer", "table")
            else ("no", "no answer given")
        )
        if result.kind == "answer":
            row["support"] = judge.support(
                result.text.split("\n\n")[0], [s.quote for s in result.sources if s.quote]
            )
            row.update(cited_stats(q, result, by_id))
        rows[q.id] = row

    retrieve = [q for q in questions if q.route == "retrieve"]
    table = [q for q in questions if q.route == "table"]
    refuse = [q for q in questions if q.route == "refuse"]
    baseline = {}
    for q in retrieve:
        prompt = f"Answer in: {LANGUAGE_NAMES[q.language]}\nQuestion: {q.text}"
        answer = memory.generate(prompt, system=MEMORY_INSTRUCTIONS, temperature=0.0, max_output_tokens=600)
        baseline[q.id] = judge.correctness(q.text, q.expected_answer, answer)

    kinds = [rows[q.id]["result"].kind for q in retrieve]
    answered = [q for q in retrieve if rows[q.id]["result"].kind == "answer"]
    a_scores = [score_of(rows[q.id]["correct"][0]) for q in retrieve]
    n_scores = [score_of(baseline[q.id][0]) for q in retrieve]
    corr, lo, hi = bootstrap_ci(a_scores)
    n_corr, n_lo, n_hi = bootstrap_ci(n_scores)
    paired = paired_bootstrap(n_scores, a_scores)
    second = " (a SECOND read of the test half)" if "--second-read" in sys.argv else ""
    out = [
        f"### P4.6 the answer layer on the TEST half, configuration {config}, gold version {manifest['version']}"
        f"{second} ({len(questions)} questions: {len(retrieve)} retrieve, {len(table)} table, {len(refuse)} refuse)",
        "",
        f"- retrieve questions: answered {kinds.count('answer')}, declined {kinds.count('abstained')}, refused "
        f"{kinds.count('refused')}, from the table {kinds.count('table')}; correctness {corr:.2f} ({lo:.2f} to {hi:.2f})",
        f"- baseline N (the same model from memory, no retrieval): correctness {n_corr:.2f} ({n_lo:.2f} to {n_hi:.2f})",
        f"- answer layer against N, correctness: difference {paired.difference:+.3f}, 95 % interval "
        f"{paired.low:+.3f} to {paired.high:+.3f}; accuracy gain claimed: {'yes' if paired.low > 0 else 'no'}",
    ]
    if answered:
        out.append(
            f"- among the {len(answered)} answered: support "
            f"{mean(score_of(rows[q.id]['support'][0]) for q in answered):.2f}; a cited source satisfies a primary "
            f"gold provision {mean(rows[q.id]['hit'] for q in answered):.2f}; coverage "
            f"{mean(rows[q.id]['coverage'] for q in answered if rows[q.id]['coverage'] is not None):.2f}; strict "
            f"precision {mean(rows[q.id]['precision'] for q in answered if rows[q.id]['precision'] is not None):.2f}"
        )
    right_rows = sum(
        rows[q.id]["result"].kind == "table" and rows[q.id]["result"].trace["fact_key"] == q.table_key
        for q in table
    )
    right_refusals = sum(
        rows[q.id]["result"].kind == "refused" and rows[q.id]["result"].reason == q.refusal_reason
        for q in refuse
    )
    seconds = sorted(r["seconds"] for r in rows.values())
    tokens_in = mean(sum(c.prompt_tokens for c in r["calls"]) for r in rows.values())
    tokens_out = mean(sum(c.output_tokens for c in r["calls"]) for r in rows.values())
    out += [
        f"- table questions answered from the right row: {right_rows}/{len(table)}; refusals refused with the right "
        f"reason: {right_refusals}/{len(refuse)}; retrieve questions refused: {kinds.count('refused')}",
        f"- model time per question (all calls real): mean {mean(seconds):.2f} s, median {median(seconds):.2f} s, "
        f"slowest {seconds[-1]:.2f} s; tokens per question {tokens_in:.0f} in, {tokens_out:.0f} out (the pipeline's "
        "calls only; judge and baseline calls are separate)",
        "",
        "Correctness by question type and language (answer layer, N; number of questions):",
        "",
    ]
    for title, key in (("type", lambda q: q.type), ("language", lambda q: q.language)):
        groups: dict[str, list[int]] = {}
        for i, q in enumerate(retrieve):
            groups.setdefault(key(q), []).append(i)
        out += [
            f"- {title} {name}: {mean(a_scores[i] for i in idx):.2f}, {mean(n_scores[i] for i in idx):.2f} (n = {len(idx)})"
            for name, idx in sorted(groups.items())
        ]
    out += [
        "",
        "Retrieve questions not judged correct, and any table or refuse question that went the wrong way:",
        "",
    ]
    for q in questions:
        r = rows[q.id]
        expected = {"retrieve": "answer", "table": "table", "refuse": "refused"}[q.route]
        if q.route == "retrieve" and r["correct"][0] != "yes":
            out.append(f"- {q.id} ({q.type}): {r['result'].kind}, {r['correct'][0]}: {r['correct'][1]}")
        elif q.route != "retrieve" and r["result"].kind != expected:
            out.append(f"- {q.id} ({q.route}): went to {r['result'].kind}")
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n{MARKER}, run {date.today().isoformat()} "
            f"(commit {commit}; gold version {manifest['version']}, fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
