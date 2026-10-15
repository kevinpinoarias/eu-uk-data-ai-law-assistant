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
