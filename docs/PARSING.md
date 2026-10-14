# Parsing the EU texts (Official Journal and consolidated)

How the downloaded XHTML becomes `Provision` records, how it is checked, and what the checks found. The code is in `src/law_assistant/parse/` (`eu_oj.py` for the Official Journal texts, `eu_consolidated.py` for the consolidated texts); run everything with `python -m law_assistant.parse.run_eu`.

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

## The consolidated texts (14 October 2026)

A consolidated text is the law as currently amended. It has no recitals and different markup, so it has its own parser; the stored `version` field says which text a provision comes from (`oj`, `consolidated-20160504`, `consolidated-20260727`).

| Text | Language | Provisions | Articles | Annexes | Coverage | Against the Official Journal text |
|---|---|---|---|---|---|---|
| GDPR, consolidated | EN | 783 | 99 | 0 | 100.00% | 16 wording changes, 0 ids on one side only |
| GDPR, consolidated | ES | 783 | 99 | 0 | 100.00% | 38 wording changes, 0 ids on one side only |
| AI Act, consolidated 27 July 2026 | EN | 1,374 | 113 + 6 inserted | 14 | 99.95% | 64 wording changes, 154 ids on one side only |
| AI Act, consolidated 27 July 2026 | ES | 1,386 | 113 + 6 inserted | 14 | 99.94% | 64 wording changes, 168 ids on one side only |

The six inserted articles are 4a, 60a and 75a to 75d, and the new Annex XIV: all added by the Digital Omnibus on AI.

### The cross-check

Each consolidated parse is compared with the Official Journal parse id by id, ignoring spacing. Every difference should be an amendment or a corrigendum, which makes it an independent test of the parser.

- **GDPR:** the skeletons are identical in both languages. The 16 English and 38 Spanish wording changes are the 2018 corrigendum; for example Article 37(1)(c) says "and" in the Official Journal text and "or" in the consolidated text.
- **AI Act:** 56 articles and annexes differ. All but Articles 103 to 109 and Annex VI are ones the Omnibus names. Those eight are articles that amend other acts and quote them: the two renderings set the quoted passages differently (a quote mark, a capital), so the differences are typography, not amendments.
- **English against Spanish:** after mapping the English labels for inserted provisions (14a, ba) onto the Spanish ones (14 bis, b bis), the consolidated AI Act differs by 12 ids, all in the new Annex XIV, where Spanish labels single items that English leaves unlabelled.

### What the checks found in the consolidated markup

7. **Different markup altogether:** paragraphs are `div.norm` with a number span and lists are two-column grids, not tables.
8. **Amendment marks inside the text:** `►C1 ... ◄` brackets and `▼B` lines, and footnote markers that leave "()" behind once removed.
9. **A second subparagraph** is a sibling paragraph in the consolidated markup but part of the paragraph in the Official Journal markup; it is merged so both parses agree.
10. **The Spanish consolidated Article 4** lays definitions out as `dlist-term | dlist-definition` tables with "a)" lines, a third layout after the two in the Official Journal text.
11. **Annex sections** ("Section A", "3. Quality management system") and dotted numbering ("3.1.") appear as plain paragraphs and divs.
12. **Inserted provisions** are numbered 14a in English and "14 bis" in Spanish.

