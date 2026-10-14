# Parsing the EU and UK texts

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

## The UK texts (15 October 2026)

`uk.py` reads the three legislation.gov.uk XML files; run them with `python -m law_assistant.parse.run_uk`. The XML is the richest source: ids are already citations and elements say from when they apply.

| Text | Provisions | Numbered units | Schedules or annexes | Left out | Coverage |
|---|---|---|---|---|---|
| UK GDPR | 1,169 (173 recitals) | 80 articles + 21 inserted | 2 annexes | 19 repealed (Articles 60 to 76, 92, 93) | 100.00% |
| Data Protection Act 2018 | 6,917 | 215 sections + 46 inserted | 21 schedules | 3 repealed, 2 not yet in force | 99.96% |
| Data (Use and Access) Act 2025 | 2,430 | 134 sections | 15 schedules | 12 not yet in force (sections 45 to 48, 60 to 62, 64, 65, 131) | 99.98% |

The missing article and section numbers are exactly the repealed or not-yet-in-force ones: the checks allow no other gap. The version label is `revised-YYYYMMDD`, the retrieval date, because the site serves the latest text.

### Cross-checks with outside facts

- **Dates agree with the government's commencement table.** `in_force_from` for UK GDPR Article 17(1)(g) is 31 March 2026, for section 103 of the new Act 19 June 2026 and for section 1 20 August 2025, which are the dates in the gov.uk commencement plan.
- **UK GDPR against the EU text.** Of 534 article-level ids both texts share, 289 have identical wording and 245 differ; Article 5(1)(a) is word for word the same, Article 6(1)(ea) (recognised legitimate interests) exists only in the UK text, and Chapter VII (Articles 60 to 76) exists only in the EU text.
- **The new Act's missing sections** equal the not-yet-in-force ones, as above.

### What the checks found in the UK markup

13. **Three document shapes:** the UK GDPR is retained EU text (preamble, chapters, `EUBody`), the other two are Acts (parts, cross-headings, schedules).
14. **Amendment markup** (`Addition`, `Substitution`) wraps the current wording and is kept; commentary and footnote markers are not text.
15. **Quoted amendments to other texts** (`BlockAmendment`: 339 in the Data Protection Act, 290 in the new Act) have no citation ids; each is kept as one closing text of its paragraph.
16. **Four recitals** (19, 50, 71, 143) put their first sentences in a `Title` element; coverage showed 4.3% of the recital text missing until it was read.
17. **A table beside the paragraph** (section 206, the index of defined expressions) is a sibling of the paragraph, not inside it; one closing line per row.
18. **Schedule paragraphs outside a heading group** have no title of their own; their cross-heading is kept in the `chapter` field.

