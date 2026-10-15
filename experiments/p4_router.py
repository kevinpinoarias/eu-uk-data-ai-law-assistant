"""
P4.2: which route does a question take (retrieve, table or refuse), and can the table lookup find the right
row? The rule router (readable patterns) against the model router (gemini-3.1-flash-lite applying the same
definitions), measured against the gold route.

PRE-REGISTRATION (written 15 October 2026 before either router has been scored on any gold question; the
rules and the model instructions were written from the definitions and from invented examples, but I had
read the development questions' labels while planning, so the development half is not blind)

Data: the 40 development questions (31 retrieve, 4 table, 5 refuse). The 40 test questions are read once,
when the whole answer layer is confirmed.
Measures, for each router: routing accuracy (all questions); refusal recall (refusals sent to refuse, and
with the right reason); false refusals (retrieve or table questions sent to refuse: the costly error, since
the user gets no answer); table recall (table questions sent to table) and table false alarms (other
questions sent to table).
Table lookup (BGE-M3 embeddings of each fact's subject and summary in the question's language, limited to
the jurisdictions the question names): for the table questions, is the top-ranked fact the gold table_key;
and the top score for every question, to choose the threshold below which no fact is returned.
Threshold rule: the lowest top score among the correctly matched table questions, rounded down to 0.05
(this is tuned on four questions and is only a safety net: a wrongly routed question that matches no fact
falls back to retrieval).

Decision rule: the router used by the pipeline is the one with the higher routing accuracy; on a tie, the
one with fewer false refusals; on a further tie the rules (free and explainable). A router with any false
refusal on the development half must be explained question by question before it is used.
Stated expectation (can be wrong): the model router reaches at least 0.95 accuracy; the rules reach about
0.85 and miss the refusals that need reading the situation (a breach that happened yesterday); the table
lookup finds the gold row for all four development table questions.

Run: python experiments/p4_router.py [--log]   (needs GEMINI_API_KEY in .env)
"""

from __future__ import annotations

import subprocess
import sys
from collections import Counter
from datetime import date

from law_assistant import settings
from law_assistant.answer.facts_lookup import FactMatcher
from law_assistant.answer.router import LLMRouter, RuleRouter
from law_assistant.answer.understand import understand
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.facts.table import read_facts
from law_assistant.llm.gemini import CachedGenerator, GeminiGenerator
from law_assistant.retrieval.bge import BGEEmbedder

LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"
CACHE = settings.PROJECT_ROOT / "data" / "llm_cache" / "router.jsonl"
BGE_DIR = settings.PROJECT_ROOT / "data" / "models" / "bge-m3"


def score_router(router, questions) -> tuple[list[str], dict]:
    predictions = [router.route(q.text) for q in questions]
    ok = [p.route == q.route for p, q in zip(predictions, questions, strict=True)]
    refusals = [(p, q) for p, q in zip(predictions, questions, strict=True) if q.route == "refuse"]
    tables = [(p, q) for p, q in zip(predictions, questions, strict=True) if q.route == "table"]
    stats = {
        "accuracy": sum(ok) / len(ok),
        "refusals sent to refuse": sum(p.route == "refuse" for p, _ in refusals),
        "refusals with the right reason": sum(
            p.route == "refuse" and p.reason == q.refusal_reason for p, q in refusals
        ),
        "false refusals": sum(
            p.route == "refuse" and q.route != "refuse" for p, q in zip(predictions, questions, strict=True)
        ),
        "table questions sent to table": sum(p.route == "table" for p, _ in tables),
        "table false alarms": sum(
            p.route == "table" and q.route != "table" for p, q in zip(predictions, questions, strict=True)
        ),
    }
    return [p.route for p in predictions], stats


def main() -> int:
    import torch

    settings.load_env_file()
    questions = [q for q in read_gold(settings.GOLD_DIR / "questions.jsonl") if q.split == "dev"]
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")
    n = len(questions)
    gold = Counter(q.route for q in questions)
    generator = GeminiGenerator.from_env()
    routers = (RuleRouter(), LLMRouter(CachedGenerator(generator, CACHE)))
    results = {r.name: score_router(r, questions) for r in routers}

    out = [
        f"### P4.2 routing on the development questions ({n}: "
        + ", ".join(f"{gold[r]} {r}" for r in ("retrieve", "table", "refuse"))
        + ")",
        "",
    ]
    for name, (_, stats) in results.items():
        out.append(
            f"**{name} router.** Accuracy {stats['accuracy']:.3f} ({round(stats['accuracy'] * n)}/{n})."
        )
        out.append(
            f"Refusals sent to refuse {stats['refusals sent to refuse']}/{gold['refuse']} "
            f"(right reason {stats['refusals with the right reason']}/{gold['refuse']}); "
            f"false refusals {stats['false refusals']}; table questions sent to table "
            f"{stats['table questions sent to table']}/{gold['table']}; "
            f"table false alarms {stats['table false alarms']}."
        )
        out.append("")
    out.append("Disagreements with the gold route (id, gold, rules, model, text):")
    out.append("")
    rule_routes, model_routes = results["rules"][0], results["llm"][0]
    for q, r, m in zip(questions, rule_routes, model_routes, strict=True):
        if r != q.route or m != q.route:
            out.append(f"- {q.id}: gold {q.route}, rules {r}, model {m}: {q.text}")

    device = "cuda" if torch.cuda.is_available() else "cpu"
    embedder = BGEEmbedder.load(BGE_DIR, device=device, max_length=512)
    facts = read_facts(settings.FACTS_DIR / "legal_facts.jsonl")
    matcher = FactMatcher(facts, embedder.embed_texts, threshold=0.0)
    out += ["", "Table lookup (top fact, its score, whether it is the gold row):", ""]
    right_scores, other_scores = [], []
    for q in questions:
        u = understand(q.text)
        match = matcher.match(q.text, u.language, u.jurisdictions)
        key = match.fact.key if match.fact else None
        if q.route == "table":
            right = key == q.table_key
            (right_scores if right else other_scores).append(match.score)
            out.append(
                f"- {q.id}: {key} ({match.score:.2f}), gold {q.table_key}: {'right' if right else 'WRONG'}"
            )
        else:
            other_scores.append(match.score)
    if right_scores:
        threshold = int(min(right_scores) * 20) / 20
        above = sum(s >= threshold for s in other_scores)
        out += [
            "",
            f"Lowest score of a correct match {min(right_scores):.2f}, so the threshold is {threshold:.2f}. "
            f"Of the {len(other_scores)} other development questions, {above} would still get a fact at "
            f"that threshold (highest {max(other_scores):.2f}); the router sends only figure questions here, "
            "so this is the share that would be wrongly answered if routed to the table.",
        ]
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## P4.2 routing and table lookup, dev half, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
