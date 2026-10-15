# Experiment index: every experiment on one page

One row per experiment or diagnostic: the question it asked, what was tried, what happened, which decision came out of it, and where the script and the full log are. Numbers are on the **development half** (31 retrieval questions, or the 40 development questions where it says so), with 95 % intervals in the full log. Anything logged before 15 October 2026 late evening used **gold version 1**; the changes of version 2 move no retrieval number that matters (`GOLD_REVIEW_2.md`). **The test half has been read once, for the retriever (T1); no other experiment has read it.** Every experiment has its plan (and the result it expected, which may turn out wrong) written in the docstring of its script, before it ran; the readings in `EXPERIMENTS.md` say which expectations failed.

How to use this page: find the row, read the decision number in `DECISIONS.md` for the reasoning, run the script, or read the section named in the last column of `EXPERIMENTS.md`.

## Phase 3: retrieval

| ID | The question | What was tried | Result (recall@5 unless stated) | Decision | Script | Section of `EXPERIMENTS.md` |
|---|---|---|---|---|---|---|
| R1.1 | How good is keyword search? | BM25 (k1 1.2, b 0.75) | **0.24** (0.12 to 0.39) | 70: the baseline | `r1_baselines.py` | R1 baselines |
| R1.2 | Does folding accents help? | BM25 with accents removed | 0.23, not better | 70 | `r1_baselines.py` | R1 baselines |
| R1.3 | Can Google's embedding model do it free? | gemini-embedding-2 | not finished: the free tier stopped it at 640 of 3,304 vectors | 75 | `r1_3_embeddings.py` | (decision log only) |
| R4.1 | Does a local embedding model beat keyword search? | BGE-M3 on the graphics card | **0.53** (0.37 to 0.69); +0.288 (+0.086 to +0.484) over BM25 | 74, 76 | `r4_bge_m3.py` | R4.1 BGE-M3 |
| R4.2 | Is a second open embedding model better, or better fused? | Qwen3-Embedding-0.6B with and without its instruction; RRF of it and BGE-M3 | 0.47 (-0.065, -0.202 to +0.073); 0.49; fusion 0.58 (+0.048, -0.048 to +0.161): none detectable | 107: BGE-M3 stays | `r4_qwen3.py` | R4.2 a second embedding model |
| R2 | Does merging keyword and embedding search help? | reciprocal rank fusion, equal weights | 0.43, worse (-0.105, -0.242 to +0.024) | 77: not adopted | `r2_fusion.py` | R2 hybrid retrieval |
| R3 | Which chunk size, and does the context line matter? | caps 200, 300, 600; no context line (BM25, then BGE-M3) | BM25: nothing detectable. BGE-M3: cap 200 0.57 (+0.040, includes 0), 300 0.54, 600 0.48; **no context line 0.37 (-0.161, -0.315 to -0.016)** | 71, 81: keep the line and the 400-word cap | `r3_bm25.py`, `r3_bge.py` | R3 (two sections) |
| R8 | Which version of a text should be indexed? | current only, original only, as-of switch (BM25, then BGE-M3) | nothing detectable (-0.008 to -0.024, all include 0) | 71, 78 | `r8_r10_bm25.py` | R8 and R10 (two sections) |
| R10 | Should copies of one provision be collapsed? | collapse copies or units | nothing detectable | 71, 78 | `r8_r10_bm25.py` | R8 and R10 |
| D-x | Do the two languages behave alike? | breakdown of R1.1 and R4.1 by language | 3 cross-language questions: BM25 0 of 3, BGE-M3 2 of 3 (described, not a claim) | 80 | `cross_language.py` | Cross-language breakdown |
| D-depth | How far down does BGE-M3 rank the right provisions? | best rank of each required provision | in the top 5 / 10 / 30 / 50 / 100: 44 / 54 / 65 / 76 / 89 %; median 8, worst 813 | 79: a reranker can add 21 points at most | `rank_depth.py` | Diagnostic: depth |
| R5 | Does a second-pass reranker help? | bge-reranker-v2-m3 over the top 30 and top 50 | 0.52 (-0.011, -0.151 to +0.129) and 0.53; 32 and 49 times slower | 82: not adopted | `r5_reranker.py` | R5 reranker |
| D-rr | Was the 512-token cut the reason? | where required provisions moved, split by cut or not | cut pairs 4 to 4 in the top 5, uncut 20 to 18: not the cause | 82 | `rerank_diagnostic.py` | Diagnostic: why the reranker did not help |
| R6.1, R6.2 | Does rewriting the question in legal vocabulary help? | rewrites by a blind agent that saw only the question texts | replace 0.68 (+0.148, +0.030 to +0.282); question plus rewrite **0.70** (+0.169, +0.040 to +0.315): an upper bound | 83, 84 | `r6_rewrite.py` | R6 question rewriting |
| R6.3 to R6.7 | Can a cheap model do the rewriting inside the system? | Gemini 3.1 and 3.5 Flash-Lite, plain and "expanding" prompts | 0.56 to 0.64, gains +0.03 to +0.105, every interval includes 0 | 84: not adopted | `r6_gemini_rewrite.py`, `r6_more_rewriters.py` | R6.3/R6.4, R6.5 to R6.7 |
| R6 filters | Do jurisdiction or language filters help? | gold-label filter (upper bound), text-derived filter, language filter, both | recall@5 0.53 for the first three, 0.56 (+0.032, +0.000 to +0.097) for both | 92: none adopted | `r6_filters.py` | R6 filters |
| R7 | Does a vector library or database beat scanning? | plain loop, NumPy, FAISS exact and approximate, sqlite-vec | same results; 113 ms, **0.7 ms**, 0.9, 0.2, 7 ms per search | 96: NumPy only | `r7_vector_store.py` | R7 vector search backends |
| D-es | Why did rewriting help English more than Spanish? | three explanations tested without a model | none held; probably no real gap | (no decision) | `spanish_diagnostic.py` | Diagnostic: Spanish against English |

## Phase 4: the answer layer (40 development questions: 31 retrieve, 4 table, 5 refuse)

| ID | The question | What was tried | Result | Decision | Script | Section |
|---|---|---|---|---|---|---|
| P4.1 | Can plain rules read a question's language, jurisdictions and date? | `answer/understand.py` | language 40/40; jurisdictions exactly right 35/40 | 85 | `p4_understand.py` | P4.1 |
| P4.2 | Which router is better, rules or a model? | rule router, Gemini router; embedding lookup of the table row | model 40/40, rules 39/40, neither refused wrongly; embeddings found the row 3 of 4 | 86 | `p4_router.py` | P4.2 |
| P4.3 | Can a model pick the table row? | Gemini picks a row or none | 4/4 right; 3 false picks on 36 other questions (my limit was 1: missed) | 87 | `p4_fact_picker.py` | P4.3 |
| P4.4 | How good is the whole layer, and what does retrieval buy? | A five passages, B eight, C five plus rewrites (upper bound), N no retrieval | correctness 0.68, 0.69, 0.79, 0.63; **A against N +0.048 (-0.097 to +0.177): not detectable**; routing, refusals and figures all right | 88, 89 | `p4_answers.py` | P4.4 and its reading |
| P4.5 | Do version-aware search and in-force dates repair two diagnosed failures? | variant D | see the section | 90, 98 | `p4_version_aware.py` | P4.5 |
| P4.7 | What does the system still do when the model is unavailable? | every model call fails; rules, similarity and plain retrieval | refusals 5/5, figures 3/4, no false refusals or figures, shown passages contain a required provision for 58 % | 103 | `p4_degraded.py` | P4.7 |
| P4.6 | The one confirmation of the answer layer on the test half | the chosen configuration against memory | not yet run (waits for the model's daily allowance) | | `p4_test_confirmation.py` | |
| T1 | Does the retriever decision hold on the sealed test half? | BM25 and BGE-M3 on the 31 test retrieval questions, gold version 2 | **0.19 and 0.55**; paired +0.360 (+0.204 to +0.527): **confirmed** | 101 | `t1_retrieval_confirmation.py` | T1 test-half confirmation |

## Reading the results honestly
- "Not detectable" means the 95 % interval of the paired difference includes 0 on only 31 questions. It does not mean "no effect".
- An experiment that fails its own pre-registered rule is logged as failed (R2, R5, R6.3 to R6.7, filters, P4.3's limit). A rule that was too strict is said to be (R7's ties).
- Variants designed after seeing development results are marked "tuned" (the expanding rewrite prompt, version-aware search, in-force dates) and wait for the test half.
- Results from different gold versions are not compared; both fingerprints are in `eval/gold/MANIFEST.json`.
