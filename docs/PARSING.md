# Parsing the EU Official Journal texts

How the downloaded XHTML becomes `Provision` records, how it is checked, and what the checks found. The code is in `src/law_assistant/parse/`; run it with `python -m law_assistant.parse.run_eu`.

## What a Provision is

One record per recital, article, numbered paragraph, list point, closing text or annex item, in reading order. Each knows its place (`path`: article 6, paragraph 1, point f is `("6", "1", "f")`), its heading and chapter, its language and version, and the cache key of the file it came from. Text is plain: no markup, no footnote markers, whitespace normalised. Recitals are kept apart from articles because they explain the law but do not bind.

## Results (14 October 2026, Official Journal texts)

| Act | Language | Provisions | Recitals | Articles | Annexes | Coverage | Problems |
|---|---|---|---|---|---|---|---|
| GDPR | EN | 956 | 173 | 99 | 0 | 100.00% | 0 |
| GDPR | ES | 956 | 173 | 99 | 0 | 100.00% | 0 |
| AI Act | EN | 1,422 | 180 | 113 | 13 | 99.87% | 0 |
| AI Act | ES | 1,424 | 180 | 113 | 13 | 99.88% | 0 |
| Digital Omnibus on AI | EN | 309 | 47 | 4 | 0 | 100.00% | 0 |
| Digital Omnibus on AI | ES | 305 | 47 | 4 | 0 | 100.00% | 0 |

Coverage is the letters and digits kept (text, labels, headings, "Article N") over those in the source's recitals, articles and annexes. The English and Spanish GDPR have exactly the same 956 ids; the AI Act differs by 2 ids in Annex X, where the English text leaves single-item sections unlabelled.

## The checks

For every parsed document (`parse/checks.py`): no duplicate ids; no empty provision unless it has children; article and recital numbers run 1 to N without gaps; known totals; every article has a heading; no leftover markup or odd whitespace; and coverage of at least 99.5%. Across languages, the id skeletons must match (GDPR exactly, AI Act within 4 ids).

## What the checks found, and how each was fixed

Each of these was invisible without a check. Every one became a test on a small fixture taken from the real markup.

1. **Spanish Article 4 uses a different layout.** The GDPR's definitions are tables in English but plain "1) ..." paragraphs in Spanish. The skeletons differed by 33 points until numbered paragraphs were read as points.
2. **Nested rows were read twice.** Iterating a table's rows also visited the rows of tables nested inside it, so sub-points appeared twice (and one level too high).
3. **Sibling sub-points.** In English Article 4(16) and 4(22) the (a), (b) tables follow the numbered table instead of sitting inside it.
4. **Annex sections.** Annex VIII and XI restart numbering under "Section A", "Section B"; without the section in the path the ids collided.
5. **A third list layout.** The Spanish Annex X uses three-column tables with an empty indent cell.
6. **The Digital Omnibus's quoted amendments** sit in wrapper divs (some with paragraph-style ids), in one-cell tables and in data tables of codes; coverage rose from 54% to 99.4%.

## Spot-checking by eye

The checks cannot say whether a sentence was read correctly, only that nothing structural is wrong. Golden provisions in `tests/test_parse_eu_real.py` assert the exact text of Article 6(1)(f), the definition of personal data, Recital 47, AI Act Article 5(1)(a) and Annex III against the official text. A human sample against the official pages is still planned before the corpus is trusted.
