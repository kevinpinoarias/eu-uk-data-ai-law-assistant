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

## The lawyer's review of the first 65 questions (15 October 2026)

Claude drafted 65 of the 80 questions (`eval/gold/questions.jsonl`; Kevin's 15 will be q066 to q080) and then re-read every expected answer against the whole provision and its neighbours, as a lawyer would. Each question's `notes` field records its ambiguities. What the review changed:

- **Wrong or incomplete answers corrected:** the data protection officer rule is not "only three cases" (Article 37(4) lets Member State law require more; Spain's LOPDGDD Article 34 does); the high-risk AI duties (Articles 14 and 26) do not yet apply, because the Omnibus moved the dates to 2 December 2027 (Annex III) and 2 August 2028 (Annex I); the AI literacy duty in Article 4 was softened by the Omnibus; limits, exceptions and companion paragraphs were added to the answers on erasure, portability, breach notification, compensation, processor contracts and records.
- **Jurisdiction cues added** to questions about law that exists in parallel in the EU and the UK, so that a correct UK or national chunk is not scored as a miss.
- **Versions pinned** where the original and the consolidated wording differ (AI Act Articles 4, 5, 6, 113, new 4a and 75a to 75d; GDPR Article 37(1)(c)), and a before-and-after pair of questions added for three of them (original and current wording).
- **q017 rewritten** as "does any piece of software count as AI, or only some?", with recital 12 as gold alongside Article 3(1), and the interpretive limit (the Commission's guidelines are not in the corpus) written into the notes.
- **Not asserted:** where the text read does not state a fact (the date Article 4a starts to apply, the reason for a corrigendum), the answer says nothing about it.
- **Data problems found by the review:** omitted UK provisions kept as lines of dots (finding 27 in `PARSING.md`, decision 47), and the paragraph-level meaning of BOE dates (decision 52).

## Rules for the metrics (step 2.4)

- A retrieved chunk is a hit if it contains one of the gold provision's pinpoint ids; if no pinpoints are given, any chunk of the unit counts (decision 51).
- A gold provision pinned to a version counts only for chunks of that version (decision 50). A question without a version accepts the same unit in any version of that instrument.
- Questions in one language may have their gold text in another (a Spanish question on a UK Act, an English question on the LOPDGDD): those are the cross-language cases for experiment R4.

## Status

Step 2.0 (schema and checks) done. Step 2.1: 65 of 80 questions drafted and checked (13 lookups, 6 definitions, 8 cross-references, 9 comparisons, 7 Spanish-law, 8 as-of, 6 numeric, 8 refusals; 32 Spanish, 33 English; 5 out-of-corpus and 3 legal-advice refusals), pending Kevin's review. Still to write by Kevin (step 2.2): 15 questions as the realistic user: 3 lookups, 2 definitions, 2 cross-references, 1 EU-UK, 1 Spanish-law, 2 as-of, 2 numeric and 2 refusals (1 out-of-corpus, 1 advice), of which 8 in Spanish and 7 in English to reach 40 and 40. Next: 2.3 the structured table (keys already named in the numeric questions), 2.4 the metrics module, 2.5 split and freeze.
