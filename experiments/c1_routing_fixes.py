"""
C1: do the candidate fixes to the router and the fact picker (decision 116) work on questions nobody tuned on?

The sealed test half showed three refusals sent to search (q060 a court case, q061 the largest fine, q079 an
adequacy list), an application-date question that never reached the table (q056) and the upper fine tier given
for a breach-notification question (q078). Decision 115 says a fix is a candidate, to be pre-registered and
measured on a new batch of unseen questions; the test half is not read again. Batch C (eval/batch_c/, 37
questions, frozen by fingerprint before this script was run) is that batch.

PRE-REGISTRATION (written 16 October 2026 before either candidate was run on any batch C question)

Variants (2, counted in the experiment tally):
  A  the shipped router instructions and picker instructions, facts table as shipped.
  B  the candidate router instructions (ROUTE_INSTRUCTIONS_V2), the candidate picker instructions
     (PICK_INSTRUCTIONS_V2) and the table with the two GDPR fine-tier subjects widened by
     experiments/data/c1_fact_scope.json (apply_scope). Model: the same as the shipped system.
Both candidates were written knowing the five test-half failures, so B is a TUNED variant. The wording of
no test-half or batch C question is in the prompts (a test checks this).
Data: the 37 questions of batch C (16 refusals, 10 figures, 11 questions about the law that must be neither
refused nor answered from the table). As a regression check only, B is also run on the 40 development
questions and compared with A's cached answers; no adoption depends on a gain there. The test half is NOT used.
Decision of one question (what the pipeline would do): the router picks a route; if it picks the table, the
picker picks a row (or none, and the pipeline then searches the text).
  correct: a refusal refused with the right reason; a figure question routed to the table with the gold row;
  a law question routed to retrieve.
  errors, in order of cost: wrong figure (a row stated that is not the gold row, or for a non-figure
  question), false refusal, missed refusal (answered or searched instead of refused), figure not reached
  (sent to retrieve), refusal with the wrong reason, table with no row (falls back to search, harmless).
Measures per variant: correct decisions of 37; refusals correctly refused of 16 (and of the 8 whose type
the test half missed: case law, enforcement decisions, adequacy status); figure questions with the gold row
of 10 (and of the 4 whose tier depends on the breach, and the 2 application dates); false refusals and wrong
figures among all 37. Paired: questions only A gets right, only B gets right.
Decision rule (small counts, so a screening rule and not a significance test):
  Router V2 is adopted if on batch C it correctly refuses more refusals than A, introduces no false refusal
  and no wrong figure that A did not already have (on batch C or on the development questions), and sends at
  least as many figure questions to the table as A.
  Picker V2 and the widened subjects are adopted if, on the 10 figure questions given to the picker directly,
  they find more gold rows than A and lose none that A found, and give no wrong figure on the development
  questions that A did not give.
  A candidate that does not meet its rule is not adopted and is recorded as a repair that did not work.
Stated expectation (can be wrong): A misses at least 4 of the 8 test-half failure types; B catches at least
7 of the 8; B refuses at most 1 of the 11 law questions wrongly (q129 and q130 mention adequacy, q128 courts,
q132 the regulator, q127 fines: the guard in B may not be enough); A gets at most 2 of the 4 tier-by-breach
rows right and B all 4; A sends at least 1 of the 2 application dates to retrieve and B sends both to the table.
Limits stated in advance: batch C was written by the same assistant that wrote the fixes, from the categories
of the failures, so a good result shows the fix works on new instances of those categories, not that routing
is good in general; 37 questions cannot show small differences; after this run batch C is spent, so an adopted
candidate stays unconfirmed on fresh questions.

Amendment (16 October 2026, before any result was seen): the first run stopped on a reply from variant A that was
not a valid route (the model answered with a reason in the route field). A reply that is not a valid route now
falls back to the rule router, as the pipeline does in degraded mode, and the number of such falls is reported
per variant. A quota or transport failure still stops the run.

Run: python experiments/c1_routing_fixes.py [--log]   (needs GEMINI_API_KEY in .env; model calls are cached, so
an interrupted run resumes without repeating calls)
"""

from __future__ import annotations

import json
import subprocess
import sys
from collections import Counter
from datetime import date

from law_assistant import settings
from law_assistant.answer.facts_lookup import (
    PICK_INSTRUCTIONS,
    PICK_INSTRUCTIONS_V2,
    LLMFactPicker,
    apply_scope,
)
from law_assistant.answer.router import ROUTE_INSTRUCTIONS, ROUTE_INSTRUCTIONS_V2, LLMRouter, RuleRouter
from law_assistant.answer.understand import understand
from law_assistant.evaluation.gold import freeze_hash, read_gold
from law_assistant.facts.table import read_facts
from law_assistant.llm.gemini import CachedGenerator, GeminiGenerator, LLMError

LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"
BATCH = settings.PROJECT_ROOT / "eval" / "batch_c"
OVERLAY = settings.PROJECT_ROOT / "experiments" / "data" / "c1_fact_scope.json"
ROUTER_CACHE = settings.PROJECT_ROOT / "data" / "llm_cache" / "router.jsonl"
PICKER_CACHE = settings.PROJECT_ROOT / "data" / "llm_cache" / "fact_picker.jsonl"

FAILURE_TYPES = {
    "q101",
    "q102",
    "q103",
    "q110",
    "q104",
    "q105",
    "q106",
    "q107",
}  # case law, enforcement, adequacy
TIER_BY_BREACH = {"q117", "q118", "q119", "q120"}
APPLICATION_DATES = {"q123", "q124"}


def decide(router, picker, q) -> tuple[str, str | None, str | None, bool]:
    fell_back = False
    try:
        r = router.route(q.text)
    except LLMError as error:
        if str(error).startswith("HTTP"):
            raise  # a quota or transport failure: stop, the run resumes from the cache
        # AMENDED 16 Oct after the first run stopped on a malformed reply from variant A (no result had been
        # seen): as in the pipeline (degraded mode), a reply that is not a valid route falls back to the rules.
        r, fell_back = RuleRouter().route(q.text), True
    key = None
    if r.route == "table":
        fact = picker.pick(q.text, understand(q.text).jurisdictions)
        key = fact.key if fact else None
    return r.route, r.reason, key, fell_back


def verdict(q, route: str, reason: str | None, key: str | None) -> str:
    if q.route == "refuse":
        if route == "refuse":
            return "correct" if reason == q.refusal_reason else "refusal, wrong reason"
        return "missed refusal"
    if route == "refuse":
        return "false refusal"
    if q.route == "table":
        if route != "table":
            return "figure not reached"
        if key == q.table_key:
            return "correct"
        return "wrong figure" if key else "table, no row (falls back to search)"
    if route == "retrieve":
        return "correct"
    return "wrong figure" if key else "table, no row (falls back to search)"


def run_variant(name, router, picker, questions) -> dict[str, tuple[str, str | None, str | None, str, bool]]:
    out = {}
    for q in questions:
        route, reason, key, fell_back = decide(router, picker, q)
        out[q.id] = (route, reason, key, verdict(q, route, reason, key), fell_back)
    return out


def summarise(name, results, questions) -> list[str]:
    by = {q.id: q for q in questions}
    ok = {i for i, r in results.items() if r[3] == "correct"}
    errors = Counter(r[3] for r in results.values() if r[3] != "correct")
    refusals = [i for i in results if by[i].route == "refuse"]
    tables = [i for i in results if by[i].route == "table"]
    lines = [
        f"**{name}.** Correct decisions {len(ok)}/{len(results)}. "
        f"Refusals refused with the right reason {sum(i in ok for i in refusals)}/{len(refusals)} "
        f"(the 8 failure types: {sum(i in ok for i in FAILURE_TYPES & set(results))}/{len(FAILURE_TYPES & set(results))}). "
        f"Figure questions with the gold row {sum(i in ok for i in tables)}/{len(tables)} "
        f"(tier by breach: {sum(i in ok for i in TIER_BY_BREACH & set(results))}/{len(TIER_BY_BREACH & set(results))}; "
        f"application dates: {sum(i in ok for i in APPLICATION_DATES & set(results))}/{len(APPLICATION_DATES & set(results))}).",
        "Errors: " + (", ".join(f"{n} {k}" for k, n in sorted(errors.items())) or "none") + ". "
        f"Malformed router replies that fell back to the rules: {sum(r[4] for r in results.values())}.",
    ]
    return lines


def main() -> int:
    settings.load_env_file()
    batch = read_gold(BATCH / "questions.jsonl")
    manifest = json.loads((BATCH / "MANIFEST.json").read_text(encoding="utf-8"))
    if freeze_hash(batch) != manifest["sha256"]:
        raise SystemExit(
            "batch C has changed since it was frozen; this experiment must not run on an edited batch"
        )
    dev = [q for q in read_gold(settings.GOLD_DIR / "questions.jsonl") if q.split == "dev"]
    facts = read_facts(settings.FACTS_DIR / "legal_facts.jsonl")
    scoped = apply_scope(facts, json.loads(OVERLAY.read_text(encoding="utf-8")))
    generator = GeminiGenerator.from_env()
    routers = CachedGenerator(generator, ROUTER_CACHE)
    pickers = CachedGenerator(generator, PICKER_CACHE)
    variants = {
        "A (shipped)": (
            LLMRouter(routers, ROUTE_INSTRUCTIONS),
            LLMFactPicker(facts, pickers, PICK_INSTRUCTIONS),
        ),
        "B (candidate)": (
            LLMRouter(routers, ROUTE_INSTRUCTIONS_V2),
            LLMFactPicker(scoped, pickers, PICK_INSTRUCTIONS_V2),
        ),
    }
    on_batch = {n: run_variant(n, r, p, batch) for n, (r, p) in variants.items()}
    a, b = on_batch["A (shipped)"], on_batch["B (candidate)"]

    out = [
        f"### C1 routing fixes on batch C ({len(batch)} questions, batch fingerprint {manifest['sha256'][:8]})",
        "",
    ]
    for name, results in on_batch.items():
        out += summarise(name, results, batch) + [""]
    only_a = [i for i in a if a[i][3] == "correct" and b[i][3] != "correct"]
    only_b = [i for i in b if b[i][3] == "correct" and a[i][3] != "correct"]
    out.append(
        f"Paired: only A correct on {len(only_a)} questions {only_a}; only B correct on {len(only_b)} {only_b}."
    )
    out += ["", "Every question where A and B differ, or either is wrong (id, gold, A, B, text):", ""]
    by = {q.id: q for q in batch}
    for i in sorted(a):
        if a[i][3] != "correct" or b[i][3] != "correct":
            q = by[i]
            gold = q.table_key if q.route == "table" else (q.refusal_reason or "retrieve")
            out.append(f"- {i} ({q.route}, gold {gold}): A {a[i][3]} [{a[i][0]}/{a[i][2] or a[i][1] or '-'}]; B {b[i][3]} [{b[i][0]}/{b[i][2] or b[i][1] or '-'}]: {q.text}")  # fmt: skip

    # the picker on its own: the 10 figure questions, whichever way each variant's router sent them
    out += ["", "Picker alone on the figure questions (gold row, A's pick, B's pick):", ""]
    right = Counter()
    for q in (q for q in batch if q.route == "table"):
        jur = understand(q.text).jurisdictions
        pa = variants["A (shipped)"][1].pick(q.text, jur)
        pb = variants["B (candidate)"][1].pick(q.text, jur)
        ka, kb = (pa.key if pa else None), (pb.key if pb else None)
        right["A"] += ka == q.table_key
        right["B"] += kb == q.table_key
        right["lost"] += ka == q.table_key and kb != q.table_key
        out.append(f"- {q.id}: gold {q.table_key}; A {ka}; B {kb}")
    out.append(
        f"Gold row found: A {right['A']}/10, B {right['B']}/10; rows A found and B lost: {right['lost']}."
    )

    # regression check on the development questions (A's answers are already in the cache)
    ra = run_variant("A", *variants["A (shipped)"], dev)
    rb = run_variant("B", *variants["B (candidate)"], dev)
    out += [
        "",
        f"Regression check on the {len(dev)} development questions (not part of the adoption rule except for new errors):",
        "",
    ]
    out += summarise("A (shipped)", ra, dev) + summarise("B (candidate)", rb, dev)
    changed = [i for i in ra if ra[i][3] != rb[i][3]]
    dev_by = {q.id: q for q in dev}
    out += ["", "Development questions whose verdict differs (id, A, B, text):", ""]
    out += [f"- {i}: A {ra[i][3]}; B {rb[i][3]}: {dev_by[i].text}" for i in changed] or ["- none"]

    report = "\n".join(out)
    print(report)
    print(f"\nmodel calls made this run: {len(generator.calls)}")
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## C1 routing and figure-picker fixes, batch C, run {date.today().isoformat()} "
            f"(commit {commit}; batch C fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
