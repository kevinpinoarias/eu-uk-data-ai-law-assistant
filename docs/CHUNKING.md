# Chunking

How the parsed provisions become the pieces that are embedded, searched and cited. The code is in `src/law_assistant/chunk/` (`chunker.py` the rules, `checks.py` the soundness checks, `run_chunk.py` the build). Build with `python -m law_assistant.chunk.run_chunk`; it writes `data/chunks/*.jsonl` and a `manifest.json` (git-ignored, rebuilt from `data/parsed/`).

## Why

A provision is too small to search on its own ("(f) legitimate interests" means nothing without Article 6(1)) and a whole schedule is too big (the Data Protection Act 2018's Schedule 19 is 31,142 words). A chunk is the unit that gets embedded and returned, and it has to carry enough context to be understood and enough identity to be cited.

## The length profile that set the rules (words per natural unit)

| Unit | Count | Median | 90th percentile | Longest |
|---|---|---|---|---|
| All units, all texts | 2,578 | 189 | 653 | 31,142 |
| GDPR articles | 99 | 208 | 691 | 1,292 |
| AI Act articles (consolidated, EN) | 119 | 314 | 879 | 2,617 |
| DPA 2018 sections | 261 | 198 | 425 | 897 |
| DPA 2018 schedules | 21 | 934 | 6,492 | 31,142 |
| LOPDGDD articles | 98 | 164 | 552 | 1,114 |
| GDPR recitals | 173 | 108 | 264 | 493 |

22% of the units are over 400 words and 87 are over 1,000.

## The rules

1. **The unit is the article, section, annex, schedule, disposition or recital.** If it fits in the cap it is one chunk. Each Spanish preamble paragraph is a recital of its own.
2. **A longer unit splits at its top-level paragraphs, then at the points of an overlong paragraph, then at sentences, and only as a last resort by words.** A paragraph stays with its points while the pair fits; a closing text stays with the point above it. The cap (400 words, a setting) is therefore a ceiling that nothing exceeds.
3. **Numbering is put back** ("1.", "(a)", "–" for bullets, a capital on spelled-out markers such as "Uno.") because the parser moved labels into the path.
4. **Every chunk has a context line**: law, chapter, citation and heading (`GDPR (Regulation (EU) 2016/679) | CHAPTER II — Principles | Article 6: Lawfulness of processing`). The embedded text is the context plus the law text; they are stored separately so Phase 3 can switch the context off and measure it.
5. **Every chunk lists the ids of its provisions** (exact pinpoints such as Article 6(1)(f) are built from them in the answer layer), the language, jurisdiction, version and `in_force_from` (the latest date among its provisions).
6. **Ids are stable**: `<version>:<language>:<first provision id>`, with `#n` for the second piece of a single provision. The same input and cap always give byte-identical output.

## Checks

For every document: no empty chunk, no duplicate id, none over the cap, no provision lost, and the letters and digits of all chunks equal those of the provisions plus their restored numbering (so nothing is invented or dropped). The build also fails if any document has a problem.

## Results (cap 400 words, 15 October 2026)

| Document | Provisions | Chunks | Units split | Median words | Max |
|---|---|---|---|---|---|
| GDPR, Official Journal (EN / ES) | 956 / 956 | 312 / 319 | 28 / 31 | 142 / 160 | 399 / 398 |
| GDPR, consolidated (EN / ES) | 783 / 783 | 136 / 143 | 25 / 27 | 219 / 235 | 396 / 398 |
| AI Act, Official Journal (EN / ES) | 1,426 / 1,428 | 410 / 443 | 69 / 83 | 191 / 230 | 400 / 399 |
| AI Act, consolidated 27 Jul 2026 (EN / ES) | 1,374 / 1,386 | 235 / 266 | 58 / 66 | 281 / 275 | 400 / 400 |
| AI Omnibus (EN / ES) | 309 / 305 | 92 / 105 | 5 / 10 | 236 / 277 | 400 / 398 |
| UK GDPR | 1,092 | 298 | 29 | 138 | 398 |
| Data Protection Act 2018 | 6,813 | 533 | 54 | 266 | 400 |
| Data (Use and Access) Act 2025 | 2,430 | 332 | 68 | 280 | 400 |
| LOPDGDD (as in force 14 Oct 2026) | 763 | 207 | 20 | 137 | 399 |

Total 3,831 chunks, no problems (3,876 before the omitted UK provisions were removed). Spot-checked by eye: GDPR Article 6 (two chunks, cut between paragraphs 2 and 3), Recital 47, AI Act Annex VI, LOPDGDD Article 7 and its third final disposition, DPA 2018 Schedule 19 (101 chunks cut at numbered paragraphs).

## What building it found

- **A parser gap (finding 26 in `PARSING.md`).** The checks reported an empty chunk for AI Act Annex VI: the Official Journal parse had kept the annex heading but none of its four items. Fixed in the parser, with a test.
- **Two rendering slips**, found by reading chunks: a trailing space after an untitled paragraph number, and "uno." where the BOE prints "Uno.".
- **36 chunks made of nothing but dots**, found later while reviewing the gold set: the UK texts show omitted law as lines of dots and the parser had kept them (finding 27 in `PARSING.md`). They are gone; a check now confirms no chunk is only dots.

## Not decided here (for Phase 3, as pre-registered experiments)

- Whether 400 words is the right size, and whether the context line helps.
- Whether to fetch the neighbours of a split article's piece when one is retrieved.
- Which versions go into the default index. All versions are chunked side by side (Official Journal and consolidated text, English and Spanish); how to answer "as of" a date, and how to avoid returning two versions of the same article, belongs to the retrieval and answer layers.
- The cap is in words. It will be checked against the real tokenizer when the embedding model is chosen.
