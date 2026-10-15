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

