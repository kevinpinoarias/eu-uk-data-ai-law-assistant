"""
P4.4: the whole answer layer on the development questions, and what retrieval buys.

PRE-REGISTRATION (written 15 October 2026 before any answer was generated for a gold question)

System: answer pipeline (src/law_assistant/answer/pipeline.py) with the model router and the model table-row
picker (P4.2, P4.3), BGE-M3 search with copies of one provision collapsed, the current text unless the question
states an earlier date, and gemini-3.1-flash-lite writing the answer (temperature 0). Every quotation is checked
in code; an answer with no valid quotation is replaced by an abstention.
Variants (all counted in the experiment tally):
  A  five passages go to the answer writer (k = 5).
  B  eight passages (k = 8): the "how many chunks" question of R9, at answer level.
  C  k = 5 with the stored blind-agent rewrites appended to the question (R6.2). Development questions only
     (there are no rewrites for the test half), so this is an UPPER BOUND showing what the answer layer would
     score if rewriting worked as well as the best writer; it is not the system.
  N  no retrieval: the same model answers from memory with no passages (baseline of roadmap 4.4); there are no
     quotations to check, so only correctness can be scored.
Data: the 40 development questions (31 retrieve, 4 table, 5 refuse). The test half is read once, for the chosen
variant, when the layer is confirmed. The corpus does not fit in a prompt (reported below), so the "whole corpus
in the prompt" baseline is not run.

Measures:
- route outcome: table questions answered from the right row; refusals refused with the right reason;
  retrieve questions refused (false refusals) or answered from the table.
- on the retrieve questions: answered (not abstained) share; correctness by a model judge (yes 1, partly 0.5,
  no 0; a refusal or abstention scores 0) with a 95 % bootstrap interval; support (are the claims backed by the
  cited quotations; answered questions only); citation hit (a cited source satisfies a primary gold
  provision) and citation coverage (share of primary gold provisions covered by the cited sources);
  citation precision against the gold (cited sources that satisfy any gold provision / all cited: a strict
  lower bound, since the gold lists only the provisions its author thought of).
- cost: seconds per question end to end (mean, median, slowest), tokens per question.
- a sample of ten judge verdicts is read by a person (an AI assistant reading it, stated as such) and the
  agreement is reported.
Decision rule (one decision): B replaces A if the lower end of the paired 95 % interval of B's correctness
minus A's is above 0; otherwise k = 5 stays (fewer passages, lower cost). The baseline N is reported for
context; the system is judged to need retrieval if A's correctness beats N's with a lower paired bound above 0.
Stated expectation (can be wrong): correctness of A is near what retrieval allows (recall@5 is 0.53), about
0.45 to 0.60, with 20 to 30 percent abstentions; support is at least 0.9 because the quotations are checked;
refusals 5/5 and table 4/4; N scores below A on correctness; B is not detectably better than A; C is higher than
A (retrieval is the bottleneck).

Run: python experiments/p4_answers.py [--log]   (needs GEMINI_API_KEY in .env; about 350 model calls)
"""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import date
from statistics import mean, median

from law_assistant import settings
from law_assistant.answer.facts_lookup import LLMFactPicker
from law_assistant.answer.generate import LANGUAGE_NAMES, AnswerWriter
from law_assistant.answer.judge import Judge, score_of
from law_assistant.answer.pipeline import AnswerPipeline
from law_assistant.answer.router import LLMRouter
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.metrics import bootstrap_ci, paired_bootstrap
from law_assistant.evaluation.relevance import matches, targets_of
from law_assistant.facts.table import read_facts
from law_assistant.llm.gemini import CachedGenerator, GeminiGenerator
from law_assistant.retrieval.bge import BGEEmbedder, document_prompt, query_prompt
from law_assistant.retrieval.dense import DenseIndex
from law_assistant.retrieval.policies import CollapsedRetriever, before_amendment_text, current_text_only
from law_assistant.retrieval.rewrite import read_rewrites

LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"
CACHE_DIR = settings.PROJECT_ROOT / "data" / "llm_cache"
RUNS = settings.PROJECT_ROOT / "data" / "runs"
BGE_DIR = settings.PROJECT_ROOT / "data" / "models" / "bge-m3"
STORE = settings.PROJECT_ROOT / "data" / "indexes" / "bge-m3"
AGENT_REWRITES = settings.PROJECT_ROOT / "eval" / "rewrites" / "r6_dev.jsonl"

MEMORY_INSTRUCTIONS = (
    "You answer questions about EU, Spanish and UK data-protection and AI law for people who are not "
    "lawyers, from your own knowledge. Answer in the language you are told, in plain words, in at most "
    "150 words. This is an explanation of what the law says, not legal advice."
)


def collapsed(index, by_id):
    return CollapsedRetriever(index, by_id, by="copies", depth=50)


def build_pipeline(parts, k, rewriter=None, version_aware=False):
    return AnswerPipeline(
        router=parts["router"], picker=parts["picker"], current=parts["current"], full=parts["full"],
        original=parts["original"], writer=parts["writer"], chunks=parts["chunks"], k=k,
        rewriter=rewriter, version_aware=version_aware,
    )  # fmt: skip


def make_parts(chunks, by_id, embedder, generator, facts):
    """Everything the pipelines share: routers, search over the three text versions, writer. Answers are cached
    on disk by prompt, so a rerun with the same inputs makes no model calls."""

    def index(cs, name):
        return DenseIndex(
            cs, embedder, STORE, name=name, document_prompt_fn=document_prompt, query_prompt_fn=query_prompt
        )

    def cached(name):
        return CachedGenerator(generator, CACHE_DIR / f"{name}.jsonl")

    return {
        "router": LLMRouter(cached("router")),
        "picker": LLMFactPicker(facts, cached("fact_picker")),
        "current": collapsed(index(current_text_only(chunks), "bge-m3-current"), by_id),
        "full": collapsed(index(chunks, "bge-m3"), by_id),
        "original": collapsed(index(before_amendment_text(chunks), "bge-m3-original"), by_id),
        "writer": AnswerWriter(cached("answers")),
        "chunks": chunks,
        "judge": Judge(cached("judge")),
        "memory": cached("memory"),
    }


def cited_stats(question, result, by_id):
    """Citation hit, coverage and precision of an answer's sources against the gold."""
    cited = [by_id[s.chunk_id] for s in result.sources if s.chunk_id]
    primary = [t for t in targets_of(question) if t.grade == 2]
    covered = [t for t in primary if any(matches(c, t.gold) for c in cited)]
    relevant = [c for c in cited if any(matches(c, t.gold) for t in targets_of(question))]
    return {
        "hit": bool(covered),
        "coverage": len(covered) / len(primary) if primary else None,
        "precision": len(relevant) / len(cited) if cited else None,
    }


def main() -> int:
    import torch

    settings.load_env_file()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    by_id = {c.id: c for c in chunks}
    questions = [q for q in read_gold(settings.GOLD_DIR / "questions.jsonl") if q.split == "dev"]
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")
    facts = read_facts(settings.FACTS_DIR / "legal_facts.jsonl")

    embedder = BGEEmbedder.load(BGE_DIR, device=device, max_length=1024)

    generator = GeminiGenerator.from_env()
    parts = make_parts(chunks, by_id, embedder, generator, facts)
    judge = parts["judge"]
    agent_rewrites = read_rewrites(AGENT_REWRITES, [q for q in questions if q.route == "retrieve"])
    variants = {
        "A": build_pipeline(parts, 5),
        "B": build_pipeline(parts, 8),
        "C": build_pipeline(parts, 5, rewriter=lambda q: agent_rewrites[q]),
    }

    outcomes: dict[str, dict] = {}
    for name, pipe in variants.items():
        rows = {}
        for q in questions:
            if name == "C" and q.route != "retrieve":
                continue  # the rewrites exist only for the retrieve questions
            before = len(generator.calls)
            result = pipe.ask(q.text)
            row = {"result": result, "calls": generator.calls[before:]}
            if result.kind in ("answer", "table"):
                row["correct"] = judge.correctness(q.text, q.expected_answer, result.text)
            else:
                row["correct"] = ("no", "no answer given")
            if result.kind == "answer":
                row["support"] = judge.support(
                    result.text.split("\n\n")[0], [s.quote for s in result.sources if s.quote]
                )
                row.update(cited_stats(q, result, by_id))
            rows[q.id] = row
        outcomes[name] = rows
        out_path = RUNS / f"p4_answers_{name}.jsonl"
        with out_path.open("w", encoding="utf-8", newline="\n") as f:
            for q in questions:
                if q.id not in rows:
                    continue
                r = rows[q.id]["result"]
                f.write(
                    json.dumps(
                        {
                            "id": q.id,
                            "gold_route": q.route,
                            "kind": r.kind,
                            "text": r.text,
                            "trace": {k: v for k, v in r.trace.items() if k != "invalid_citations"},
                            "invalid": [(c.quote, why) for c, why in r.trace["invalid_citations"]],
                            "correct": rows[q.id]["correct"],
                            "support": rows[q.id].get("support"),
                        },
                        ensure_ascii=False,
                        default=str,
                    )  # fmt: skip
                    + "\n"
                )

    # Baseline N: the same model, no passages.
    memory = parts["memory"]
    baseline = {}
    for q in (q for q in questions if q.route == "retrieve"):
        prompt = f"Answer in: {LANGUAGE_NAMES[q.language]}\nQuestion: {q.text}"
        answer = memory.generate(prompt, system=MEMORY_INSTRUCTIONS, temperature=0.0, max_output_tokens=600)
        baseline[q.id] = (answer, judge.correctness(q.text, q.expected_answer, answer))

    retrieve = [q for q in questions if q.route == "retrieve"]

    def scores(name):
        return [score_of(outcomes[name][q.id]["correct"][0]) for q in retrieve]

    out = [f"### P4.4 the answer layer on the development questions ({len(questions)} questions)", ""]
    for name in ("A", "B", "C"):
        rows = outcomes[name]
        kinds = [rows[q.id]["result"].kind for q in retrieve]
        answered = [q for q in retrieve if rows[q.id]["result"].kind == "answer"]
        corr, lo, hi = bootstrap_ci(scores(name))
        label = {"A": "k = 5", "B": "k = 8", "C": "k = 5 with the blind agent's rewrites (upper bound)"}[name]
        out.append(f"**Variant {name} ({label}).**")
        out.append(
            f"- retrieve questions ({len(retrieve)}): answered {kinds.count('answer')}, abstained "
            f"{kinds.count('abstained')}, refused {kinds.count('refused')}, from the table {kinds.count('table')}; "
            f"correctness {corr:.2f} ({lo:.2f} to {hi:.2f})"
        )
        if answered:
            sup = mean(score_of(rows[q.id]["support"][0]) for q in answered)
            hit = mean(rows[q.id]["hit"] for q in answered)
            cov = mean(rows[q.id]["coverage"] for q in answered if rows[q.id]["coverage"] is not None)
            prec = mean(rows[q.id]["precision"] for q in answered if rows[q.id]["precision"] is not None)
            out.append(
                f"- among the {len(answered)} answered: support {sup:.2f}; a cited source satisfies a primary "
                f"gold provision {hit:.2f}; coverage of the primary provisions {cov:.2f}; strict precision {prec:.2f}"
            )
        if name != "C":
            table = [q for q in questions if q.route == "table"]
            refuse = [q for q in questions if q.route == "refuse"]
            out.append(
                "- table questions answered from the right row: "
                f"{sum(rows[q.id]['result'].kind == 'table' and rows[q.id]['result'].trace['fact_key'] == q.table_key for q in table)}"
                f"/{len(table)}; refusals refused with the right reason: "
                f"{sum(rows[q.id]['result'].kind == 'refused' and rows[q.id]['result'].reason == q.refusal_reason for q in refuse)}"
                f"/{len(refuse)}; retrieve questions refused {kinds.count('refused')}"
            )
        times = sorted(sum(c.seconds for c in rows[q.id]["calls"]) for q in questions if q.id in rows)
        toks_in = mean(sum(c.prompt_tokens for c in rows[q.id]["calls"]) for q in questions if q.id in rows)
        toks_out = mean(sum(c.output_tokens for c in rows[q.id]["calls"]) for q in questions if q.id in rows)
        out.append(
            f"- model time per question (excluding search and judging calls made outside the pipeline is not "
            f"separable here): mean {mean(times):.2f} s, median {median(times):.2f} s, slowest {times[-1]:.2f} s; "
            f"tokens per question {toks_in:.0f} in, {toks_out:.0f} out (includes the judge calls for this question)"
        )
        out.append("")
    n_scores = [score_of(baseline[q.id][1][0]) for q in retrieve]
    nc, nlo, nhi = bootstrap_ci(n_scores)
    out.append(
        f"**Baseline N (no retrieval).** correctness {nc:.2f} ({nlo:.2f} to {nhi:.2f}); no quotations to check."
    )
    out.append("")
    for first, second in (("A", "B"), ("N", "A"), ("A", "C")):
        a = n_scores if first == "N" else scores(first)
        b = scores(second)
        p = paired_bootstrap(a, b)
        out.append(
            f"{second} against {first}, correctness: difference {p.difference:+.3f}, "
            f"95 % interval {p.low:+.3f} to {p.high:+.3f}"
        )
    by_type: dict[str, list[tuple[float, float, float]]] = {}
    for i, q in enumerate(retrieve):
        by_type.setdefault(q.type, []).append((scores("A")[i], scores("C")[i], n_scores[i]))
    out += ["", "Correctness by question type (A, C upper bound, N no retrieval; number of questions):", ""]
    for kind, rows3 in sorted(by_type.items()):
        a_m, c_m, n_m = (mean(r[j] for r in rows3) for j in range(3))
        out.append(f"- {kind}: {a_m:.2f}, {c_m:.2f}, {n_m:.2f} (n = {len(rows3)})")
    by_language: dict[str, list[tuple[float, float]]] = {}
    for i, q in enumerate(retrieve):
        by_language.setdefault(q.language, []).append((scores("A")[i], n_scores[i]))
    out += ["", "Correctness by question language (A, N; number of questions):", ""]
    for lang, rows2 in sorted(by_language.items()):
        out.append(
            f"- {lang}: {mean(r[0] for r in rows2):.2f}, {mean(r[1] for r in rows2):.2f} (n = {len(rows2)})"
        )
    words = sum(c.words for c in chunks)
    out += [
        "",
        f"The corpus is {len(chunks):,} chunks and about {words:,} words (roughly {int(words * 1.5):,} tokens), "
        "so it does not fit in a prompt of one million tokens once Spanish, the original texts and the markup "
        "are counted; that baseline is not run.",
        "",
        "Retrieve questions not judged correct in variant A, and any table or refuse question that went the wrong way:",
        "",
    ]
    for q in questions:
        r = outcomes["A"][q.id]
        expected_kind = {"retrieve": "answer", "table": "table", "refuse": "refused"}[q.route]
        if q.route == "retrieve" and r["correct"][0] != "yes":
            out.append(f"- {q.id} ({q.route}): {r['result'].kind}, {r['correct'][0]}: {r['correct'][1]}")
        elif q.route != "retrieve" and r["result"].kind != expected_kind:
            out.append(f"- {q.id} ({q.route}): went to {r['result'].kind}")
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## P4.4 answer layer, dev half, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
