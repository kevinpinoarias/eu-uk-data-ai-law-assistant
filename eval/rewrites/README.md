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
