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

## The last 15 questions: gaps in the first 65 (15 October 2026)

Kevin asked Claude to draft the last 15 and to look for ways of asking that the first 65 did not cover. The gaps found, and the question that fills each (q066 to q080):

- scope ("does the GDPR apply to a US company?", q066, with the Europe-versus-Union trap);
- marketing and the right to object, the commonest real complaint (q067);
- a false premise, to be corrected ("does the AI Act ban all facial recognition?", q068);
- roles: controller versus processor (q069);
- a keyword-style query whose answer is partly in a recital (q070, the first `terse` question);
- two laws at once (automated rejection of job applicants: GDPR Article 22 and the AI Act, q071);
- "who enforces it?" (q072);
- the UK Acts beyond the UK GDPR: complaints to the controller under section 164A of the 2018 Act (q073);
- Spain's advertising-exclusion systems (q074);
- application dates for marking AI-generated content and for general-purpose AI models (q075, q076);
- a keyword-style question with no jurisdiction, where the right answer gives both the EU and the UK figure (q077);
- a two-step numeric answer (breach notification is in Articles 25 to 39, hence the lower fine tier, q078);
- a fact outside the corpus inside a topic the corpus covers (India's adequacy status, q079);
- applying the rule to the user's own facts, where the assistant explains but does not decide (q080).

All 80 now pass the checks and match the plan exactly (16 lookups, 8 definitions, 10 cross-references, 10 comparisons, 8 Spanish-law, 10 as-of, 8 numeric, 10 refusals; 40 Spanish and 40 English; 71 lay, 7 lawyer and 2 terse). Two leakage warnings are expected and annotated (q051 and q068, whose key terms are also the legal terms).

**What this changes about the plan.** One reason for Kevin to write 15 questions was to reduce the risk that the author of the system also shapes the test. That is no longer fully met: Claude wrote all 80. The mitigation is Kevin's review of all 80, and he may rewrite or replace any question; any he writes himself will carry `author: kevin`.

## Independent review and the freeze (15 October 2026)

**The review.** Five separate AI reviewer passes, each given 16 questions, saw only the question, the expected answer and the text of the cited provisions (not the drafting notes), were told to be skeptical and to mark any concern that rested on outside knowledge, and could edit nothing. On the first draft they found 15 questions fine, 53 with minor findings and 12 with major findings. Every finding was checked against the corpus before it was adopted; none was adopted on trust.

**What the reviewers caught that the scripts could not:**

- the as-of question on the original bias-detection rule (original Article 10(5)) was built on a false premise: that Article was not yet applicable on its date, and the Omnibus replaced it before it ever applied, so the question is now about the wording as published;
- the UK "malicious person" in Article 17(1)(g) is a narrowly defined term (convicted of listed harassment or stalking offences, or subject to a stalking protection order), not any spiteful accuser;
- work email and digital devices are covered by LOPDGDD Article 87, not Article 89 (video surveillance), which the refusal answer had cited;
- the EU GDPR has its own rule that research, archiving and statistics are not incompatible further processing (Article 5(1)(b)), so the comparison with the UK's Article 8A overstated the difference;
- several answers relied on provisions that were not in the gold, or left out conditions in the cited text (the processor contract, the 72-hour notification, the research safeguards, the high-risk classification), and some questions lacked a jurisdiction cue.

**What was not adopted.** Gold provisions on refusal questions (the schema says a refusal has none); claims resting on law outside the corpus that could not be verified (for example a proposed amendment of the GDPR's 250-employee threshold, and the name of the Act that inserted the UK erasure ground), which are noted in the questions instead; the reason for the 2018 wording change of Article 37(1)(c), which the text does not state.

**One design lesson.** Two gold provisions of the same question that fall in one chunk cap the best achievable nDCG below 1, because one chunk is credited with one provision. The oracle test (a ranking built from the gold must score 1 on every question) caught this once, in q019, and now guards it.

**The freeze.** `eval/gold/MANIFEST.json` records the SHA-256 fingerprint of the whole set, the date, the seed (20261015, fixed before any result was looked at and never re-drawn), the counts and the review statement. The split is 40 development and 40 test, balanced within every type and language, with exactly 31 retrieval questions in each half. A test that runs in CI fails on any edit to the set. To change a question, make a new version: edit the set, re-split only if the plan says so, write a new manifest with version 2, and treat results from version 1 as not comparable.

**The label that goes with it.** Drafted by an AI assistant, checked by scripts, independently reviewed by five AI passes, and not reviewed by a qualified lawyer or by a person for its legal content. The expected answers are reference statements of the key points, not exhaustive treatments.

## Status

Phase 2 is complete: the schema and checks, 80 questions (reviewed and frozen on 15 October 2026), the table of 19 exact facts, the metrics, and the split. The set is approved for use. A further round of independent review is planned near the end of the project, before the final write-up; any change that comes out of it makes a new version of the set (decision 67). Next: Phase 3, embeddings and the vector index, then experiments R1 to R7 against the development half, with the test half used once per decision.
