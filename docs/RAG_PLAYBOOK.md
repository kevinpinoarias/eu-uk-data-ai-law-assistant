# How to build a RAG tool: a playbook from this project

A step-by-step guide to building a retrieval-augmented generation (RAG) tool, written from what actually happened here. Each step has the same four parts: **the generic idea** (true for any RAG project), **what we did**, **what went wrong or surprised us**, and **a checklist** you can tick. Real numbers are from this project's development half and are marked as such; they show the size of effects, not constants of nature. Terms are in `GLOSSARY.md`; the full story in order is `JOURNEY.md`; the reasoning for every choice is in `DECISIONS.md`.

## 0. What RAG is, and when it is the wrong tool

**The idea.** A language model writes fluent text whether or not it is right, and knows nothing newer than its training. RAG first *retrieves* passages from a trusted collection, then asks the model to answer *only from them*, ideally with quotations a reader can check. Two stages, two ways to fail: retrieval can miss the right passage (then the model has nothing to work from), and generation can stray from the passages it was given.

**When not to use it.** If the answer is a number or a field in structured data (a price, a fine ceiling, a date), do not make the model read prose and paraphrase: look it up. In this project exact figures come from a table of 19 hand-checked rows. RAG is for unstructured prose where no schema exists, such as legislation, manuals, tickets or policies.

**A warning that shaped the whole project.** The same model answering *without* retrieval scored 0.63 on judged correctness against 0.68 with it (not a detectable difference on 31 questions). Do not assume RAG improves accuracy; measure against the no-retrieval baseline, and be clear about what retrieval *does* give you: checkable quotations, named sources and versions, refusals, and knowledge newer than the model.

**Checklist.**
- [ ] Is the answer prose, not a number in a table? If numeric, plan a lookup.
- [ ] Who is the user, and what must the tool refuse to do?
- [ ] What is the no-retrieval baseline you must beat or at least compare with?

## 1. Scope and sources: licences first

**The idea.** A RAG tool is only as good, and as legal, as its documents. Decide what is in the collection, and find out what you may do with it before you copy it.
**What we did.** Seven laws (GDPR, AI Act and its 2026 amendment, UK GDPR, Data Protection Act 2018, Data (Use and Access) Act 2025, Spain's LOPDGDD). We read each publisher's reuse terms; the Spanish regulator's guides were left out because their licence is non-commercial and would clash with our own open licence. Fetchers identify themselves, obey the sites' rules, pause between requests, and never get past a bot check (the EU publisher's pages are protected; we use its official API). Each download records where it came from, when, its fingerprint and its licence.
**What surprised us.** Facts we assumed ("the amendment's date") were wrong or unverified until read at the source; the notes are the record of what was checked.
**Checklist.**
- [ ] A table of every source: licence, credit line, what you may redistribute.
- [ ] Fetchers with an identifying User-Agent, rate limits, and a rule never to evade protections.
- [ ] Provenance stored with every document (source, date, fingerprint).
- Files: `SOURCES.md`, `src/law_assistant/fetch/`.

## 2. Parse into one common record, with checks that can fail

**The idea.** Sources are web pages or XML in different layouts. Convert them all into one small record (here a *provision*: a recital, article, paragraph or point, with an id like `eu-gdpr/art-6/1/f`). Everything downstream depends on this being right, and a parser fails *quietly*: if it drops an article, nothing complains.
**What we did.** Checks that can actually fail: ids unique and numbering without gaps; known totals (99 GDPR articles, 173 recitals); English and Spanish with the same skeleton; letters and digits kept add up to those in the source (coverage); consolidated text matches the original except where an amendment explains the difference.
**What went wrong.** The checks caught real bugs: an AI Act annex whose body was silently dropped (we had first called a 99.87 % coverage "typography"; it was a bug), Spanish Article 4 in a different layout, and UK "omitted" provisions stored as lines of dots, which became 36 meaningless chunks. Each became a permanent test.
**Checklist.**
- [ ] Coverage check against the source, not just "it ran".
- [ ] Known counts and cross-language/skeleton checks.
- [ ] Every bug found becomes a test.
- Files: `PARSING.md`, `src/law_assistant/parse/`.

## 3. Chunk along the document's own structure

**The idea.** The chunk is what search finds and returns; its shape decides what can be found. Too small and it means nothing alone ("(f) legitimate interests"); too big and it is imprecise and may exceed a model's input.
**What we did.** Cut along the law's structure (an article, or its paragraphs when long), restore the numbering, cap at 400 words, and put a **context line** in front ("GDPR | Chapter II | Article 6: Lawfulness of processing"). 3,831 chunks; ids are deterministic.
**What mattered.** The context line was the one chunking choice that clearly mattered: without it recall@5 fell from 0.53 to 0.37 (paired -0.161, interval -0.315 to -0.016), because an embedding model reads the whole text as one meaning and the line says which law and article it is reading. Chunk size (200, 300, 400, 600 words) changed nothing detectable. Moral: write 400 as a *guess*, then test it, and do not fall in love with a size.
**Checklist.**
- [ ] Structure-aware cuts; no chunk empty or over the cap; nothing lost.
- [ ] A context line (title, section, source) in the embedded text.
- [ ] Deterministic ids that survive re-chunking.
- Files: `CHUNKING.md`, `src/law_assistant/chunk/`.

## 4. Write the gold set first, review it blind, freeze it

**The idea.** To know whether the system is any good you need questions whose right answers a person wrote down *before* building. If you write the test after the system, you write questions it already handles.
**What we did.** 80 questions (half English, half Spanish; mostly lay wording; lookups, definitions, cross-references, EU-versus-UK comparisons, Spanish law, date-dependent questions, exact figures, and questions that **must be refused**). Labels name the provision by instrument and unit (never by chunk), with optional pinpoints, a version and a role (primary or acceptable), so the gold survives any re-chunking. Scripts check every cited unit, pinpoint and quotation exists, that no question copies its answer's words, and that figures agree with the facts table. Then **independent reviewers** (five blind AI passes, twice) saw only the question, the expected answer and the cited text, and could edit nothing; every finding was verified before being adopted. The set was split 40 for tuning and 40 for one final test with a fixed seed, and **frozen** with a fingerprint that a test checks.
**What went wrong.** The first review found 12 serious problems in the first draft: a question built on a false premise, a legal term defined too broadly, a wrong article cited. The second found 10 more corrections, and showed that a reviewer can only judge what it is shown: three "major" findings were dates held in metadata the reviewers did not see, which exposed that our own answer writer never saw them either.
**Honest label.** Drafted by an AI assistant, checked by scripts, reviewed by AI passes, **not reviewed by a lawyer.** Say so wherever the set is mentioned.
**Checklist.**
- [ ] Include refusal questions, exact-figure questions, date-dependent questions, and some in each language you support.
- [ ] Labels by provision, not chunk.
- [ ] Machine checks; blind independent review; verify each finding.
- [ ] Split with a fixed seed; the test half read once; freeze with a hash; a change means a new version.
- Files: `GOLD_SET.md`, `GOLD_REVIEW_2.md`, `eval/gold/`.

## 5. Choose metrics, and know what your sample can detect

**The idea.** A ranked list is scored by whether, and how high, the right passages appear. The main score should match how the answer layer will use the list.
**What we did.** hit@k, recall@k, MRR, nDCG; the headline is **recall@5** (the answer writer reads about five passages). Each gold provision is credited once, so duplicate copies cannot inflate the score. Every score has a bootstrap interval; two variants are compared with a *paired* bootstrap on the same questions so noise cancels.
**The hard truth about small samples.** With 31 development retrieval questions an interval is about plus or minus 0.15, so only large effects are detectable. Many of our results are "not detectable", which is not "no effect". Say which one it is, and do not pool non-significant results into a significant one.
**Checklist.**
- [ ] A primary metric chosen *before* experiments.
- [ ] Intervals everywhere; paired comparisons.
- [ ] A statement of what the sample can and cannot detect.
- Files: `METRICS.md`, `src/law_assistant/evaluation/`.

## 6. Baselines before cleverness

**The idea.** Build the dumbest things first: a random ranking (the floor), an oracle built from the gold (must score 1 on every question, which tests the test), and keyword search. They tell you the scale of the problem.
**What we did.** Random hit@10 about 1.3 %; the oracle caught a real flaw (two gold provisions in one chunk cap nDCG below 1); BM25 got recall@5 0.24. A diagnostic on *why* BM25 failed (the right article ranked 724th of 3,831: the question says "person responsible for data protection", the law says "data protection officer") pointed straight at embeddings.
**Checklist.**
- [ ] Random and oracle rankings; the oracle must score 1.
- [ ] A keyword baseline and a look at *why* it fails.

## 7. The experiment protocol (the habit that matters most)

**The idea.** Experiments are cheap to run and easy to fool yourself with. A protocol removes the temptation to keep the flattering result.
**Our protocol.**
1. A plan file lists every experiment, the primary metric and the **decision rule** (here: adopt a variant only if the lower end of its paired 95 % interval of improvement is above 0).
2. Each experiment script starts with a **pre-registration** in its docstring, written *before* the first run: the variant, the data, the metrics, the rule, and **the result you expect** (so you can be wrong on the record).
3. Tune only on the development half; the test half is read once per decision.
4. Every variant is counted and logged, including failures. A variant designed after seeing results is labelled "tuned".
5. The log records the commit and the gold fingerprint of every run.
6. A reading section afterwards says which expectations failed.
**What it bought us.** It let us write "the reranker did not help" and "fusion was worse" and "the cheap rewriter was not detectable" without flinching, and it stopped us tuning fusion weights until fusion won. It also showed when a rule was too strict (R7's ties) and we said so.

**A template for the top of a script:**
```
PRE-REGISTRATION (written <date>, before <what has not yet happened>)
Variant(s): ...            Data: ...
Primary metric: ...        Also reported: ...
Decision rule: a variant is adopted if ...
Stated expectation (can be wrong): ...
```
- Files: `PHASE3_PLAN.md`, `EXPERIMENTS.md`, `EXPERIMENT_INDEX.md`, `experiments/`.

## 8. Retrieval: what moved the number, in the order we found it

| Lever | Effect (recall@5, dev) | Lesson |
|---|---|---|
| Keyword search (BM25) | 0.24 | the vocabulary gap between lay questions and legal text |
| Embedding model (BGE-M3, local) | **0.53** | the first big, detectable gain |
| Context line in each chunk | 0.37 without it | tell the model what it is reading |
| Rewrite the question in the law's words | 0.70 (strong writer); +0.03 to +0.11, not detectable (cheap in-system models) | the wording of the query mattered more than the machinery, but a cheap model did not reproduce the gain |
| Merging keyword and embeddings (RRF) | 0.43 (worse) | a weak list can drag down a strong one |
| Reranker (cross-encoder) | 0.52, 32 times slower | standard practice is not automatic improvement |
| Chunk size, version policy, duplicate collapsing, jurisdiction/language filters | nothing detectable | tidying what the search may return changes little |
| Vector database or FAISS | same results; NumPy 0.7 ms vs 113 ms for a Python loop | not needed below hundreds of thousands of chunks |

**General lessons.**
- **Diagnose before you build.** Measure where the right passages rank (here 44 % in the top 5, 65 % in the top 30, 89 % in the top 100) before choosing a reranker: it can only reorder what the first stage found, so it was capped at about 21 points before we downloaded anything.
- **A weak stage hides the effect of later stages.** With BM25 at 0.24, chunk-size and version experiments were uninformative; they were repeated once embeddings existed.
- **Ties exist.** Copies of one text have identical vectors; order among ties must be fixed (by id) or two correct methods will look different.
- **Cache embeddings by model and prompt.** 3,831 chunks were only 3,304 distinct prompts.
**Checklist.**
- [ ] Measure the rank-depth of the right passages before adding a stage.
- [ ] Try the cheap things (context line, query wording) before the expensive ones.
- [ ] Keep a table like the one above; failures belong in it.
- Files: `HOW_RETRIEVAL_WORKS.md`, `EXPERIMENTS.md`.

## 9. The answer layer: make trust a property of code, not of the model

**The idea.** Everything that can be checked with ordinary code should be, because it is exact, free and cannot be talked round. Reserve the model for writing.
**What we built, in order.**
1. **Understand** the question with rules (language 40/40, jurisdictions 35/40).
2. **Route** it: retrieve, look up an exact figure, or refuse (model router 40/40; rules 39/40).
3. **Look up exact figures** in the table, picking the row with a model behind the router.
4. **Search** (current text unless a date is stated; copies of a provision collapsed; five passages).
5. **Write** from numbered passages as JSON, with quotations copied exactly.
6. **Verify in code** that every quotation exists in the passage it names; drop failures; if none remain, **decline** instead of answering.
7. **Label** the law, provision and text version from the chunk's own fields (never from the model).
8. **Refuse** other countries' law, regulators' guides and advice on the user's situation, in the user's language.
**What went wrong, and what the measurement said.**
- The layer was **not detectably more correct** than the model's memory (0.68 against 0.63, interval -0.10 to +0.18). Its value is verifiability and refusals, and we claim only that.
- A **model judge is biased**: ours was too generous on 2 of the 12 verdicts I read, and one of those exposed a real bug (the 2026 amendment's dates quoted for a question dated 1 January 2026).
- **Dates and versions are half the difficulty in law.** The writer was never shown the chunk's in-force date; the fix is an option measured separately.
**Checklist.**
- [ ] A router with refusals and an exact-figure path; both measured.
- [ ] Quotations required, and checked in code.
- [ ] Source labels built from data, not by the model.
- [ ] A no-retrieval baseline; a judge you have read a sample of.
- [ ] Refusal and decline are different behaviours; test both.
- Files: `HOW_THE_ANSWER_LAYER_WORKS.md`, `PHASE4_PLAN.md`, `src/law_assistant/answer/`.

## 10. Working with the limits of APIs and free tiers

**The idea.** A free tier has quotas you do not control, and they decide how many experiments you can run in a day.
**What happened.** The first embedding run was throttled to a crawl; a generation quota (500 requests a day for the cheap model, 20 for the larger one) ran out mid-experiment, and the reply said "retry in 9 hours"; our client slept obediently and the run looked frozen. A model we planned to use was closed to new accounts; another needed more output tokens because it reasons before answering.
**What we do now.** Fail fast on any wait over five minutes and say why; cache every model answer on disk by model, prompt and settings so a rerun makes no calls; count calls before an experiment and budget them (a full evaluation is about 250 calls); fix a prompt's wording before running, because changing it invalidates the cache.
**Checklist.**
- [ ] Read the whole error message; never sleep through a long retry delay.
- [ ] A disk cache keyed by everything that affects the answer.
- [ ] A call budget per experiment.
- [ ] A paid key and a budget alert before a public launch.
- Files: `src/law_assistant/llm/gemini.py`.

## 11. Shipping: limits, privacy, traces, container, checks

**The idea.** Most of what goes wrong with a public AI demo is not the model: it is cost, abuse, privacy, slow starts and silent failures.
**What we did.** A service layer that limits each visitor (6 questions a minute) and everyone (300 a day), caps question length, hides internal errors, and writes a trace per question without the visitor's address; a one-file web page (phone, dark mode, a disclaimer, no outside libraries); traces deleted after 30 days and a notice not to type personal data; a CPU container (a question embeds in 0.12 s on a CPU); CI that runs lint, tests and a secret scan; a rule that the live link goes in the README only after the sealed test half has been read.
**The irony to remember.** A data-protection assistant that logs what people type is itself processing personal data. Apply to yourself what the tool explains.
- Files: `PHASE5_PLAN.md`, `DEPLOYMENT.md`.

## 12. Documentation habits that made this auditable

- **A decisions log** (`DECISIONS.md`): one row per choice with its date, the choice, the evidence and the alternatives considered. 100 rows so far; no names in it.
- **A journey** (`JOURNEY.md`): each step in three parts (the idea, why we did it, what we found).
- **An experiment log and index** with the commit and the gold fingerprint of every run.
- **A glossary** for every term; **honest labels** (not lawyer-reviewed; not legal advice; tuned variants marked).
- **Pre-registered expectations** so "I was wrong" is on the record.
- **Memory of what was checked** versus what was assumed: unverified sizes and prices are marked unknown until read.

## 13. Mistakes we made and what caught them

| Mistake | What caught it | Fix |
|---|---|---|
| Parser dropped an annex's body; first excused as "typography" | the empty-chunk check | fixed, tested; the excuse corrected in the docs |
| Dotted "omitted" UK provisions became empty chunks | chunk checks | skipped, counted, documented as known gaps |
| A gold answer cited the wrong article | blind reviewers | corrected; the process documented |
| Two gold provisions in one chunk capped nDCG | the oracle test | rule and test added |
| A client slept 9 hours on a quota message | a frozen-looking run | fail-fast on long waits |
| A judge passed an anachronistic answer | reading a sample of verdicts | repair built; judge's bias reported |
| A pre-registered rule too strict about ties | the diagnosis of a "disagreement" | said so; adopted the optimisation |
| A reviewer's "major" findings were metadata the packet omitted | tracing the dates to chunk metadata | showed a real gap in the system |
| Search index rewrote 51 MB after every query | measuring for deployment | in-memory option for serving |
| Expected explanations that turned out wrong (Spanish gap) | testing three explanations | concluded "probably noise" |

## 14. A short checklist for your own RAG project

1. Scope the collection; check every licence; keep provenance.
2. Parse to one record; add checks that can fail; turn each bug into a test.
3. Chunk by structure with a context line; test size as a guess.
4. Write, review blind, split and freeze the gold set; label it honestly.
5. Choose the primary metric; use intervals and paired comparisons.
6. Build random, oracle and keyword baselines; diagnose the failures.
7. Pre-register each experiment with its rule and expectation; log failures.
8. Cheap levers first (embedding model, context line, query wording); measure ceilings before adding stages.
9. Make trust a property of code: route, look up numbers, verify quotations, decline, refuse.
10. Compare with the no-retrieval baseline and read a sample of the judge's work.
11. Budget calls; cache answers; fail fast on quotas.
12. Ship with limits, privacy and traces; read the sealed test half once, then publish.

## 15. The sealed test half: how and when to read it

**The idea.** The test half is only worth something if it is read once per decision, after the decision is made. Reading it to *choose* between variants turns it into a second development set.
**What we did.** Retrieval was settled first (BGE-M3 plain), so its decision was confirmed on the test half alone, with the plan committed to git before the run and a guard in the script that refuses a second read. Result: recall@5 0.55 on unseen questions against 0.53 on development, so no overfitting to the development half.
**Rules we hold to.** One read per decision; the configuration, the rule and the expectation are written and committed first; anything designed after seeing development results is labelled tuned and is tested on the test half, not trusted; whatever comes out is reported, including a failure.
**Checklist.**
- [ ] Decide the configuration on the development half only.
- [ ] Commit the pre-registration before the run; add a guard against a second read.
- [ ] Compare with the same baseline as on development.
- [ ] Report it in the README next to the development number.
