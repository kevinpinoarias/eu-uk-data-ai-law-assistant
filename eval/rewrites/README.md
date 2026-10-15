# Question rewrites for experiment R6

`r6_dev.jsonl` holds one rewritten search query for each of the 31 development retrieval questions, written on
15 October 2026 by a separate language-model agent (Claude Sonnet) that was given **only the question texts**: no
gold set, no corpus, no tools and no files. Its prompt (the instructions below plus the 31 `id`, `language` and
`question` fields, copied from the gold file) was fixed before any rewrite was scored.

Instructions given to the agent:

- Rewrite each question as one search query worded the way the legal text itself would put it.
- Keep the same language as the question.
- Use the legal terms of art and name the instrument when the question points to one.
- Do **not** cite article, section or paragraph numbers.
- Keep every part of the question; at most 40 words; do not answer the question.
- Work from the question text alone: no tools, no files, no look-ups.

Two things to keep in mind when reading results:

- The rewrites come from a language model that has read a great deal of law, so this tests "would an automatic
  rewriter help", and the final assistant would use a language model for this step too. It is not a test of a
  specific product.
- Only the development half has rewrites. The test half has none and is untouched.

## Files

| File | Who wrote the rewrites | Experiment |
|---|---|---|
| `r6_dev.jsonl` | A separate agent (Claude Sonnet) that saw only the question texts | R6.1, R6.2 (recall@5 0.68 and 0.70; an upper bound) |
| `r6_gemini_dev.jsonl` | gemini-3.1-flash-lite, plain instructions | R6.3, R6.4 |
| `r6_5_dev.jsonl` | gemini-3.5-flash-lite, plain instructions | R6.5 |
| `r6_6_dev.jsonl` | gemini-3.1-flash-lite, instructions that also ask for the legal terms the provision would contain | R6.6 |
| `r6_7_dev.jsonl` | gemini-3.5-flash-lite, the same expanding instructions | R6.7 |

The cheap in-system rewriters (R6.3 to R6.7) gave +0.03 to +0.11 in recall@5 with every interval including zero, so none is used by the pipeline (decision 84). The expanding instructions were written after seeing the development results of R6.3.
