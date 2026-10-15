"""
P4.7: what does the system still do when the language model cannot be reached? With every model call failing,
the pipeline routes with plain rules, finds a table row by embedding similarity, refuses with fixed messages and,
for questions that need an answer written, shows the most relevant passages without writing anything.

PRE-REGISTRATION (written 15 October 2026 before this mode has been run on any gold question)

Setup: the real pipeline, real BGE-M3 search and real table matcher (threshold 0.65, from P4.2), but the router,
the table picker and the answer writer all raise an error as if the model's allowance were used up. Data: the 40
development questions (gold version 2): 31 retrieve, 4 table, 5 refuse. No model calls, no quota.
Measures:
- table questions: answered from the right row (of 4);
- refusals: refused with the right reason (of 5);
- wrong behaviour on the other questions: retrieve questions refused (false refusals) or answered from the table
  (false figures, the dangerous error);
- retrieve questions: how many end in the "passages only" mode, and in how many of those the three shown passages
  contain a primary gold provision (the share of users who would see the right law even with no answer written);
- seconds per question (no model, so the retrieval and rules only).
Decision rule (for whether degraded mode may be switched on in the shipped service): on if there are no false
refusals and no more than one false figure on the development half, and every refusal is right; the false figure,
if any, is reported question by question. Otherwise the degraded mode answers only refusals and passages (no
table figure from similarity) until fixed.
Stated expectation (can be wrong): refusals 5/5; table 3/4 (the matcher confused two deadlines in P4.2); one false
figure (q023, which the rule router sends to the table); no false refusals; the three shown passages contain a
primary provision for about half of the retrieve questions (BGE-M3's recall@5 is 0.53).

Run: python experiments/p4_degraded.py [--log]
"""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import date
from statistics import mean

from law_assistant import settings
from law_assistant.answer.facts_lookup import FactMatcher, LLMFactPicker
from law_assistant.answer.generate import AnswerWriter
from law_assistant.answer.pipeline import AnswerPipeline
from law_assistant.answer.router import LLMRouter, RuleRouter
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.relevance import matches, targets_of
from law_assistant.facts.table import read_facts
from law_assistant.llm.gemini import LLMError
from law_assistant.retrieval.bge import BGEEmbedder, document_prompt, query_prompt
from law_assistant.retrieval.dense import DenseIndex
from law_assistant.retrieval.policies import CollapsedRetriever, before_amendment_text, current_text_only

LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"
BGE_DIR = settings.PROJECT_ROOT / "data" / "models" / "bge-m3"
STORE = settings.PROJECT_ROOT / "data" / "indexes" / "bge-m3"
THRESHOLD = 0.65


class DownGenerator:
    """Every call fails, as when the model's allowance is used up."""

    model = "down"
    calls: list = []

    def generate(self, *args, **kwargs):
        raise LLMError("HTTP 429: the quota is used up")


def main() -> int:
    import torch

    device = "cuda" if torch.cuda.is_available() else "cpu"
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    by_id = {c.id: c for c in chunks}
    questions = [q for q in read_gold(settings.GOLD_DIR / "questions.jsonl") if q.split == "dev"]
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")
    facts = read_facts(settings.FACTS_DIR / "legal_facts.jsonl")
    embedder = BGEEmbedder.load(BGE_DIR, device=device, max_length=1024)

    def search(cs, name):
        index = DenseIndex(
            cs, embedder, STORE, name=name, document_prompt_fn=document_prompt,
            query_prompt_fn=query_prompt, persist_queries=False,
        )  # fmt: skip
        return CollapsedRetriever(index, by_id, by="copies", depth=50)

    down = DownGenerator()
    pipeline = AnswerPipeline(
        router=LLMRouter(down), picker=LLMFactPicker(facts, down), writer=AnswerWriter(down),
        current=search(current_text_only(chunks), "bge-m3-current"), full=search(chunks, "bge-m3"),
        original=search(before_amendment_text(chunks), "bge-m3-original"), chunks=chunks, k=5,
        fallback_router=RuleRouter(),
        fallback_matcher=FactMatcher(facts, embedder.embed_texts, threshold=THRESHOLD),
    )  # fmt: skip

    rows = {}
    for q in questions:
        start = time.perf_counter()
        rows[q.id] = (pipeline.ask(q.text), time.perf_counter() - start)
    table = [q for q in questions if q.route == "table"]
    refuse = [q for q in questions if q.route == "refuse"]
    retrieve = [q for q in questions if q.route == "retrieve"]
    right_rows = [
        q for q in table if rows[q.id][0].kind == "table" and rows[q.id][0].trace["fact_key"] == q.table_key
    ]
    right_refusals = [
        q for q in refuse if rows[q.id][0].kind == "refused" and rows[q.id][0].reason == q.refusal_reason
    ]
    false_refusals = [q for q in retrieve + table if rows[q.id][0].kind == "refused"]
    false_figures = [q for q in retrieve if rows[q.id][0].kind == "table"]
    passages_only = [q for q in retrieve if rows[q.id][0].kind == "sources"]

    def shows_primary(q):
        shown = [by_id[s.chunk_id] for s in rows[q.id][0].sources]
        return any(matches(c, t.gold) for c in shown for t in targets_of(q) if t.grade == 2)

    seeing = [q for q in passages_only if shows_primary(q)]
    wrong_table = [q for q in table if q not in right_rows]
    out = [
        f"### P4.7 degraded mode: every model call fails ({len(questions)} development questions, gold version "
        f"{manifest['version']})",
        "",
        f"- table questions answered from the right row: {len(right_rows)}/{len(table)}"
        + (
            f" (wrong: {[(q.id, rows[q.id][0].kind, rows[q.id][0].trace['fact_key']) for q in wrong_table]})"
            if wrong_table
            else ""
        ),
        f"- refusals refused with the right reason: {len(right_refusals)}/{len(refuse)}",
        f"- false refusals (a retrieve or table question refused): {len(false_refusals)}"
        + (f" {[q.id for q in false_refusals]}" if false_refusals else ""),
        f"- false figures (a retrieve question answered from the table): {len(false_figures)}"
        + (f" {[(q.id, rows[q.id][0].trace['fact_key']) for q in false_figures]}" if false_figures else ""),
        f"- retrieve questions ending in passages only: {len(passages_only)}/{len(retrieve)}; the three shown "
        f"passages contain a primary gold provision for {len(seeing)} of them ({len(seeing) / max(len(passages_only), 1):.0%})",
        f"- seconds per question: mean {mean(t for _, t in rows.values()):.2f}, slowest {max(t for _, t in rows.values()):.2f}",
        f"- every result marked degraded: {all(r.trace['degraded'] for r, _ in rows.values())}",
        "",
        "Outcome of every question (kind): " + ", ".join(f"{q.id} {rows[q.id][0].kind}" for q in questions),
    ]
    switch_on = not false_refusals and len(false_figures) <= 1 and len(right_refusals) == len(refuse)
    out.append(f"\nDecision rule met (degraded mode may be switched on): {'yes' if switch_on else 'NO'}.")
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## P4.7 degraded mode, dev half, run {date.today().isoformat()} "
            f"(commit {commit}; gold version {manifest['version']}, fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
