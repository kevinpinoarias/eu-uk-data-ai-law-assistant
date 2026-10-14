# The gold question set (Phase 2)

The scoreboard that every later experiment is measured against. It is written, reviewed and frozen before any retrieval experiment. Code: `src/law_assistant/evaluation/` (`gold.py` the record, `checks.py` the checks). The set itself will live in `eval/gold/` once drafted.

## What a gold set is (the generic idea)

In any machine-learning project a gold set is a collection of examples where a person has written down the correct answer, so a system's output can be compared with something trusted. It is built before the experiments for the same reason a test is written before the code: otherwise the questions drift towards what the system already handles. The usual recipe is: define what correct means, cover the realistic cases, label, split into development and test, freeze, measure with uncertainty, and guard against leakage (the answer's wording hiding in the question).

## The plan for this project

80 questions, 40 English and 40 Spanish, mostly in lay wording with no article numbers.

| Type | Count | What it tests |
|---|---|---|
| lookup | 16 | which provision says X |
| definition | 8 | what a defined term means |
| cross_reference | 10 | the answer needs two or more provisions |
| comparison | 10 | EU against UK |
| spanish_law | 8 | the LOPDGDD |
| as_of | 10 | the answer depends on the date |
| numeric | 8 | an exact figure or date: must go to the structured table, not retrieval |
| refuse | 10 | 6 out of the corpus, 4 requests for legal advice |

Kevin writes about 15 of them himself, as the realistic user; Claude drafts the rest from a topic map shown first so nothing is duplicated. Split: 40 development, 40 test, stratified by type and language with a recorded seed. The test set is used once per decision. It is committed with a dated hash; the discipline is procedural and logged.

## The record

- **Labels are by instrument and unit** (`eu-gdpr`, article 17), with optional pinpoint provision ids and quotes, never by chunk, so the same gold works whatever chunking is tested (experiment R3).
- A gold provision has a role: `primary` (must be found) or `acceptable` (also relevant), and optional `version` and `language` filters (the AI Act's original and consolidated wording differ).
- A question records language, type, route (`retrieve`, `table`, `refuse`), phrasing (`lay`, `lawyer`), jurisdictions, `as_of` (the corpus snapshot date, 2026-10-14, if empty), the short expected answer, `table_key` for numeric questions, `refusal_reason`, author, split, review date and notes.
- The gold is tied to the corpus snapshot. Any change after freezing is a new version with a new hash; results from different versions are not comparable.

## The checks

1. **Well-formed:** id form, route follows from type, a retrieval question has a primary gold provision and jurisdictions, a refusal has no gold and a reason, a numeric question has a table key, an `as_of` question has a valid date, no blank text, no duplicate id or text.
2. **Mix against the plan** by type, language and refusal reason.
3. **Against the parsed corpus:** the unit exists, every pinpoint id exists, every quote is in the text (whitespace ignored), narrowed by version and language when given. No fact enters the gold that the corpus does not contain.
4. **Overlap warning (leakage):** the share of the question's longer words found in its gold text, weighted by how rare each word is across the corpus. Advisory, threshold 60%. Weighting was added after the first real run: the example question in the plan, "¿A qué edad puede un menor dar su consentimiento en España?", scored 60% because it uses the same distinctive words as Article 7. That question is easy for a keyword search, so the check was right and the example was not lay enough.

No qualified lawyer has reviewed the set. Interpretation questions are limited to "what does this text say"; the write-up will say so.

## Status

Step 2.0 (schema and checks) done, test first, 304 tests passing. Next: 2.1 drafting in batches, 2.2 Kevin's questions, 2.3 the structured table, 2.4 the metrics module (hit@k, recall@k, MRR, nDCG, paired bootstrap), 2.5 split and freeze.
