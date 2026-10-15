# Retrieval metrics

`law_assistant.evaluation.relevance` (when a chunk is a hit) and `law_assistant.evaluation.metrics` (the scores and the intervals). Used by every experiment in Phase 3.

## Generic idea

Retrieval returns a ranked list, so it is scored on the list: **hit@k** (was a correct result in the top k?), **recall@k** (what share of the correct items was in the top k?), **MRR** (one over the rank of the first correct result, averaged over questions) and **nDCG@k** (a graded score that rewards putting the most relevant items first, normalised so a perfect ranking scores 1). Because a test set is small, each average is reported with a **bootstrap interval** (resample the questions with replacement and see how much the average moves), and two systems are compared with a **paired bootstrap** on the same questions, which gives an interval for the *difference* that is much tighter than comparing two separate intervals.

## Applied here

- **A hit** (decisions 50 and 51): the chunk has the gold provision's instrument, unit kind and unit; if the gold pins a version or a language the chunk must have it; and if the gold lists pinpoint ids the chunk must contain at least one, so another part of the same article does not count. Without pinpoints any chunk of the unit counts.
- **Targets and grades.** Each gold provision of a question is a target: primary (grade 2, gain 3) or acceptable (grade 1, gain 1). hit, recall and MRR use the primary targets only; nDCG uses both.
- **Each target is credited once.** The index holds every text in several copies (English and Spanish, original and consolidated, several pieces of a long article). A target is credited at the first chunk that satisfies it; later copies add nothing and cost nothing. At most one target is credited per chunk, so one chunk per target in the best order scores nDCG 1.
- **Only retrieval questions are scored.** 62 of the 80 gold questions go to retrieval; the 8 numeric ones go to the facts table and the 10 refusals to the router, which have their own measures in Phase 4.
- **A run** is a file of ranked chunk ids per question (`write_run`, `read_run`); `score_run` scores it and refuses a run that lacks a retrieval question or names an unknown chunk.
- **The gold checks itself.** `unreachable_targets` lists any gold provision that no real chunk can satisfy; it is empty for the committed set, so no gold error can look like a retrieval failure. An oracle ranking scores 1 on every question, and an empty ranking scores 0.
- **Intervals.** `bootstrap_ci(values)` gives the mean and a 95 % percentile interval; `paired_bootstrap(a, b)` gives the mean difference, its interval and the share of resamples in which b is not better. Both take a seed and use no extra library.

## First numbers (15 October 2026)

- A **random ranking** of 10 chunks out of 3,831 scores a hit@10 of 1.3 %, the "no skill" floor.
- Each primary provision is satisfied by 1 to 16 chunks (median 4), because of the copies.
- **How precise can the answers be?** With 62 retrieval questions the full set gives a hit-rate interval of roughly plus or minus 10 points near 0.8; after the 40/40 split each half has about 31 retrieval questions, so a half gives about plus or minus 14. Differences between variants are therefore only detectable when they are large or when the paired comparison makes them tight; the write-up has to say "no detectable difference" when the interval includes 0.

## Decision rule for Phase 3

Judge each variant by the change in the metric against its baseline on the development half, with the paired interval; count the variants tried; touch the test half once per decision.
