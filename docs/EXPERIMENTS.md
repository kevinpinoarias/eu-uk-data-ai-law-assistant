# Experiment log


## R1 baselines, run 2026-10-15 (commit 9243e0c; gold fingerprint 7d9a62f5)

### R1 baselines on the development questions (31 retrieval questions)

| Variant | recall@5 | mrr | ndcg@10 | hit@5 | recall@10 |
|---|---|---|---|---|---|
| R1.1 BM25 plain | 0.24 (0.12 to 0.39) | 0.25 (0.13 to 0.40) | 0.22 (0.11 to 0.35) | 0.35 (0.19 to 0.52) | 0.30 (0.17 to 0.45) |
| R1.2 BM25 accents folded | 0.23 (0.11 to 0.36) | 0.25 (0.13 to 0.40) | 0.21 (0.11 to 0.33) | 0.35 (0.19 to 0.52) | 0.28 (0.15 to 0.42) |
| oracle (ceiling) | 1.00 (1.00 to 1.00) | 1.00 (1.00 to 1.00) | 1.00 (1.00 to 1.00) | 1.00 (1.00 to 1.00) | 1.00 (1.00 to 1.00) |
| random (floor, mean of 20 draws) | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) | 0.00 (0.00 to 0.00) | 0.01 (0.01 to 0.01) |

R1.2 against R1.1, recall@5: difference -0.016, 95 % interval -0.048 to +0.000; share of resamples in which R1.2 is not better 1.00.

Recall@5 by question type (R1.1 BM25 plain, R1.2 folded; number of questions):

- as_of: 0.20, 0.20 (n = 5)
- comparison: 0.22, 0.22 (n = 5)
- cross_reference: 0.20, 0.20 (n = 5)
- definition: 0.38, 0.38 (n = 4)
- lookup: 0.12, 0.12 (n = 8)
- spanish_law: 0.50, 0.38 (n = 4)

Recall@5 by question language (R1.1 BM25 plain, R1.2 folded; number of questions):

- en: 0.18, 0.18 (n = 17)
- es: 0.32, 0.29 (n = 14)

Recall@5 by shared words with its gold text (R1.1 BM25 plain, R1.2 folded; number of questions):

- shares few words: 0.22, 0.20 (n = 19)
- shares many words: 0.28, 0.28 (n = 12)

**Against the stated expectations.** "Neither baseline exceeds 0.9 recall@5": true (0.24). "Keyword search does well where a question uses the law's own words": only weakly supported (recall@5 0.28 for questions that share many words with their gold text, against 0.22 for those that share few; with 12 and 19 questions the difference is not detectable). Decision rule: R1.2 is not better than R1.1 (the lower end of the paired interval is 0.000 and R1.2 is not better in every resample), so R1.1 is the current pipeline for later comparisons. R1.3 (embeddings) has not been run.

### Exploration after R1 (not pre-registered; a diagnostic, not a result to decide on)

- Every one of the 155 chunks in the development questions' top 5 is in the question's own language, so keyword search cannot cross languages (a Spanish question about the English-only UK Acts, or the reverse, cannot be answered by it).
- A top 5 holds on average 0.77 repeated units (the same article as the original and the consolidated text, or two pieces of one article), so copies use up slots (this is the case for R10).
- Only 13 of the 31 questions have all their primary provisions anywhere in BM25's top 50.
- q004 ("Do I need to name a person responsible for data protection..."): the right article (GDPR Article 37) ranks 724th of 3,831; its text says "designate" and "data protection officer", not "name" or "responsible". The top result is a section of the Data (Use and Access) Act that shares ten of the question's words, mostly common ones.
- q005 (Spanish, "cambio de proveedor"): the top results are AI Act articles, where "proveedor" means the provider of an AI system, not the data-portability provider the user meant. I have not traced the scoring, so this is a likely cause, not a verified one.



## R8 and R10 with BM25, run 2026-10-15 (commit 195c796; gold fingerprint 7d9a62f5)

### R8 and R10 with BM25 on the development questions (31 retrieval questions)

| Variant | recall@5 | mrr | ndcg@10 | hit@5 | recall@10 |
|---|---|---|---|---|---|
| R8.1 everything (baseline R1.1) | 0.24 (0.12 to 0.39) | 0.25 (0.13 to 0.40) | 0.22 (0.11 to 0.35) | 0.35 (0.19 to 0.52) | 0.30 (0.17 to 0.45) |
| R8.2 current text only | 0.25 (0.12 to 0.40) | 0.26 (0.14 to 0.41) | 0.23 (0.12 to 0.36) | 0.35 (0.19 to 0.52) | 0.32 (0.19 to 0.47) |
| R8.3 original for past dates, current otherwise | 0.25 (0.12 to 0.40) | 0.26 (0.14 to 0.41) | 0.23 (0.12 to 0.36) | 0.35 (0.19 to 0.52) | 0.32 (0.19 to 0.47) |
| R10.1 collapse copies of a piece | 0.24 (0.12 to 0.39) | 0.26 (0.13 to 0.40) | 0.23 (0.12 to 0.35) | 0.35 (0.19 to 0.52) | 0.31 (0.17 to 0.46) |
| R10.2 collapse to one chunk per unit | 0.24 (0.12 to 0.39) | 0.26 (0.13 to 0.41) | 0.23 (0.12 to 0.36) | 0.35 (0.19 to 0.52) | 0.31 (0.17 to 0.46) |

Each variant against R1.1 on recall@5 (paired bootstrap), and recall@5 on the 12 version-sensitive questions:

- R8.1 everything (baseline R1.1): difference +0.000 (95 % interval +0.000 to +0.000); version-sensitive recall@5 0.12 (baseline 0.12)
- R8.2 current text only: difference +0.008 (95 % interval +0.000 to +0.024); version-sensitive recall@5 0.12 (baseline 0.12)
- R8.3 original for past dates, current otherwise: difference +0.008 (95 % interval +0.000 to +0.024); version-sensitive recall@5 0.12 (baseline 0.12)
- R10.1 collapse copies of a piece: difference +0.000 (95 % interval +0.000 to +0.000); version-sensitive recall@5 0.12 (baseline 0.12)
- R10.2 collapse to one chunk per unit: difference +0.000 (95 % interval +0.000 to +0.000); version-sensitive recall@5 0.12 (baseline 0.12)

Gold provisions no chunk of the index can satisfy (of the development questions):

- all texts: 0 (none)
- current text only: 2 (q044, q048)
- original text only: 14 (q004, q009, q013, q020, q025, q026, q044, q047, q048, q072)

**Reading this result against the pre-registered rules and expectations.** Nothing is adopted: R8.2 and R8.3 improve recall@5 by 0.008 with an interval of 0.000 to 0.024, and the rule needs the lower end above 0; R10.1 and R10.2 change nothing (0.000 in every resample). The expectations: R8.2 does zero the two development questions about the original text (q044, q048 become unreachable), as stated; R8.2 raising recall on undated questions is in the right direction but not detectable; "R10.1 helps a little" was wrong here (no change). R8.3 still loses q048, a question about both versions, because its date is today, which shows that an as-of rule based on one date cannot serve a question that compares versions.

**Why so little moved, and what this does not show.** BM25 finds the right unit in its top 10 for only about 30 % of the required provisions, so freeing slots (R10) or removing superseded copies (R8) has little to act on: the bottleneck is the vocabulary gap, not the slots. These questions are therefore not answered yet; they are repeated with embeddings once R1.3 exists, where the other language's copy of each article is also returned and the picture may differ. Conclusions here are provisional by design.



## R3 chunk size and context line with BM25, run 2026-10-15 (commit 6986e7f; gold fingerprint 7d9a62f5)

### R3 (chunk size, context line) with BM25 on the development questions (31 questions)

| Variant | recall@5 | mrr | ndcg@10 | hit@5 | recall@10 |
|---|---|---|---|---|---|
| R3.1 cap 400 (baseline R1.1) | 0.24 (0.12 to 0.39) | 0.25 (0.13 to 0.40) | 0.22 (0.11 to 0.35) | 0.35 (0.19 to 0.52) | 0.30 (0.17 to 0.45) |
| R3.2 cap 200 | 0.22 (0.10 to 0.35) | 0.25 (0.12 to 0.40) | 0.23 (0.12 to 0.35) | 0.35 (0.19 to 0.52) | 0.29 (0.16 to 0.44) |
| R3.3 cap 300 | 0.21 (0.10 to 0.35) | 0.23 (0.11 to 0.36) | 0.21 (0.10 to 0.33) | 0.32 (0.16 to 0.48) | 0.30 (0.17 to 0.45) |
| R3.4 cap 600 | 0.24 (0.12 to 0.39) | 0.22 (0.11 to 0.34) | 0.20 (0.11 to 0.31) | 0.35 (0.19 to 0.52) | 0.31 (0.18 to 0.46) |
| R3.5 cap 400, no context line | 0.22 (0.10 to 0.36) | 0.23 (0.10 to 0.38) | 0.20 (0.09 to 0.32) | 0.29 (0.13 to 0.45) | 0.27 (0.13 to 0.42) |

Each variant against R3.1 on recall@5 (paired bootstrap), with the size of its index:

- R3.1 cap 400 (baseline R1.1): difference +0.000 (95 % interval +0.000 to +0.000); 3,831 chunks, mean 218 words
- R3.2 cap 200: difference -0.024 (95 % interval -0.065 to +0.000); 6,278 chunks, mean 133 words
- R3.3 cap 300: difference -0.032 (95 % interval -0.097 to +0.000); 4,574 chunks, mean 182 words
- R3.4 cap 600: difference +0.000 (95 % interval +0.000 to +0.000); 3,195 chunks, mean 261 words
- R3.5 cap 400, no context line: difference -0.027 (95 % interval -0.059 to +0.000); 3,831 chunks, mean 218 words

**Reading this result.** Nothing is adopted: no variant's paired interval has its lower end above 0 (the upper end of every interval is exactly 0.000, because no variant improves a single question's recall@5 on net). Against the stated expectations: "recall@5 changes little with chunk size" holds (cap 200 and 300 are 0.02 to 0.03 lower, cap 600 equal); "smaller chunks raise hit@5 on lookups" was wrong (hit@5 is 0.35 at caps 200 and 400 and 0.32 at 300); "leaving the context line out lowers recall@5 slightly" is the point estimate (0.22 against 0.24; hit@5 falls from 0.35 to 0.29) but is not detectable at this sample size. Cap 600 does not lose anything with BM25, but it would exceed the 512-token limit of multilingual-e5 and is not a free choice for R4. Provisional, to be repeated with embeddings: BM25's weak baseline (0.24) limits how much any chunking choice can show.



## R4.1 BGE-M3, run 2026-10-15 (commit e7f7e20; gold fingerprint 7d9a62f5)

### R4.1 BGE-M3 on the development questions (31 retrieval questions)

| Variant | recall@5 | mrr | ndcg@10 | hit@5 | recall@10 |
|---|---|---|---|---|---|
| R1.1 BM25 plain | 0.24 (0.12 to 0.39) | 0.25 (0.13 to 0.40) | 0.22 (0.11 to 0.35) | 0.35 (0.19 to 0.52) | 0.30 (0.17 to 0.45) |
| R4.1 BGE-M3 | 0.53 (0.37 to 0.69) | 0.46 (0.31 to 0.62) | 0.48 (0.34 to 0.62) | 0.61 (0.45 to 0.77) | 0.63 (0.47 to 0.78) |

R4.1 against R1.1, recall@5: difference +0.288, 95 % interval +0.086 to +0.484; share of resamples in which BGE-M3 is not better 0.00.
Chunks cut at 1024 tokens: 0 of 3831.

Recall@5 by question type (R1.1 BM25, R4.1 BGE-M3; number of questions):

- as_of: 0.20, 0.40 (n = 5)
- comparison: 0.22, 0.35 (n = 5)
- cross_reference: 0.20, 0.40 (n = 5)
- definition: 0.38, 0.44 (n = 4)
- lookup: 0.12, 0.75 (n = 8)
- spanish_law: 0.50, 0.75 (n = 4)

Recall@5 by question language (R1.1 BM25, R4.1 BGE-M3; number of questions):

- en: 0.18, 0.51 (n = 17)
- es: 0.32, 0.55 (n = 14)

Recall@5 by shared words with its gold text (R1.1 BM25, R4.1 BGE-M3; number of questions):

- shares few words: 0.22, 0.59 (n = 19)
- shares many words: 0.28, 0.44 (n = 12)


## R2 hybrid retrieval with bge, run 2026-10-15 (commit e7f7e20; gold fingerprint 7d9a62f5)

### R2 hybrid retrieval (bge) on the development questions (31 questions)

| Variant | recall@5 | mrr | ndcg@10 | hit@5 | recall@10 |
|---|---|---|---|---|---|
| B1 BM25 plain | 0.24 (0.12 to 0.39) | 0.25 (0.13 to 0.40) | 0.22 (0.11 to 0.35) | 0.35 (0.19 to 0.52) | 0.30 (0.17 to 0.45) |
| B2 embedding alone | 0.53 (0.37 to 0.69) | 0.46 (0.31 to 0.62) | 0.48 (0.34 to 0.62) | 0.61 (0.45 to 0.77) | 0.63 (0.47 to 0.78) |
| R2.1 RRF equal weights | 0.43 (0.27 to 0.58) | 0.43 (0.28 to 0.58) | 0.45 (0.32 to 0.58) | 0.52 (0.32 to 0.68) | 0.61 (0.45 to 0.76) |

Better single retriever on recall@5: B2 embedding alone. Fused variants against it (paired bootstrap):

- R2.1 RRF equal weights: difference -0.105 (95 % interval -0.242 to +0.024); share of resamples in which it is not better 0.95
- R2.2 not run (R2.1 does not improve on the better single retriever in point estimate)

Recall@5 by question type (B1 BM25 plain, B2 embedding alone, R2.1 RRF equal weights; number of questions):

- as_of: 0.20, 0.40, 0.20 (n = 5)
- comparison: 0.22, 0.35, 0.20 (n = 5)
- cross_reference: 0.20, 0.40, 0.50 (n = 5)
- definition: 0.38, 0.44, 0.44 (n = 4)
- lookup: 0.12, 0.75, 0.62 (n = 8)
- spanish_law: 0.50, 0.75, 0.50 (n = 4)

Recall@5 by question language (B1 BM25 plain, B2 embedding alone, R2.1 RRF equal weights; number of questions):

- en: 0.18, 0.51, 0.44 (n = 17)
- es: 0.32, 0.55, 0.41 (n = 14)

## Reading R4.1 and R2 (15 October 2026)

**R4.1, BGE-M3 against BM25.** Against the pre-registered rule: BGE-M3 improves recall@5 from 0.24 to 0.53 and the lower end of the paired interval (+0.086) is above 0, so it is better than BM25 and becomes the retriever the later experiments are measured against. Against the stated expectations: "beats BM25 with the lower bound above 0" held; "most on lay-worded questions" held (questions that share few words with their gold text go from 0.22 to 0.59, lookups from 0.12 to 0.75); "below 0.9" held. Cross-language questions (a question in one language whose gold text is in the other) have not been separated yet. Zero chunks were cut at 1,024 tokens. It is still only one model: R4 adopts a model after every candidate has run, and about half of the required provisions are still missing from the top five (recall@10 is 0.63).

**R2, fusion with BM25.** Not adopted, and the stated expectation was wrong: merging BM25 into BGE-M3 lowers recall@5 from 0.53 to 0.43 (paired interval -0.242 to +0.024, so not detectably worse, but in no resample clearly better). The reason is the arithmetic of the method: reciprocal rank fusion gives both lists equal weight, and BM25's top results are mostly wrong (recall@5 0.24), so they push right answers down. By the pre-registered rule R2.2 (weighting the embedding list 2 to 1) is not run, because R2.1 does not improve on the better single retriever in point estimate. Fusion may pay off if the keyword side improves (for example after the query is rewritten, R6) or with a weaker embedding model; that is a hypothesis, not a result.


## Cross-language breakdown, run 2026-10-15 (commit 7fbd515; gold fingerprint 7d9a62f5)

### Cross-language breakdown of R1.1 and R4.1 (31 development questions)

recall@5 by group (R1.1 BM25, R4.1 BGE-M3; number of questions):

- cross-language (no text in the question's language): 0.00, 0.67 (n = 3)
- same-language text available: 0.27, 0.52 (n = 28)

hit@5 by group (R1.1 BM25, R4.1 BGE-M3; number of questions):

- cross-language (no text in the question's language): 0.00, 0.67 (n = 3)
- same-language text available: 0.39, 0.61 (n = 28)

Cross-language development questions: q042, q049, q074.
- R1.1 BM25 recall@5 on them: q042 0.00, q049 0.00, q074 0.00
- R4.1 BGE-M3 recall@5 on them: q042 1.00, q049 0.00, q074 1.00


## R8 and R10 with bge, run 2026-10-15 (commit 7fbd515; gold fingerprint 7d9a62f5)

### R8 and R10 with bge on the development questions (31 retrieval questions)

| Variant | recall@5 | mrr | ndcg@10 | hit@5 | recall@10 |
|---|---|---|---|---|---|
| R8.1 everything (baseline R1.1) | 0.53 (0.37 to 0.69) | 0.46 (0.31 to 0.62) | 0.48 (0.34 to 0.62) | 0.61 (0.45 to 0.77) | 0.63 (0.47 to 0.78) |
| R8.2 current text only | 0.52 (0.37 to 0.69) | 0.48 (0.33 to 0.64) | 0.49 (0.36 to 0.63) | 0.61 (0.45 to 0.77) | 0.63 (0.48 to 0.78) |
| R8.3 original for past dates, current otherwise | 0.52 (0.37 to 0.69) | 0.48 (0.33 to 0.64) | 0.49 (0.35 to 0.63) | 0.61 (0.45 to 0.77) | 0.63 (0.48 to 0.78) |
| R10.1 collapse copies of a piece | 0.52 (0.37 to 0.69) | 0.47 (0.32 to 0.62) | 0.49 (0.35 to 0.64) | 0.61 (0.45 to 0.77) | 0.63 (0.47 to 0.79) |
| R10.2 collapse to one chunk per unit | 0.51 (0.35 to 0.67) | 0.46 (0.31 to 0.61) | 0.48 (0.34 to 0.63) | 0.58 (0.42 to 0.74) | 0.61 (0.45 to 0.77) |

Each variant against R1.1 on recall@5 (paired bootstrap), and recall@5 on the 12 version-sensitive questions:

- R8.1 everything (baseline R1.1): difference +0.000 (95 % interval +0.000 to +0.000); version-sensitive recall@5 0.38 (baseline 0.38)
- R8.2 current text only: difference -0.008 (95 % interval -0.048 to +0.024); version-sensitive recall@5 0.33 (baseline 0.38)
- R8.3 original for past dates, current otherwise: difference -0.008 (95 % interval -0.048 to +0.024); version-sensitive recall@5 0.33 (baseline 0.38)
- R10.1 collapse copies of a piece: difference -0.008 (95 % interval -0.048 to +0.024); version-sensitive recall@5 0.33 (baseline 0.38)
- R10.2 collapse to one chunk per unit: difference -0.024 (95 % interval -0.081 to +0.016); version-sensitive recall@5 0.29 (baseline 0.38)

Gold provisions no chunk of the index can satisfy (of the development questions):

- all texts: 0 (none)
- current text only: 2 (q044, q048)
- original text only: 14 (q004, q009, q013, q020, q025, q026, q044, q047, q048, q072)


## Diagnostic: depth of the required provisions in BGE-M3's ranking, run 2026-10-15 (commit 7fbd515; gold fingerprint 7d9a62f5)

### How deep BGE-M3 ranks the required provisions (31 development questions, 54 primary provisions)

- within the top 5: 44% of provisions; all provisions of 45% of the questions
- within the top 10: 54% of provisions; all provisions of 55% of the questions
- within the top 20: 65% of provisions; all provisions of 65% of the questions
- within the top 30: 65% of provisions; all provisions of 65% of the questions
- within the top 50: 76% of provisions; all provisions of 74% of the questions
- within the top 100: 89% of provisions; all provisions of 87% of the questions
- median best rank 8, worst 813 of 3831 chunks

**Reading the diagnostic (exploration).** BGE-M3 has the required provision within its top 10 for 54 % of the 54 primary provisions, within the top 30 for 65 % and within the top 100 for 89 %; the median best rank is 8 and the worst is 813 of 3,831. A reranker that re-scores the top 30 can therefore lift at most 65 % of provisions into view, against 44 % in the top 5 today (about +21 points at best), and the 35 % that sit beyond rank 30 are out of its reach: they need a better first-stage search (a better model or a rewritten question). This is the ceiling for R5, not a prediction of what it will deliver.

**Reading R8 and R10 repeated with BGE-M3.** Nothing is adopted. Version policy and duplicate collapsing change recall@5 by -0.008 to -0.024 (every interval includes 0): the stated expectation that collapsing copies would gain a little was wrong, and the expectation that current-text-only would gain on undated questions was wrong in direction. With a better retriever the two questions are still not where the losses are: the answer is not found because the right article is not ranked high, not because copies crowd it out.

**Reading the cross-language breakdown.** Only three development questions are cross-language (q042, q049, q074). BM25 scores 0 on all three as expected, and BGE-M3 finds two of them (recall@5 1.00 on q042 and q074, 0.00 on q049). Too few for any claim beyond "keyword search cannot, and the embedding model can".



## R3 chunk size and context line with BGE-M3, run 2026-10-15 (commit 7fbd515; gold fingerprint 7d9a62f5)

### R3 (chunk size, context line) with BGE-M3 on the development questions (31 questions)

| Variant | recall@5 | mrr | ndcg@10 | hit@5 | recall@10 |
|---|---|---|---|---|---|
| R3.1 cap 400 (baseline R4.1) | 0.53 (0.37 to 0.69) | 0.46 (0.31 to 0.62) | 0.48 (0.34 to 0.62) | 0.61 (0.45 to 0.77) | 0.63 (0.47 to 0.78) |
| R3.2 cap 200 | 0.57 (0.41 to 0.73) | 0.49 (0.34 to 0.64) | 0.50 (0.36 to 0.63) | 0.65 (0.48 to 0.81) | 0.67 (0.52 to 0.81) |
| R3.3 cap 300 | 0.54 (0.38 to 0.70) | 0.46 (0.32 to 0.62) | 0.47 (0.34 to 0.61) | 0.61 (0.45 to 0.77) | 0.64 (0.48 to 0.79) |
| R3.4 cap 600 | 0.48 (0.31 to 0.64) | 0.43 (0.29 to 0.58) | 0.46 (0.33 to 0.59) | 0.55 (0.39 to 0.71) | 0.63 (0.48 to 0.78) |
| R3.5 cap 400, no context line | 0.37 (0.23 to 0.53) | 0.33 (0.19 to 0.48) | 0.32 (0.20 to 0.46) | 0.45 (0.29 to 0.65) | 0.44 (0.28 to 0.60) |

Each variant against R3.1 on recall@5 (paired bootstrap), with the size of its index:

- R3.1 cap 400 (baseline R4.1): difference +0.000 (95 % interval +0.000 to +0.000); 3,831 chunks, mean 218 words
- R3.2 cap 200: difference +0.040 (95 % interval -0.089 to +0.177); 6,278 chunks, mean 133 words
- R3.3 cap 300: difference +0.008 (95 % interval -0.065 to +0.097); 4,574 chunks, mean 182 words
- R3.4 cap 600: difference -0.056 (95 % interval -0.137 to +0.008); 3,195 chunks, mean 261 words
- R3.5 cap 400, no context line: difference -0.161 (95 % interval -0.315 to -0.016); 3,831 chunks, mean 218 words

**Reading R3 with BGE-M3.** Nothing is adopted for chunk size: no cap beats 400 detectably (cap 200 +0.040 with an interval of -0.089 to +0.177; cap 300 +0.008; cap 600 -0.056 with an interval of -0.137 to +0.008). Against the stated expectations: "recall@5 does not improve detectably with smaller chunks" held; "cap 600 is not better" held; "leaving the context line out lowers recall@5" held, and it is the first detectable effect in Phase 3: recall@5 falls from 0.53 to 0.37, a paired difference of -0.161 with an interval of -0.315 to -0.016 that excludes 0. The context line ("GDPR | Chapter II | Article 6: Lawfulness of processing") is the part of a chunk that tells the embedding model which law and which article it is reading, and a lay question matches that heading. With BM25 the same removal moved recall@5 by only -0.027 (not detectable), so the line matters much more to an embedding model. Cap 200 is the only size that looks slightly better and costs 64 % more chunks, so it is left as a candidate for the final configuration and is not adopted.


## R5 reranker, run 2026-10-15 (commit 2facbe9; gold fingerprint 7d9a62f5)

### R5 reranker (bge-reranker-v2-m3) over BGE-M3 on the development questions (31 retrieval questions)

| Variant | recall@5 | mrr | ndcg@10 | hit@5 | recall@10 |
|---|---|---|---|---|---|
| R4.1 BGE-M3 | 0.53 (0.37 to 0.69) | 0.46 (0.31 to 0.62) | 0.48 (0.34 to 0.62) | 0.61 (0.45 to 0.77) | 0.63 (0.47 to 0.78) |
| R5.1 rerank top 30 | 0.52 (0.36 to 0.68) | 0.46 (0.33 to 0.61) | 0.47 (0.36 to 0.59) | 0.65 (0.48 to 0.81) | 0.64 (0.49 to 0.79) |
| R5.2 rerank top 50 | 0.53 (0.37 to 0.68) | 0.43 (0.30 to 0.57) | 0.45 (0.34 to 0.57) | 0.68 (0.52 to 0.84) | 0.65 (0.51 to 0.79) |

R5.1 (top 30) against R4.1, recall@5: difference -0.011, 95 % interval -0.151 to +0.129; share of resamples in which the reranker is not better 0.58.
R5.2 (top 50) against R4.1, recall@5: difference -0.003, 95 % interval -0.142 to +0.137; share of resamples in which the reranker is not better 0.52.
R5.2 (top 50) against R5.1 (top 30), recall@5: difference +0.008, 95 % interval +0.000 to +0.024; share of resamples in which depth 50 is not better 0.36.

Latency per question on this machine (GTX 1060, half precision): first stage alone 0.12 s; with reranker over the top 30 3.83 s; over the top 50 5.91 s.
Scored pairs cut at 512 tokens: 436 of 1550 (the top 50 candidates of 31 questions).

Recall@5 by question type (R4.1 BGE-M3, R5.1 top 30; number of questions):

- as_of: 0.40, 0.47 (n = 5)
- comparison: 0.35, 0.42 (n = 5)
- cross_reference: 0.40, 0.40 (n = 5)
- definition: 0.44, 0.44 (n = 4)
- lookup: 0.75, 0.62 (n = 8)
- spanish_law: 0.75, 0.75 (n = 4)

Recall@5 by question language (R4.1 BGE-M3, R5.1 top 30; number of questions):

- en: 0.51, 0.53 (n = 17)
- es: 0.55, 0.51 (n = 14)

Recall@5 by shared words with its gold text (R4.1 BGE-M3, R5.1 top 30; number of questions):

- shares few words: 0.59, 0.54 (n = 19)
- shares many words: 0.44, 0.49 (n = 12)


## Diagnostic: why the reranker did not help, run 2026-10-15 (commit 2facbe9; gold fingerprint 7d9a62f5)

### Why R5.1 did not beat BGE-M3 (31 development questions; the primary provisions BGE-M3 ranks within its top 30: 35)

- all: 35 provisions; in the top 5 before 24, after 22 (moved in 5, moved out 7); median rank gain +0.0
- pair cut at 512 tokens: 8 provisions; in the top 5 before 4, after 4 (moved in 3, moved out 3); median rank gain +2.0
- pair not cut: 27 provisions; in the top 5 before 20, after 18 (moved in 2, moved out 4); median rank gain +0.0


## R6 question rewriting, run 2026-10-15 (commit 2facbe9; gold fingerprint 7d9a62f5)

### R6 question rewriting on the development questions (31 retrieval questions)

| Variant | recall@5 | mrr | ndcg@10 | hit@5 | recall@10 |
|---|---|---|---|---|---|
| R4.1 BGE-M3 | 0.53 (0.37 to 0.69) | 0.46 (0.31 to 0.62) | 0.48 (0.34 to 0.62) | 0.61 (0.45 to 0.77) | 0.63 (0.47 to 0.78) |
| R6.1 replace | 0.68 (0.54 to 0.81) | 0.65 (0.50 to 0.79) | 0.59 (0.47 to 0.71) | 0.81 (0.65 to 0.94) | 0.75 (0.61 to 0.88) |
| R6.2 append | 0.70 (0.56 to 0.84) | 0.59 (0.45 to 0.73) | 0.56 (0.44 to 0.68) | 0.81 (0.68 to 0.94) | 0.75 (0.61 to 0.88) |

R6.1 (replace) against R4.1, recall@5: difference +0.148, 95 % interval +0.030 to +0.282; share of resamples in which the rewrite is not better 0.01.
R6.2 (append) against R4.1, recall@5: difference +0.169, 95 % interval +0.040 to +0.315; share of resamples in which the rewrite is not better 0.00.

Rewrite length in words: mean 30.1, longest 43; 2 of 31 exceed the 40 the agent was asked to stay under.

Recall@5 by question type (R4.1, R6.1 replace, R6.2 append; number of questions):

- as_of: 0.40, 0.47, 0.60 (n = 5)
- comparison: 0.35, 0.40, 0.40 (n = 5)
- cross_reference: 0.40, 0.50, 0.50 (n = 5)
- definition: 0.44, 0.69, 0.69 (n = 4)
- lookup: 0.75, 1.00, 1.00 (n = 8)
- spanish_law: 0.75, 0.88, 0.88 (n = 4)

Recall@5 by question language (R4.1, R6.1 replace, R6.2 append; number of questions):

- en: 0.51, 0.74, 0.79 (n = 17)
- es: 0.55, 0.61, 0.59 (n = 14)

Recall@5 by shared words with its gold text (R4.1, R6.1 replace, R6.2 append; number of questions):

- shares few words: 0.59, 0.68, 0.74 (n = 19)
- shares many words: 0.44, 0.67, 0.65 (n = 12)

## Reading R5, the reranker diagnostic and R6 (15 October 2026)

**R5, the reranker: nothing is adopted, and the stated expectation failed.** I expected the reranker to raise recall@5 above 0.53 with a lower paired bound above 0 (staying below the ceiling of about 0.65). It did not move: reranking BGE-M3's top 30 gave recall@5 0.52 (paired difference -0.011, interval -0.151 to +0.129) and the top 50 gave 0.53 (-0.003, interval -0.142 to +0.137). Depth 50 against depth 30 is +0.008 (interval +0.000 to +0.024), which is practically nothing. Per-question speed on this machine: 0.12 s for BGE-M3 alone, 3.83 s with the reranker over the top 30, 5.91 s over the top 50, about 32 and 49 times slower, for no detectable gain. One pattern is worth recording and not worth building on: hit@5 (is at least one required provision in the top 5) went 0.61, 0.65, 0.68, while MRR went 0.46, 0.46, 0.43. The reranker sometimes brings in a first right answer but pushes others out; none of these differences is detectable with 31 questions.

**Why: the diagnostic ruled out one explanation.** 436 of the 1,550 scored pairs (28 %) were longer than the reranker's 512-token limit, so the end of a long chunk was cut. If that were the cause, cut pairs would do worse. They did not: among the 35 primary provisions that BGE-M3 ranks within its top 30, the 8 whose pair was cut stayed at 4 in the top 5 (moved in 3, out 3), and the 27 uncut ones went from 20 to 18 (in 2, out 4). Overall 24 before, 22 after (moved in 5, out 7). So the reranker is not failing because of the cut; it simply re-orders about as well as BGE-M3 already does on these questions. I have not tested why (for example, preferring other relevant-looking articles to the ones the gold set requires); that stays an open question and no longer-limit variant was run.

**R6, rewriting the question: the first clearly detectable gain from a retrieval change.** Thirty-one rewrites were written beforehand by a separate agent that saw only the question texts (no gold set, no corpus, no tools; the prompt is in `eval/rewrites/README.md`), then searched with BGE-M3 unchanged.

- R6.1 (rewrite alone): recall@5 0.68 (0.54 to 0.81), paired difference +0.148, interval +0.030 to +0.282.
- R6.2 (question followed by the rewrite): recall@5 0.70 (0.56 to 0.84), paired difference +0.169, interval +0.040 to +0.315.
- hit@5 rose from 0.61 to 0.81 for both; MRR from 0.46 to 0.65 (replace) and 0.59 (append).

Against the stated expectations: "raises recall@5 above 0.53" held, and the lower bound did not include 0 (I had said it might). "Most for lay-worded questions that share few words with their gold text" did **not** hold: those went 0.59 to 0.68 (replace) and 0.74 (append), while the questions that already share many words went 0.44 to 0.67 and 0.65, a bigger jump. "R6.2 sits between R4.1 and R6.1" did not hold either: on recall@5 it is slightly above R6.1, on MRR below. "Rewrites could hurt date- and version-dependent questions" did not show: as_of went 0.40 to 0.47 (replace) and 0.60 (append). By language: English 0.51 to 0.74 and 0.79; Spanish 0.55 to 0.61 and 0.59, a much smaller gain. By type: lookup 0.75 to 1.00, definition 0.44 to 0.69, comparison 0.35 to 0.40 (unchanged within noise).

**Decision rule applied.** Both variants have a lower bound above 0, so both qualify; the rule keeps the higher recall@5, which is R6.2 (0.70 against 0.68). The two intervals overlap almost completely, so the data do not show that append beats replace; replace has the better MRR. R6.2 is carried forward as the working configuration.

**What this does and does not show.** It shows an automatic rewriter of this kind (a strong language model that sees only the question) can lift the first search from 0.53 to about 0.70 on the development questions. It does not show it on the test half (rewrites for the test questions have not been made; they will be made by the same prompt, once, when the pipeline is confirmed). It costs one language-model call per question in the final assistant, whose latency and price are not measured here. The rewriting model knows a lot of law, so the gain is partly that model's knowledge; that is the point of the step but it means the result depends on the model chosen. Two rewrites ran over the 40-word limit it was given (longest 43 words); they were not edited. Thirty-one questions is a small sample.


## R6.3/R6.4 question rewriting with Gemini, run 2026-10-15 (commit 3f9c7a2; gold fingerprint 7d9a62f5)

### R6.3/R6.4 question rewriting with gemini-3.1-flash-lite on the development questions (31 retrieval questions)

| Variant | recall@5 | mrr | ndcg@10 | hit@5 | recall@10 |
|---|---|---|---|---|---|
| R4.1 BGE-M3 | 0.53 (0.37 to 0.69) | 0.46 (0.31 to 0.62) | 0.48 (0.34 to 0.62) | 0.61 (0.45 to 0.77) | 0.63 (0.47 to 0.78) |
| R6.2 agent rewrite, append | 0.70 (0.56 to 0.84) | 0.59 (0.45 to 0.73) | 0.56 (0.44 to 0.68) | 0.81 (0.68 to 0.94) | 0.75 (0.61 to 0.88) |
| R6.3 Gemini rewrite, append | 0.56 (0.40 to 0.73) | 0.55 (0.39 to 0.70) | 0.50 (0.38 to 0.63) | 0.65 (0.48 to 0.81) | 0.70 (0.55 to 0.85) |
| R6.4 Gemini rewrite, replace | 0.56 (0.40 to 0.71) | 0.55 (0.40 to 0.70) | 0.50 (0.37 to 0.63) | 0.68 (0.52 to 0.84) | 0.66 (0.51 to 0.81) |

R6.3 (append) against R4.1, recall@5: difference +0.032, 95 % interval -0.145 to +0.210; share of resamples in which the rewrite is not better 0.40.
R6.4 (replace) against R4.1, recall@5: difference +0.024, 95 % interval -0.145 to +0.194; share of resamples in which the rewrite is not better 0.41.
For information, R6.3 against the agent's R6.2, recall@5: difference -0.137, 95 % interval -0.266 to -0.024.

Cost of the rewrite step (31 model calls this run; cached answers are not counted): 2.25 s per call on average, median 1.76 s, slowest 15.25 s; 10589 prompt tokens and 988 output tokens in total (342 and 32 per question).
Rewrite length in words: mean 27.8, longest 39; 0 of 31 exceed 40.

Recall@5 by question language (R4.1, R6.2 agent, R6.3 Gemini append; number of questions):

- en: 0.51, 0.79, 0.54 (n = 17)
- es: 0.55, 0.59, 0.59 (n = 14)

Recall@5 by question type (R4.1, R6.2 agent, R6.3 Gemini append; number of questions):

- as_of: 0.40, 0.60, 0.40 (n = 5)
- comparison: 0.35, 0.40, 0.45 (n = 5)
- cross_reference: 0.40, 0.50, 0.50 (n = 5)
- definition: 0.44, 0.69, 0.44 (n = 4)
- lookup: 0.75, 1.00, 1.00 (n = 8)
- spanish_law: 0.75, 0.88, 0.25 (n = 4)


## R6.5 to R6.7 other rewriters, run 2026-10-15 (commit 3f9c7a2; gold fingerprint 7d9a62f5)

### R6.5 to R6.7 other rewriters on the development questions (31 retrieval questions)

| Variant | recall@5 | mrr | ndcg@10 | hit@5 | recall@10 |
|---|---|---|---|---|---|
| R4.1 BGE-M3 | 0.53 (0.37 to 0.69) | 0.46 (0.31 to 0.62) | 0.48 (0.34 to 0.62) | 0.61 (0.45 to 0.77) | 0.63 (0.47 to 0.78) |
| R6.5 gemini-3.5-flash-lite, plain | 0.60 (0.44 to 0.75) | 0.57 (0.43 to 0.72) | 0.53 (0.41 to 0.65) | 0.71 (0.55 to 0.87) | 0.70 (0.56 to 0.84) |
| R6.6 gemini-3.1-flash-lite, expanding | 0.64 (0.48 to 0.79) | 0.56 (0.42 to 0.71) | 0.52 (0.39 to 0.64) | 0.71 (0.55 to 0.87) | 0.69 (0.55 to 0.83) |
| R6.7 gemini-3.5-flash-lite, expanding | 0.63 (0.48 to 0.77) | 0.57 (0.42 to 0.71) | 0.54 (0.43 to 0.66) | 0.74 (0.58 to 0.90) | 0.77 (0.64 to 0.88) |

R6.5 (gemini-3.5-flash-lite, plain) against R4.1, recall@5: difference +0.065, 95 % interval -0.065 to +0.202; share of resamples in which the rewrite is not better 0.18.
R6.6 (gemini-3.1-flash-lite, expanding) against R4.1, recall@5: difference +0.105, 95 % interval -0.032 to +0.258; share of resamples in which the rewrite is not better 0.07.
R6.7 (gemini-3.5-flash-lite, expanding) against R4.1, recall@5: difference +0.097, 95 % interval -0.040 to +0.242; share of resamples in which the rewrite is not better 0.10.

Cost of R6.5: 8.51 s per call, 342 prompt and 21 output tokens per question (31 calls); rewrite length mean 17.2 words, longest 37.
Cost of R6.6: 3.80 s per call, 385 prompt and 67 output tokens per question (31 calls); rewrite length mean 49.1 words, longest 82.
Cost of R6.7: 5.25 s per call, 385 prompt and 43 output tokens per question (31 calls); rewrite length mean 32.0 words, longest 59.

Recall@5 by question language (R4.1, then R6.5, R6.6, R6.7; number of questions):

- en: 0.51, 0.63, 0.71, 0.75 (n = 17)
- es: 0.55, 0.55, 0.55, 0.48 (n = 14)

## Reading R6.3 to R6.7, the rewriters that can run inside the pipeline (15 October 2026)

**No Gemini rewriter qualifies, and the stated expectation failed.** I expected the cheap in-pipeline rewriter to land between 0.53 and 0.70 with a lower paired bound above 0. The point estimates are all above the baseline but none is detectable with 31 questions:

| Rewriter (question followed by the rewrite) | recall@5 | paired difference against R4.1 | interval |
|---|---|---|---|
| R4.1 BGE-M3 alone | 0.53 | none | none |
| R6.3 gemini-3.1-flash-lite, plain prompt | 0.56 | +0.032 | -0.145 to +0.210 |
| R6.5 gemini-3.5-flash-lite, plain prompt | 0.60 | +0.065 | -0.065 to +0.202 |
| R6.6 gemini-3.1-flash-lite, expanding prompt | 0.64 | +0.105 | -0.032 to +0.258 |
| R6.7 gemini-3.5-flash-lite, expanding prompt | 0.63 | +0.097 | -0.040 to +0.242 |
| R6.2 the blind agent's rewrites | 0.70 | +0.169 | +0.040 to +0.315 |

R6.4 (the Gemini rewrite alone, gemini-3.1-flash-lite) was 0.56 (+0.024, -0.145 to +0.194). The agent's rewrites beat R6.3 by 0.137 (interval 0.024 to 0.266 in the agent's favour). The "expanding" prompt, which asks the model to add the specific legal terms the provision would contain, was designed after seeing R6.3's development results, so it is a tuned variant: its +0.07 over the plain prompt is suggestive, not shown. Together they lean the same way (a rewrite helps and a richer one helps more), but my rule does not let me add up non-significant results.

**Decision rule applied.** No variant has a lower bound above 0, so the in-pipeline rewrite step is **not adopted**; the agent's 0.70 is reported as an upper bound with a stronger writer, not as the system's score. Per the pre-registration there is no further prompt or model tuning on the development half.

**What stopped a fair test of a stronger model.** `gemini-3.5-flash` (the larger Flash model) allows 20 requests a day on the free tier; 22 of the 62 calls I needed went through, then the quota was used up (the reply said to retry in 9 hours 28 minutes). `gemini-2.5-flash` is closed to new accounts. Those two variants were dropped before anything was scored and replaced by the two generations of Flash-Lite; a larger model needs billing on the key. The same message exposed a flaw in my client: it obeyed the 9-hour retry delay by sleeping, so the run looked frozen for 11 minutes. Both Gemini clients now stop at once when the wait exceeds five minutes. The earlier "stall" of the embedding run (640 of 3,304 vectors) may well have been the same thing; I never read its reply text closely enough to confirm.

**Cost of the rewrite step (per question, from the calls this run).** About 342 to 385 prompt tokens and 21 to 67 output tokens. Time per call varied from 2.25 s (median 1.76 s, slowest 15 s) for gemini-3.1-flash-lite to 8.5 s for gemini-3.5-flash-lite in this run; the free tier is not a measure of paid-tier speed. No price is stated because none was verified.


## P4.1 reading the question, dev half, run 2026-10-15 (commit 3f9c7a2; gold fingerprint 7d9a62f5)

### P4.1 reading the question: language, jurisdictions, date (dev half, 40 questions)

- language: 40/40 correct
- jurisdictions: exactly the gold set 35/40; every gold jurisdiction found 36/40; something extra named 1/40
- as-of: 1/1 of the questions with a stated date read correctly; 0 questions got a date the gold does not have

Misses (id, what was detected, gold):

- q019: jurisdictions [] (gold ['EU'])
- q026: jurisdictions [] (gold ['EU'])
- q062: jurisdictions ['ES'] (gold [])
- q073: jurisdictions ['EU', 'UK'] (gold ['EU', 'UK', 'ES'])
- q080: jurisdictions ['ES'] (gold ['ES', 'EU'])


## P4.2 routing and table lookup, dev half, run 2026-10-15 (commit 3f9c7a2; gold fingerprint 7d9a62f5)

### P4.2 routing on the development questions (40: 31 retrieve, 4 table, 5 refuse)

**rules router.** Accuracy 0.975 (39/40).
Refusals sent to refuse 5/5 (right reason 5/5); false refusals 0; table questions sent to table 4/4; table false alarms 1.

**llm router.** Accuracy 1.000 (40/40).
Refusals sent to refuse 5/5 (right reason 5/5); false refusals 0; table questions sent to table 4/4; table false alarms 0.

Disagreements with the gold route (id, gold, rules, model, text):

- q023: gold retrieve, rules table, model retrieve: En la UE, ¿cómo puedo obtener una copia de los datos que una empresa tiene sobre mí y en cuánto tiempo debe dármela?

Table lookup (top fact, its score, whether it is the gold row):

- q052: gdpr-fine-upper-tier (0.68), gold gdpr-fine-upper-tier: right
- q054: gdpr-breach-notification-deadline (0.70), gold gdpr-breach-notification-deadline: right
- q055: gdpr-breach-notification-deadline (0.64), gold gdpr-response-deadline: WRONG
- q057: gdpr-child-consent-age (0.74), gold gdpr-child-consent-age: right

Lowest score of a correct match 0.68, so the threshold is 0.65. Of the 37 other development questions, 3 would still get a fact at that threshold (highest 0.73); the router sends only figure questions here, so this is the share that would be wrongly answered if routed to the table.


## P4.3 model-picked table row, dev half, run 2026-10-15 (commit 3f9c7a2; gold fingerprint 7d9a62f5)

### P4.3 the model picks the table row (40 development questions)

- table questions right: 4/4; wrong row: 0
- false picks on the 36 other questions: 3

Misses:

- q009 (retrieve): picked ai-act-fine-prohibited-practices for a question that is not a figure question
- q023 (retrieve): picked gdpr-response-deadline for a question that is not a figure question
- q044 (retrieve): picked ai-act-high-risk-application-dates for a question that is not a figure question


## P4.4 answer layer, dev half, run 2026-10-15 (commit 3f9c7a2; gold fingerprint 7d9a62f5)

### P4.4 the answer layer on the development questions (40 questions)

**Variant A (k = 5).**
- retrieve questions (31): answered 25, abstained 6, refused 0, from the table 0; correctness 0.68 (0.53 to 0.82)
- among the 25 answered: support 0.86; a cited source satisfies a primary gold provision 0.64; coverage of the primary provisions 0.55; strict precision 0.64
- table questions answered from the right row: 4/4; refusals refused with the right reason: 5/5; retrieve questions refused 0
- model time per question (excluding search and judging calls made outside the pipeline is not separable here): mean 1.74 s, median 1.85 s, slowest 3.31 s; tokens per question 1706 in, 244 out (includes the judge calls for this question)

**Variant B (k = 8).**
- retrieve questions (31): answered 26, abstained 5, refused 0, from the table 0; correctness 0.69 (0.55 to 0.82)
- among the 26 answered: support 0.88; a cited source satisfies a primary gold provision 0.77; coverage of the primary provisions 0.62; strict precision 0.68
- table questions answered from the right row: 4/4; refusals refused with the right reason: 5/5; retrieve questions refused 0
- model time per question (excluding search and judging calls made outside the pipeline is not separable here): mean 1.76 s, median 1.92 s, slowest 5.26 s; tokens per question 2536 in, 241 out (includes the judge calls for this question)

**Variant C (k = 5 with the blind agent's rewrites (upper bound)).**
- retrieve questions (31): answered 27, abstained 4, refused 0, from the table 0; correctness 0.79 (0.65 to 0.92)
- among the 27 answered: support 0.80; a cited source satisfies a primary gold provision 0.74; coverage of the primary provisions 0.60; strict precision 0.72
- model time per question (excluding search and judging calls made outside the pipeline is not separable here): mean 2.61 s, median 2.25 s, slowest 7.66 s; tokens per question 2055 in, 338 out (includes the judge calls for this question)

**Baseline N (no retrieval).** correctness 0.63 (0.50 to 0.76); no quotations to check.

B against A, correctness: difference +0.016, 95 % interval -0.065 to +0.113
A against N, correctness: difference +0.048, 95 % interval -0.097 to +0.177
C against A, correctness: difference +0.113, 95 % interval -0.016 to +0.258

The corpus is 3,831 chunks and about 833,327 words (roughly 1,249,990 tokens), so it does not fit in a prompt of one million tokens once Spanish, the original texts and the markup are counted; that baseline is not run.

Questions answered wrongly or not at all in variant A (id, route outcome, correctness):

- q004 (retrieve): abstained, no: no answer given
- q013 (retrieve): answer, partly: The answer focuses exclusively on human oversight and omits several other key obligations for deployers under the AI Act, such as data input requirements, logging, incident reporting, and fundamental rights impact assessments.
- q014 (retrieve): abstained, no: no answer given
- q023 (retrieve): abstained, no: no answer given
- q028 (retrieve): abstained, no: no answer given
- q030 (retrieve): answer, partly: The answer incorrectly claims that the balancing test applies to the UK's 'recognised legitimate interests' (Article 6(1)(ea)), whereas the reference answer correctly notes that the balancing test is not required once an Annex 1 condition is met.
- q042 (retrieve): answer, partly: The answer correctly identifies the right to erasure for data provided by the user and minors, but it fails to mention the right to erasure for data provided by third parties as outlined in Article 94(2) of the LOPDGDD.
- q043 (retrieve): abstained, no: no answer given
- q047 (retrieve): answer, partly: The answer correctly identifies the AI Office as the supervisor but fails to mention the specific exceptions regarding high-risk systems (Annex I/III) and the comprehensive enforcement powers (fines, binding commitments) detailed in the reference.
- q048 (retrieve): answer, no: The answer incorrectly claims the original text used 'or' and that the wording has not changed, failing to identify the 'and' to 'or' correction that occurred in the corrigendum.
- q049 (retrieve): abstained, no: no answer given
- q051 (retrieve): answer, partly: The answer correctly identifies the criteria for a 'malicious person' and the conditions for erasure, but it fails to mention the start date of 31 March 2026 as requested by the question.
- q058 (refuse): refused, no: no answer given
- q062 (refuse): refused, no: no answer given
- q063 (refuse): refused, no: no answer given
- q065 (refuse): refused, no: no answer given
- q073 (retrieve): answer, partly: The answer correctly explains the UK procedure but fails to provide the requested comparison with the EU, incorrectly stating that the provided texts do not contain enough information to do so.
- q080 (refuse): refused, no: no answer given

## Reading P4.1 to P4.4, the answer layer on the development questions (15 October 2026)

All numbers are for the 40 development questions (31 retrieve, 4 table, 5 refuse). The rules and prompts were written after I had seen the shape of the development labels, so these numbers are optimistic; the test half has not been read and is read once, at the end.

**P4.1 reading the question (rules).** Language 40 of 40. Jurisdictions exactly equal to the gold set on 35 of 40 (every gold jurisdiction found on 36); misses: q019 and q026 name no place or law in their text (gold: EU), q062 mentions the Spanish regulator in a question the gold treats as outside the corpus, q073 and q080 where the gold adds a second jurisdiction the words do not name. One stated date read correctly (q044, "the start of 2026"). The expectation of about 0.75 on jurisdictions was too low; 0.875 was reached, but with rules written knowing the development labels.

**P4.2 routing.** The model router (gemini-3.1-flash-lite applying written definitions and no examples from the gold set) got 40 of 40; the rule router 39 of 40 (it sent q023, "how do I get a copy of my data and within what time", to the table; the gold says retrieve). Neither made a false refusal; both sent 5 of 5 refusals to refuse with the right reason and 4 of 4 figure questions to the table. The expectation that the rules would reach only about 0.85 was wrong (0.975). The lesson I draw is cautious: the development half has only 5 refusals and 4 table questions, so this does not show the rules would survive new wording. The model router is used by the pipeline; the rule router stays as the free baseline.

**P4.2 table lookup by embeddings.** The nearest fact by cosine similarity was right for 3 of 4 table questions; for q055 (the deadline to answer a rights request) it chose the breach-notification deadline (score 0.64 against 0.68 to 0.74 for the correct ones).

**P4.3 a model picks the row.** gemini-3.1-flash-lite given the 19 keys and subjects picked the right row for 4 of 4 table questions, and picked a row for 3 of the 36 other questions (q009, q023, q044). My pre-registered rule was 4 of 4 with at most 1 false pick, so **the rule was not met**. The picker is only called after the router has chosen the table, and in the end-to-end run (P4.4) no retrieve question was answered from the table, so I use it behind the router and record the miss here.

**P4.4 the whole layer.**

| | A: 5 passages | B: 8 passages | C: 5 + blind-agent rewrites (upper bound) | N: no retrieval |
|---|---|---|---|---|
| retrieve questions answered / abstained | 25 / 6 | 26 / 5 | 27 / 4 | not applicable |
| correctness by model judge (95 % interval) | 0.68 (0.53 to 0.82) | 0.69 (0.55 to 0.82) | 0.79 (0.65 to 0.92) | 0.63 (0.50 to 0.76) |
| claims supported by the cited quotations (answered) | 0.86 | 0.88 | 0.80 | no quotations |
| a cited source satisfies a primary gold provision (answered) | 0.64 | 0.77 | 0.74 | none |
| coverage of the primary gold provisions | 0.55 | 0.62 | 0.60 | none |

Table questions answered from the right row 4 of 4; refusals refused with the right reason 5 of 5; retrieve questions refused 0 (all three variants).
Paired differences in correctness: B against A +0.016 (-0.065 to +0.113); A against N +0.048 (-0.097 to +0.177); C against A +0.113 (-0.016 to +0.258). **None is detectable.** By question type (A, C, N): as_of 0.40, 0.40, 0.20; comparison 0.60, 0.60, 0.50; cross_reference 0.80, 0.90, 0.70; definition 0.75, 1.00, 0.88; lookup 0.81, 0.94, 0.81; spanish_law 0.62, 0.88, 0.62. By language: English 0.65, 0.79, 0.59; Spanish 0.71, 0.79, 0.68.

Against the stated expectations: correctness 0.45 to 0.60 for A was too low (0.68, helped by a generous judge, below); 20 to 30 percent abstentions held roughly (6 of 31); support of at least 0.9 did **not** hold (0.86; the code guarantees every quotation exists, not that every claim follows from it); refusals and table 5/5 and 4/4 held; "N scores below A" held on the point estimate but is not detectable; "B not detectably better than A" held; "C higher than A" held on the point estimate, not detectably.

**Decision rule applied.** B does not replace A (the interval of its gain includes 0), so five passages stay. The system is **not shown to be more correct than the same model answering from memory** (+0.048, interval -0.097 to +0.177). That is the honest result. What retrieval adds in this design is not measured by that number: every quotation in an answer is checked in code to exist in a retrieved passage, answers name the law, provision and text version, out-of-corpus and advice questions are refused, and an answer with no valid quotation becomes an abstention. The memory baseline offers none of these, and it can be wrong about texts newer than its training (the 2025 UK Act, the 2026 amendment), which is where retrieval scored highest relative to memory (as_of 0.40 against 0.20, 5 questions).

**A person read the judge's work.** I read the answers and verdicts of 12 questions (q006, q009, q016, q019, q020, q025, q026, q032, q044, q048, q052, q066) as an AI assistant, not as a lawyer. I agreed with the judge on 10. On two it was too generous: q044 (asked as of the start of 2026, the answer gave the dates from the July 2026 amending regulation and the judge passed it) and q032 (the answer covers the UK's new definitions but not the separate research chapter the reference describes, judged "yes" where I would say "partly"). So the correctness figures are probably a little high for every variant, including the baseline.

**Two failures found by reading; a fix written, not yet measured.** q044 shows the search offered the 2026 amending regulation to a question about the start of 2026; q048 (asked about the wording "as first published") was searched in the current text only, which hides the original wording, and was answered wrongly (the judge was right to fail it). Variant D (experiment p4_version_aware.py, pre-registered) searches the text as first published without the amending regulation for questions dated before 27 July 2026, and every version for questions about the original wording. **It has not been run**: the free tier of gemini-3.1-flash-lite allows 500 requests a day and today's allowance was used up (the client stopped at once and reported that the quota resets in about eight and a half hours). D is a tuned variant, designed from these two development failures.

**What the free tier cost.** The experiments of 15 October used well over 500 requests of one model. Each full evaluation of the answer layer is about 250 model calls (answers, two judge verdicts each, a baseline), so the one confirmation on the test half needs a day's allowance on its own. A paid key would lift this; until then the confirmation has to be scheduled.


## R6 filters, run 2026-10-15 (commit ec0c219; gold fingerprint 7d9a62f5)

### R6 filters on the development questions (31 retrieval questions)

| Variant | recall@5 | mrr | ndcg@10 | hit@5 | recall@10 |
|---|---|---|---|---|---|
| R4.1 BGE-M3 | 0.53 (0.37 to 0.69) | 0.46 (0.31 to 0.62) | 0.48 (0.34 to 0.62) | 0.61 (0.45 to 0.77) | 0.63 (0.47 to 0.78) |
| F1 gold jurisdictions (upper bound) | 0.53 (0.37 to 0.69) | 0.49 (0.34 to 0.64) | 0.50 (0.37 to 0.64) | 0.61 (0.45 to 0.77) | 0.67 (0.51 to 0.82) |
| F2 jurisdictions from the text | 0.53 (0.37 to 0.69) | 0.49 (0.34 to 0.64) | 0.50 (0.37 to 0.64) | 0.61 (0.45 to 0.77) | 0.67 (0.51 to 0.82) |
| F3 language | 0.53 (0.37 to 0.69) | 0.40 (0.27 to 0.55) | 0.44 (0.32 to 0.58) | 0.61 (0.45 to 0.77) | 0.62 (0.46 to 0.77) |
| F4 jurisdictions and language | 0.56 (0.40 to 0.73) | 0.46 (0.32 to 0.61) | 0.48 (0.35 to 0.61) | 0.65 (0.48 to 0.81) | 0.65 (0.49 to 0.81) |

F1 gold jurisdictions (upper bound) against R4.1, recall@5: difference +0.000, 95 % interval +0.000 to +0.000; top-5 changed for 9 of 31 questions.
F2 jurisdictions from the text against R4.1, recall@5: difference +0.000, 95 % interval +0.000 to +0.000; top-5 changed for 9 of 31 questions.
F3 language against R4.1, recall@5: difference +0.000, 95 % interval +0.000 to +0.000; top-5 changed for 13 of 31 questions.
F4 jurisdictions and language against R4.1, recall@5: difference +0.032, 95 % interval +0.000 to +0.097; top-5 changed for 17 of 31 questions.

Recall@5 by question language (R4.1, F1, F2, F3, F4; number of questions):

- en: 0.51, 0.51, 0.51, 0.51, 0.57 (n = 17)
- es: 0.55, 0.55, 0.55, 0.55, 0.55 (n = 14)

Recall@5 by jurisdiction group (R4.1, F1, F2, F3, F4; number of questions):

- ES: 0.75, 0.75, 0.75, 0.75, 0.75 (n = 4)
- EU: 0.54, 0.54, 0.54, 0.54, 0.59 (n = 20)
- EU+UK: 0.31, 0.31, 0.31, 0.31, 0.31 (n = 4)
- EU+UK+ES: 0.50, 0.50, 0.50, 0.50, 0.50 (n = 1)
- UK: 0.50, 0.50, 0.50, 0.50, 0.50 (n = 2)

## Reading R6 filters (15 October 2026)

**No filter is adopted.** The filters cost nothing (no model calls) and are easy to explain, so they were worth testing, but on the 31 development questions none has a lower paired bound above 0 on recall@5.

| Filter | recall@5 | paired difference | interval | MRR | recall@10 | questions whose top 5 changed |
|---|---|---|---|---|---|---|
| none (R4.1) | 0.53 | none | none | 0.46 | 0.63 | none |
| F1 gold jurisdictions (upper bound) | 0.53 | +0.000 | +0.000 to +0.000 | 0.49 | 0.67 | 9 |
| F2 jurisdictions read from the text | 0.53 | +0.000 | +0.000 to +0.000 | 0.49 | 0.67 | 9 |
| F3 language | 0.53 | +0.000 | +0.000 to +0.000 | 0.40 | 0.62 | 13 |
| F4 both | 0.56 | +0.032 | +0.000 to +0.097 | 0.46 | 0.65 | 17 |

**What it says.** The filter that uses the gold labels (an upper bound for any jurisdiction filter) did no better in recall@5 than the one that reads the question, and neither moved it at all: the filters change the top five for 9 of 31 questions but not how many required provisions are in it. So the required provisions are not being crowded out by text from the wrong jurisdiction; what is missing is ranked below the right jurisdiction's own text. The language filter alone lowered MRR (0.46 to 0.40), perhaps because the other-language copy of a provision was sometimes the better-ranked one. F4's +0.032 has an interval that starts at exactly 0.000, so it is not shown. This matches the pattern since BGE-M3 arrived: tidying what the search is allowed to return changes little; the gains came from the question's wording (R6 rewriting) and from the context line in each chunk.

The stated expectations: "F1 raises recall@5 by a few points" did not hold (0.000); "F2 gets part of it" is moot; "F3 changes little" held for recall@5 and not for MRR; "no filter has a lower paired bound above 0" held. A reminder that the jurisdiction groups are small (UK 2 questions, EU+UK 4).


## R7 vector search backends, run 2026-10-15 (commit b1e34db; gold fingerprint 7d9a62f5)

### R7 vector search backends (3,831 vectors of 1024 numbers)

**Part A: accuracy on the development questions** (overlap of the top 10 with the plain loop; identical order; recall@5; MRR)

| Backend | overlap@10 | identical order | recall@5 | MRR |
|---|---|---|---|---|
| python | 1.000 | 31/31 | 0.532 | 0.462 |
| numpy | 0.987 | 26/31 | 0.532 | 0.462 |
| faiss-flat | 0.987 | 7/31 | 0.532 | 0.462 |
| faiss-hnsw | 0.971 | 6/31 | 0.524 | 0.456 |
| sqlite-vec | 0.997 | 27/31 | 0.532 | 0.462 |

**Part B: speed on the real vectors** (milliseconds)

| Backend | build | search median | search 95th percentile |
|---|---|---|---|
| python | 49 | 113.03 | 117.09 |
| numpy | 117 | 0.68 | 0.99 |
| faiss-flat | 121 | 0.94 | 1.48 |
| faiss-hnsw | 664 | 0.21 | 0.39 |
| sqlite-vec | 295 | 7.29 | 8.59 |

**Part C: speed as the set grows** (synthetic random vectors; median milliseconds per search; build in seconds)

| Backend | 3,831 vectors | 38,310 vectors | 153,240 vectors |
|---|---|---|---|
| python | 118.58 (build 0.0 s) | 1235.61 (build 1.5 s) | not run |
| numpy | 0.68 (build 0.1 s) | 7.46 (build 1.4 s) | 30.26 (build 0.0 s) |
| faiss-flat | 1.02 (build 0.1 s) | 21.51 (build 1.3 s) | 77.53 (build 0.2 s) |
| faiss-hnsw | 0.81 (build 1.6 s) | 1.43 (build 18.7 s) | 1.78 (build 85.2 s) |
| sqlite-vec | 7.14 (build 0.3 s) | 63.59 (build 2.6 s) | not run |

Approximate index overlap@10 with the exact one on random vectors (information only): 3,831: 0.60, 38,310: 0.40, 153,240: 0.10

On disk, the sqlite-vec database for the real vectors is 17 MB; the raw float32 vectors are 16 MB.

## Reading R7, vector search backends (15 October 2026)

**Result.** Search results are the same whatever backend scans the vectors; what changes is speed. On the real 3,831 vectors: the plain Python loop 113 ms per search, NumPy 0.68 ms, FAISS exact 0.94 ms, FAISS approximate (HNSW) 0.21 ms, sqlite-vec 7.3 ms. recall@5 0.532 and MRR 0.462 for every exact backend; the approximate index gives 0.524 and 0.456 and overlaps the exact top 10 on 0.971.

**The pre-registered rule was not met to the letter, and why.** I required an identical top 10 from exact backends. NumPy and FAISS exact overlapped the loop on 0.987 of the top-10 places and had a different order on several questions. Every difference is a perfect tie: 3,831 chunks have only 3,300 distinct vectors (copies of one text, such as the same article in two versions), so equal scores can be listed in any order, and the loop breaks ties by chunk id where the libraries do not. After giving the NumPy scan the same tie rule, 30 of 31 development questions have an identical top-10 order and the other differs by a float32 rounding (a score gap of 8e-8); recall@5, MRR and nDCG@10 are identical to three decimals (0.532, 0.462, 0.478). I read the rule by its intent (same answers) and adopt NumPy; the rule's wording was too strict about ties.

**Scaling (synthetic vectors, ms per search).** 3,831 / 38,310 / 153,240 vectors: python 119 / 1,236 / not run; NumPy 0.7 / 7.5 / 30; FAISS exact 1.0 / 21.5 / 78; FAISS HNSW 0.8 / 1.4 / 1.8 (build 85 s at 153k); sqlite-vec 7 / 64 / not run. So a plain NumPy scan stays under a 100 ms budget up to about 500,000 vectors and under a second to about 5 million; the approximate index only pays off beyond that, and its build time and its loss of exactness are the price. The overlap figures for HNSW on random vectors (0.60, 0.40, 0.10) are not meaningful: random vectors have no neighbourhood structure for a graph index to use. FAISS exact was slower than NumPy's matrix product here (a single-query workload on a CPU).

**What each would buy beyond speed.** sqlite-vec keeps the vectors in a database file (17 MB against 16 MB raw), so it brings persistence and SQL filtering (for example jurisdiction or version as ordinary columns) at 10 times NumPy's search time, which at 7 ms is still negligible next to the 0.12 s needed to embed the question and the seconds the language model takes. FAISS buys nothing at this size.

**Decision 96.** The default scan in `DenseIndex` is NumPy when it is installed (else the plain loop), with ties broken by chunk id; no vector database or FAISS is adopted. At 3,831 chunks the answer to "does a vector store beat scanning?" is no: it changes nothing a user sees. The size at which it would start to matter is a few hundred thousand chunks, or the need to filter by metadata inside the store.


## Diagnostic: Spanish against English questions, run 2026-10-15 (commit b1e34db; gold fingerprint 8c91df9a)

### Why rewriting helped English more than Spanish (31 development retrieval questions)

Share of required (primary) provisions within the top 5 / 10 / 30, and median best rank:

- en, question: 28 provisions; top 5 43%, top 10 57%, top 30 64%; median best rank 7.5
- en, question+rewrite: 28 provisions; top 5 61%, top 10 68%, top 30 86%; median best rank 3.5
- es, question: 26 provisions; top 5 46%, top 10 50%, top 30 65%; median best rank 10.0
- es, question+rewrite: 26 provisions; top 5 50%, top 10 62%, top 30 77%; median best rank 5.5

Language of the top-5 chunks (share in the question's own language / in the other language):

- en, question: 85% / 15% over 17 questions
- en, question+rewrite: 88% / 12% over 17 questions
- es, question: 50% / 50% over 14 questions
- es, question+rewrite: 79% / 21% over 14 questions

Does the question need law that exists only in the other language? (primary gold provisions by instrument):

- en questions: 28 primary provisions; UK law (English only) 9 (32%); LOPDGDD (Spanish only) 2 (7%); EU law (both languages) 17
- es questions: 26 primary provisions; UK law (English only) 3 (12%); LOPDGDD (Spanish only) 3 (12%); EU law (both languages) 20

Rewrite length in words (mean) against question length:

- en: question 19.2, rewrite 29.1
- es: question 20.4, rewrite 31.4

Spanish questions with a required provision still outside the top 5 after rewriting (id, best ranks):

- q019: before [('eu-ai-act 3', 41)]; after [('eu-ai-act 3', 145)]
- q023: before [('eu-gdpr 15', 1), ('eu-gdpr 12', 82)]; after [('eu-gdpr 15', 1), ('eu-gdpr 12', 48)]
- q043: before [('es-lopdgdd 73', 53), ('es-lopdgdd 74', 90)]; after [('es-lopdgdd 73', 4), ('es-lopdgdd 74', 44)]
- q047: before [('eu-ai-act 75', 12), ('eu-ai-act 75a', 44), ('eu-ai-act 75c', 813)]; after [('eu-ai-act 75', 6), ('eu-ai-act 75a', 21), ('eu-ai-act 75c', 640)]
- q049: before [('uk-gdpr 6', 19)]; after [('uk-gdpr 6', 21)]
- q070: before [('eu-gdpr 4', 11), ('eu-gdpr 7', 3), ('eu-gdpr 43', 1), ('eu-gdpr 42', 2)]; after [('eu-gdpr 4', 6), ('eu-gdpr 7', 1), ('eu-gdpr 43', 4), ('eu-gdpr 42', 3)]
- q072: before [('eu-ai-act 70', 78), ('eu-ai-act 64', 450), ('eu-ai-act 75', 17), ('eu-ai-act 88', 50)]; after [('eu-ai-act 70', 45), ('eu-ai-act 64', 64), ('eu-ai-act 75', 17), ('eu-ai-act 88', 30)]
- q073: before [('uk-dpa-2018 164A', 5), ('eu-gdpr 77', 9)]; after [('uk-dpa-2018 164A', 3), ('eu-gdpr 77', 10)]

## Reading the Spanish diagnostic (15 October 2026)

**The stated expectation was wrong, and none of the three explanations holds up.** I expected the gap in how much rewriting helped (English 0.51 to 0.79, Spanish 0.55 to 0.59 in recall@5) to come from Spanish questions needing law that exists only in English, so that a Spanish rewrite cannot match it. The opposite is true: 32 % of the English questions' required provisions are UK law (English only) against 12 % of the Spanish questions'. The other two explanations fail too. (a) A ceiling: before rewriting, the two languages are alike (46 % of required Spanish provisions in the top 5 against 43 % of English ones; median best rank 10 against 7.5). (c) Weaker rewrites: they are equally longer than the questions (+9.9 words in English, +11.0 in Spanish).

What the numbers do show, on 26 and 28 required provisions: with the rewrite appended, the share in the top 5 goes 43 to 61 % in English and 46 to 50 % in Spanish; in the top 30, 64 to 86 % and 65 to 77 %; median best rank 7.5 to 3.5 and 10 to 5.5. Spanish improves everywhere, just less. With samples this small (14 Spanish questions) the difference between the gains is within the noise, so the honest reading is: **there may be no real language gap in the effect of rewriting**, and the 0.79 against 0.59 recall@5 contrast reflects a few questions. Of the 14 Spanish questions, the ones still missing after rewriting are mostly multi-provision AI Act questions (q019, q047, q072) whose required provisions rank at 45 to 640, plus q049 (the UK recognised-legitimate-interest question, rank 21).

**One real finding about language.** Before rewriting, only 50 % of the top-5 chunks for a Spanish question are in Spanish (85 % of English questions' top 5 are in English); the rest are English copies of the same laws. They count as hits (the gold does not insist on a language), but they use up places, and the answer writer then reads half its passages in the other language. The rewrite, which contains Spanish legal terms, moves that to 79 % Spanish. This is a design point for the answer layer, not a retrieval score: preferring the question's language among copies of a provision (the language filter F3 did that and did not help recall@5, but lowered MRR). It is recorded here and not acted on.

**q019 got worse with the rewrite** (best rank 41 to 145): the general-purpose AI model question, where the rewrite named the definition's own words and pulled other text higher. One example in 31, not a pattern.
