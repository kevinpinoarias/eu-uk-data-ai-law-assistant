# Sources and licences

Every legal text this project retrieves comes from an official source and keeps that source's licence. This file lists what is used, under what terms, and the credit line each requires. The project's own code is Apache-2.0 (see `LICENSE`); that licence does **not** cover the texts below.

Terms were read on each source's own legal page on 13 October 2026. This is project research, not legal advice, and terms change, so they are re-checked before any document is downloaded. The document-level manifest and the facts confirmed in step 0.2 of the roadmap are below the tier tables.

## Tier 1 — the first version

| Source | Documents | Reuse terms | Required credit |
|---|---|---|---|
| EUR-Lex (EU) | Regulation (EU) 2016/679 (GDPR); Regulation (EU) 2024/1689 (AI Act); the AI Act amending regulation (the "Digital Omnibus on AI", Regulation (EU) 2026/1744, confirmed in step 0.2) | Legal documents reusable for commercial or non-commercial purposes under Commission Decision 2011/833/EU; consolidated texts and editorial content CC BY 4.0; metadata CC0 | "Source: EUR-Lex, © European Union." State when text is a summary or has been changed. Only the Official Journal version is authentic. |
| legislation.gov.uk (UK) | UK GDPR; Data Protection Act 2018; Data (Use and Access) Act 2025 | Open Government Licence v3.0 except where stated; max 1,500 requests per 5 minutes; identifying User-Agent; robots.txt followed | "Contains public sector information licensed under the Open Government Licence v3.0." |
| BOE (Spain) | Ley Orgánica 3/2018 (LOPDGDD), consolidated text | Free reuse, commercial or not, derivatives allowed, if the source is cited, the meaning is not distorted, consolidated texts are marked as informative only, the last update date is shown and no endorsement is implied | Copies: "Fuente de los datos: Agencia Estatal Boletín Oficial del Estado". Derived works: "Basado en datos de la Agencia Estatal Boletín Oficial del Estado". Mark consolidated texts "texto consolidado, de carácter meramente informativo". |

## Tier 1 manifest (checked 13 October 2026; nothing downloaded yet)

| Document | Identifier | Versions to ingest | Languages | Fetch route |
|---|---|---|---|---|
| GDPR, Regulation (EU) 2016/679 | ELI `http://data.europa.eu/eli/reg/2016/679/oj`, CELEX `32016R0679` | Official Journal text; the consolidated text (its CELEX to be confirmed in Phase 1) | EN, ES | EUR-Lex Cellar REST API |
| AI Act, Regulation (EU) 2024/1689 | ELI `http://data.europa.eu/eli/reg/2024/1689/oj`, CELEX `32024R1689` | Original, 12/07/2024 (`32024R1689`); consolidated, 27/07/2026 (`02024R1689-20260727`, listed by EUR-Lex as the current version) | EN, ES | EUR-Lex Cellar REST API |
| Digital Omnibus on AI, Regulation (EU) 2026/1744 of 8 July 2026 | ELI `http://data.europa.eu/eli/reg/2026/1744/oj`, CELEX `32026R1744`; OJ L, 24.7.2026 | Official Journal text (in force from 27 July 2026) | EN, ES (24 languages published) | EUR-Lex Cellar REST API |
| UK GDPR | `legislation.gov.uk/eur/2016/679` | Latest revised; dated versions to be tested through the API | EN | legislation.gov.uk API |
| Data Protection Act 2018 (c. 12) | `legislation.gov.uk/ukpga/2018/12` | Latest revised ("up to date with all changes known to be in force on or before 12 October 2026" when read) | EN | legislation.gov.uk API |
| Data (Use and Access) Act 2025 (c. 18, Royal Assent 19 June 2025) | `legislation.gov.uk/ukpga/2025/18` | Dated versions from 19/06/2025 to 30/09/2026 are published | EN | legislation.gov.uk API |
| LOPDGDD, Ley Orgánica 3/2018 | BOE-A-2018-16673; ELI `https://www.boe.es/eli/es/lo/2018/12/05/3/con` | Consolidated text, last updated 27/12/2025; the API holds every version since publication | ES | BOE open-data API (`/datosabiertos/api/legislacion-consolidada/id/BOE-A-2018-16673/texto`) |

## Facts confirmed in step 0.2

**EU AI Act timeline (read on the Official Journal text of Regulation (EU) 2026/1744):**
- Entered into force on the third day after publication (published 24 July 2026, so in force 27 July 2026).
- High-risk obligations (Chapter III, Sections 1 to 3) now apply from **2 December 2027** for Annex III systems (Article 6(2)) and **2 August 2028** for Annex I systems (Article 6(1)). The original date was 2 August 2026.
- Article 5(1) points (ba) and (bb), and Article 5(1a) and (1b), apply from 2 December 2026. AI systems that generate synthetic content and were on the market before 2 August 2026 must comply with Article 50(2) by 2 December 2026.
- Articles 102 to 110 apply from 27 July 2026.

**UK Data (Use and Access) Act 2025, in force in stages** (gov.uk commencement plan, last updated 12 October 2026, and legislation.gov.uk):
- 20 August 2025: first provisions, including the first changes to the UK GDPR, DPA 2018 and PECR.
- 5 February 2026: the main Part 5 changes to the UK GDPR (Commencement No. 6, S.I. 2026/82).
- 31 March 2026: the new erasure ground, Article 17(1)(g).
- 19 June 2026: the remainder of section 103 (data subject complaints), per the commencement notes on legislation.gov.uk.
- 30 September 2026: the ICO becomes the Information Commission; its functions transfer and the "ICO" name stays.

**The EU GDPR itself:** no adopted amendment found. The Digital Omnibus changes to the GDPR (proposed 19 November 2025) were still in negotiation in the sources found; to be verified on the Legislative Observatory (procedure 2025/0360(COD)) before Phase 1 ends.

## Fetch rules learned

- **EUR-Lex web pages are bot-protected.** A scripted request returns HTTP 202 with `x-amzn-waf-action: challenge`. We do not bypass it. The Publications Office's own routes are used instead: the Cellar REST API (a HEAD request for the GDPR by CELEX with an XHTML `Accept` header was answered with a redirect to the document and HTTP 200), its SPARQL endpoint, or the bulk data dump (needs an EU Login).
- **legislation.gov.uk:** `robots.txt` sets `Crawl-delay: 5`, so we wait at least 5 seconds between requests, well inside the 1,500-requests-per-5-minutes cap. Every request carries an identifying User-Agent.
- **BOE:** the open-data API serves the consolidated text with all versions; response format and parameters to be read from its technical document in Phase 1.

## Planned for later tiers (terms to be re-checked before use)

- **Tier 2:** EDPB guidelines and opinions (reuse authorised if the source is acknowledged, the meaning is not distorted and author and source marks are kept); European Commission AI Act guidelines (per-document notices); ICO guidance (text under OGL v3.0 with the credit "Information Commission's Office, [title and date], licensed under the Open Government Licence"; images and logos excluded); the ePrivacy Directive and the UK PECR; the EU–UK adequacy decision.
- **Tier 3:** CJEU case law; AEPD guides (CC BY-NC-SA 4.0 per document, non-commercial and share-alike, so their text is kept out of this repository); regulator enforcement decisions; GOV.UK AI policy papers (OGL v3.0, per-document check); adjacent EU laws.

## Excluded

Law-firm commentary, ISO/IEC standards and other paywalled material, and any page behind a bot check (never bypassed).

## Not legal advice

This project explains and cites public law texts. It is not legal advice, and answers may be out of date or wrong. Always check the official source.
