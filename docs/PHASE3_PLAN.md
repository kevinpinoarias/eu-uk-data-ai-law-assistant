# Phase 3 plan: retrieval experiments (draft for approval, 15 October 2026)

Nothing here has been run. This plan fixes the method, the variants and the decision rules before any result exists (pre-registration). Anything not in this file when an experiment runs counts as exploration and is labelled that way.

## 1. What a retrieval experiment is

**Generic idea.** A retrieval system is a pipeline of design choices: how documents are cut, how text is turned into searchable form, how candidates are found and ordered. Each choice can help, do nothing, or hurt, and intuition is unreliable. An experiment changes one choice against a baseline, scores both on a fixed question set, and asks whether the difference is bigger than the noise. The discipline that makes the answer trustworthy: write the plan first, tune on one set of questions and confirm on another, count how many things were tried, and log failures.

**Here.** The questions are the frozen gold set (fingerprint `7d9a62f5…`). Tuning uses the 31 development retrieval questions only. The 31 test questions are looked at once per decision, by the pipeline we propose to adopt against its baseline.

## 2. The experiments

### In the roadmap, Phase 3 (seven)

| | Question | Variants (planned) |
|---|---|---|
| R1 | How good are keyword search and embedding search alone? | 3 |
| R2 | Does combining them (reciprocal rank fusion) beat either? | 2 to 3 |
| R3 | Is the 400-word article-based chunk right? Does the context line help? | 5 to 6 |
| R4 | Which embedding model, including across languages? | about 4 |
| R5 | Does a reranker earn its latency? | 1 to 2 |
| R6 | Do filters (jurisdiction, language, as-of) and query rewriting help? | about 4 |
| R7 | Does a vector database beat scanning every vector? | 3 |

### In the roadmap, later phases (evaluations, not retrieval tuning)

| | What | Phase |
|---|---|---|
| 4.4 | Baselines for the whole system: no retrieval at all, and the whole corpus in the prompt where it fits | 4 |
| 4.5 | Routing evaluation: do numeric questions reach the table and narrative ones retrieval? (the project's central claim) | 4 |
| 4.6 | Answer-model comparison: Gemini Flash-Lite against a larger Gemini Flash and an open model | 4 |
| 4.2, 4.3 | Citation checks and abstention behaviour, measured on the gold set | 4 |

### Proposed additions (not in the roadmap; need your approval)

| | Why it is a real question here | Where it would sit |
|---|---|---|
| R8 Index version policy | The index holds the original and the consolidated text of the GDPR and the AI Act, in two languages. Should both be indexed, or only the current text plus the original where a question is about the past? Returning the superseded wording for a today question is a wrong answer, and 14 gold questions are version-sensitive. | after R6 (it interacts with the as-of filter) |
| R9 Top-k and neighbours | How many chunks should the answer layer get (3, 5, 8, 10), and should the pieces next to a hit, or the article's opening lines, come with it? This was left open in `CHUNKING.md`. | after R5 |
| R10 Duplicate collapsing | The same article appears as up to a dozen near-copies (two languages, two versions, several pieces). Do results improve if copies of one unit are collapsed to the best one, so top-5 slots are not wasted? | with R9 |
| R11 Query language handling | A Spanish question against an English-only text (and back): does translating the query help, or do multilingual embeddings already cover it? | inside R4 (cross-language cases) |

So: seven in the roadmap for retrieval, three evaluations later in the roadmap, and four proposed additions (R8 to R11; R11 is a sub-analysis of R4). Together about 25 variants will be tried and counted, and every one is logged.

## 3. Shared method (applies to every experiment)

- **Data.** Chunks in `data/chunks/` (3,831, rebuilt by `python -m law_assistant.chunk.run_chunk`); gold questions in `eval/gold/`, retrieval questions only (62 of 80; 31 per half).
- **Run files.** A retriever turns each question into a ranked list of chunk ids; `evaluation.metrics.score_run` scores it. Run files go to `data/runs/` (git-ignored); the summary of every run goes to `docs/EXPERIMENTS.md` (committed).
- **Primary metric: recall@5.** It is what the answer layer will see: the share of the required provisions found in the top 5 chunks. Secondary: MRR, nDCG@10, hit@5, recall@10. Chosen now so no one can pick the flattering metric afterwards.
- **Comparison.** Paired bootstrap on the same development questions (10,000 resamples, seed 0), reported as the change against the stated baseline with a 95 % interval.
- **Decision rule.** A variant is adopted only if the lower end of the interval of its improvement in recall@5 is above 0. Otherwise the simpler variant stays, and the write-up says "no detectable difference". On 31 questions only fairly large effects can pass; that is a property of the evidence, not a reason to lower the bar.
- **Ties and cost.** If two variants are not distinguishable, prefer the one that is cheaper, simpler and needs no download or key.
- **Many variants, many chances.** About 25 variants will be tried, so a few will look better by luck. The count is reported next to every claim, and the final pipeline is confirmed once on the test half against the R1 baseline, not against a hand-picked rival.
- **Reference rows.** Every table also shows the random ranking (hit@10 of about 1.3 %) and the oracle (1.0), so the scale is visible.
- **Interactions.** R1 to R3 run with a provisional embedding model; after R4 picks the model, R2 and R3 are re-checked once with it. That is two extra runs, counted.
- **Logging.** Each run records the experiment, the variant, the date, the git commit, the model and settings, and the metrics with intervals. Failures are logged like successes. A pre-registration docstring sits at the top of each experiment script, written before it first runs.

## 4. Step 3.0: the harness (no downloads, no installs)

Built test first, using only the standard library.

1. **A retriever interface:** an object with `search(query, k)` returning ranked chunk ids, plus a builder that indexes a list of chunks.
2. **BM25 in plain Python.** BM25 scores a chunk by how often and how rarely the query's words appear in it. Tests use a tiny corpus where the scores are worked out by hand; ties break by chunk id so results are reproducible.
3. **The runner:** run a retriever over the retrieval questions, write the run file, score it, append a row to the experiments log.
4. **Reference retrievers:** random, and oracle (built from the gold). The oracle must score 1 on every question and random must score near zero, exactly as the metrics tests already require.

Tests include: BM25 on a hand-checked example; deterministic ordering; the runner on the real chunks with the oracle scoring 1.

## 5. R1 in detail (pre-registration)

**Question.** How well do the two standard baselines retrieve the right law on the development questions?

**Variants.**
- R1.1 BM25 over the chunk's context line and text, lower-cased, split on letters and digits, no stemming, no stop words, standard parameters (k1 = 1.2, b = 0.75). No tuning of the parameters in R1.
- R1.2 The same with accents folded (protección and proteccion match), because real users often type without them.
- R1.3 Embedding search over the same text with the provisional model (see section 7), cosine similarity, brute force.

**Reported:** all metrics, overall and split by question type, by language of the question and by whether the question shares few words with its answer (the weighted overlap from the gold checks). The point of the split is to see where each baseline fails.

**What each outcome means (written before the run).** If BM25 beats embeddings on recall@5, the lay-wording gap is smaller than feared and hybrid search (R2) is the next test. If embeddings win clearly on lay questions but BM25 wins on legal terms, that predicts a hybrid gain. R1 adopts nothing: it fixes the baselines that R2 to R7 are measured against. The baseline for "the current pipeline" is the better of R1.1 and R1.2 (or R1.3 if it is clearly better).

**Honest expectation, stated now so it can be wrong:** embeddings will beat BM25 on the lay and cross-language questions, BM25 will beat embeddings on questions that quote legal terms, and neither will be above 0.9 on recall@5.

## 6. R2 to R7 in outline (full pre-registration written before each runs)

- **R2 Hybrid.** Reciprocal rank fusion of BM25 and embeddings, with a fixed constant of 60 and no tuning. Variants: fusion of R1.1 with R1.3; of the best BM25 with R1.3; plus a weighted version only if the unweighted one shows promise.
- **R3 Chunking.** Cap 200, 300, 400, 600 words; paragraph-level chunks; parent-and-child (search small, return the surrounding article); context line on and off. Chunk sets are rebuilt by the existing builder; the gold needs no change because it labels provisions, not chunks.
- **R4 Embedding models.** The hosted free model against two open multilingual models, same-language and cross-language, with the cross-language cases of the gold set analysed separately.
- **R5 Reranker.** One cross-encoder over the top 30; report latency next to accuracy.
- **R6 Filters and rewriting.** Jurisdiction and language filters set from the question; an as-of filter; a rewritten query. Run with the gold's own jurisdiction labels as an upper bound, then with inferred ones.
- **R7 Vector store.** NumPy brute force against FAISS against one database. At 3,831 chunks I expect no accuracy difference, and the write-up should say so and give the size at which that changes; the real differences are filtering, persistence and effort.

## 7. What needs your approval (standing rule: ask before any download or install)

Nothing is needed for step 3.0 or for R1.1 and R1.2. For the embedding runs I need one of the following, and I will give the exact filename, source and size before you decide:

- **Option A, hosted:** a free Gemini API key in `.env`, one small client file, no large download. Legal texts are public, so nothing private leaves the machine; the free tier is for private development only (decision 3 and the billing note still apply to a public demo).
- **Option B, open model on this machine:** a multilingual embedding model and the libraries to run it, a download in the hundreds of megabytes to a few gigabytes depending on the model and on whether a GPU build of the numerical library is chosen.
- **Option C, start with BM25 only,** run R1.1 and R1.2 now, and defer the embedding decision until you have chosen.

I recommend C first (nothing to install, and it produces real numbers today), then A for R1.3 and R4's hosted candidate, then B when R4 needs the open models.

## 8. Order of work

1. Step 3.0, the harness and BM25 (test first).
2. R1.1 and R1.2, logged.
3. Your decision on embeddings, then R1.3.
4. R2, R3, R4 (then the re-check), R5, R6, R8, R9 and R10, R7.
5. One confirmation run on the test half: the adopted pipeline against the R1 baseline.
6. A second round of independent review of the gold set before the final write-up (decision 67); any change makes a new version.
