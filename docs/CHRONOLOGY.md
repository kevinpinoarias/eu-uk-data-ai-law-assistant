# Chronology: every commit, oldest first

Generated from the git history by `scripts/make_chronology.py`; regenerate after a commit. It answers "what was done when"; the reasoning is in `DECISIONS.md`, the story in `JOURNEY.md`, the results in `EXPERIMENT_INDEX.md`. Nothing is pushed by the assistant: pushing is done by the project owner.

| # | When | Commit | What |
|---|---|---|---|
| 1 | 2026-10-13 19:03 | `7a41b99` | Add project scaffolding: licence, README and source licences |
| 2 | 2026-10-13 19:22 | `caae5dd` | Record the Tier 1 document manifest and the facts confirmed in step 0.2 |
| 3 | 2026-10-14 12:04 | `93d1f5d` | Add project skeleton: package, tests and CI |
| 4 | 2026-10-14 12:33 | `c8dd53e` | Add the UK fetcher: polite, cached and verified by tests |
| 5 | 2026-10-14 12:43 | `f35273b` | Add the BOE fetcher for the Spanish data-protection law |
| 6 | 2026-10-14 13:02 | `61b34e4` | Add the EU fetcher: five acts in English and Spanish via Cellar |
| 7 | 2026-10-14 13:31 | `42c1883` | Add the common Provision model and the EU Official Journal parser |
| 8 | 2026-10-14 13:47 | `b19323b` | Add the consolidated EU text parser and cross-check it against the OJ |
| 9 | 2026-10-14 14:01 | `dae98cc` | Add the UK parser for the UK GDPR, the DPA 2018 and the new Act |
| 10 | 2026-10-14 14:17 | `f84b5bd` | Add the BOE parser for the Spanish data-protection law (LOPDGDD) |
| 11 | 2026-10-14 14:39 | `67655e3` | Fix the Official Journal parser: AI Act Annex VI items were dropped |
| 12 | 2026-10-14 14:39 | `73d6a9e` | Add the chunker: provisions in, retrievable chunks out |
| 13 | 2026-10-14 18:30 | `f34e63c` | Add the gold question set schema and its checks (Phase 2, step 2.0) |
| 14 | 2026-10-14 19:08 | `8f23875` | Skip omitted UK provisions shown as lines of dots |
| 15 | 2026-10-14 19:08 | `6a5071f` | Draft 65 gold questions after a lawyer-style review |
| 16 | 2026-10-14 19:24 | `5154f67` | Complete the gold set: 15 questions that fill the gaps in the first 65 |
| 17 | 2026-10-14 21:33 | `bd0faf0` | Add the structured table of exact facts (Phase 2, step 2.3) |
| 18 | 2026-10-15 10:50 | `20cc804` | Add the retrieval metrics (Phase 2, step 2.4) |
| 19 | 2026-10-15 11:14 | `9243e0c` | Review, split and freeze the gold set (Phase 2, step 2.5) |
| 20 | 2026-10-15 12:00 | `be0a1f7` | Add the retrieval harness and the first baselines (Phase 3, step 3.0, R1) |
| 21 | 2026-10-15 12:57 | `195c796` | Add the embedding client, cache and dense search; R1.3 script (not yet run) |
| 22 | 2026-10-15 13:14 | `6986e7f` | Retry rate limits properly; add version policies, collapsing, R8 and R10 (BM25) |
| 23 | 2026-10-15 13:20 | `e7f7e20` | Add reciprocal rank fusion, R3 with BM25, the Phase 4 plan and the journey doc |
| 24 | 2026-10-15 13:44 | `7fbd515` | Add the local BGE-M3 embedding model and run R4.1 and R2 |
| 25 | 2026-10-15 14:07 | `2facbe9` | Repeat R3, R8 and R10 with BGE-M3; add cross-language and rank-depth diagnostics |
| 26 | 2026-10-15 16:02 | `3f9c7a2` | Add the reranker (R5) and question rewriting (R6); document the why |
| 27 | 2026-10-15 17:43 | `ec0c219` | Add the answer layer, Gemini client and rewriter experiments; document the why |
| 28 | 2026-10-15 18:09 | `b1e34db` | Add filters experiment, service layer, web page and deployment notes |
| 29 | 2026-10-15 20:45 | `4f65e8f` | Second gold review (version 2), R7 vector stores, Spanish diagnostic, Phase 5 plan |
| 30 | 2026-10-15 20:52 | `cfc1984` | Add the documentation set and pre-register the test-half retrieval confirmation |
| 31 | 2026-10-15 21:01 | `39e9e0e` | Log T1 (retriever confirmed on the test half); pre-register the answer-layer confirmation |
| 32 | 2026-10-15 21:08 | `91dd3f1` | Build and run the container; document the results and the remaining measurements |
| 33 | 2026-10-15 21:16 | `bc3d683` | Add degraded mode to the pipeline and pre-register P4.7 |
| 34 | 2026-10-15 21:24 | `a233f17` | Add Spanish page labels, accessibility checks, CI smoke test, Qwen3 embedder; pre-register R4.2 |
| 35 | 2026-10-15 21:46 | `a8851ac` | Log R4.2 (second embedding model not adopted), degraded mode, page, CI smoke test |
| 36 | 2026-10-16 12:03 | `03eedb6` | Add bilingual privacy notice, hourly trace pruning, accessibility checklist; log P4.5 (variant D not adopted) |
| 37 | 2026-10-16 12:08 | `d45cf1b` | Fill the privacy notice with the owner's details; put the lawyer's review back on the list |
| 38 | 2026-10-16 12:32 | `4d94b57` | Log P4.6: the answer layer on the sealed test half did not beat memory |
| 39 | 2026-10-16 12:32 | `70075f9` | Regenerate the chronology |
| 40 | 2026-10-16 13:49 | `ce80ad0` | Add deploy prep and routing-fix candidates: cold-start notice, data bundle, deploy workflow, batch C |

## What each commit said

### 1. `7a41b99` Add project scaffolding: licence, README and source licences

Starts the EU / UK data and AI law assistant: a bilingual (English and
Spanish) retrieval-augmented assistant over EU, Spanish and UK
data-protection and AI law. Nothing is built yet; this commit holds the
scaffolding and the licence research.

- LICENSE and NOTICE: code under Apache-2.0. The legal texts the
  project retrieves keep their own licences and are not covered by it.
- SOURCES.md: the Tier 1 documents (GDPR, AI Act and its amending
  regulation, UK GDPR, Data Protection Act 2018, Data (Use and Access)
  Act 2025, LOPDGDD) with each source's reuse terms and required credit
  line, read from the sources' own legal pages on 13 October 2026, plus
  the planned later tiers and exclusions.
- README.md: the purpose, the Tier 1 scope, the six-phase plan and a
  not-legal-advice disclaimer.
- .gitignore, .gitattributes, .env.example: secrets, fetched source
  documents and built indexes are never committed; line endings are
  normalised; the fetcher contact variable is documented.

### 2. `caae5dd` Record the Tier 1 document manifest and the facts confirmed in step 0.2

Adds the document-level manifest for the seven Tier 1 documents
(identifiers, versions to ingest, languages and fetch route), the
confirmed AI Act timeline under Regulation (EU) 2026/1744, the staged
commencement of the Data (Use and Access) Act 2025, and the fetch rules
learned: EUR-Lex pages are bot-protected, so its Cellar API is used;
legislation.gov.uk asks for a 5-second crawl delay. Marks the Omnibus
as confirmed and updates the README's Phase 0 status.

### 3. `93d1f5d` Add project skeleton: package, tests and CI

Python 3.12 package under src/law_assistant with its settings module:
the project paths, and the identifying User-Agent every fetcher must
send (legislation.gov.uk does not accept anonymous agents). A missing
contact or one with control characters is refused. Nine tests, written
before the code, also guard that downloaded sources stay in a
git-ignored folder and that the package version matches pyproject.toml.

Adds a CI workflow (lint, format check, tests, secret scan, read-only
permissions) and a development section in the README.

### 4. `c8dd53e` Add the UK fetcher: polite, cached and verified by tests

Fetches the three Tier 1 UK documents (UK GDPR, Data Protection Act
2018, Data (Use and Access) Act 2025) from legislation.gov.uk into
data/raw/, which git ignores. Each document is fetched once and saved
with a record of its URL, retrieval time, hash, size, licence and
credit line; writes are atomic so a failed download leaves nothing
behind.

Politeness is enforced in code and tests: an identifying User-Agent (a
missing contact is an error), robots.txt honoured, at least 5 seconds
between requests or the site's crawl delay if slower, and http(s) URLs
only. A small .env reader supplies the contact. 31 new tests, written
before the code, use a fake client and a fake clock and never touch the
network.

Adds docs/DECISIONS.md, the record of design decisions so far.

### 5. `f35273b` Add the BOE fetcher for the Spanish data-protection law

Fetches the LOPDGDD (Ley Orgánica 3/2018) from the BOE open-data API
into data/raw/boe_es/: the consolidated text with its seven dated
versions (XML), its metadata (JSON) and its ELI record (XML). Each is
saved with the BOE's credit lines and the informative-only notice.

Documents can now name the format they ask for through an Accept
header. The command-line part shared by every source (document
selection, robots.txt, throttling, reporting) moves into fetch/runner,
and the UK fetcher uses it too. Nine new tests, written before the
code; the SOURCES.md manifest records the versions found.

### 6. `61b34e4` Add the EU fetcher: five acts in English and Spanish via Cellar

Fetches the GDPR (Official Journal and consolidated text), the AI Act
(Official Journal text and the consolidated text of 27 July 2026) and
the Digital Omnibus on AI, each in English and Spanish, as XHTML into
data/raw/eur_lex_cellar/ (ten files). EUR-Lex's web pages answer
scripts with a bot challenge, so the official Cellar API is used: a
CELEX URL with the format and language chosen by headers. Documents can
now name a language through an Accept-Language header. Each file keeps
the EUR-Lex credit line, the licence, and for consolidated texts the
"no legal effect" notice.

Checked after the download: recitals exist only in the Official Journal
texts (GDPR 173, AI Act 180, Omnibus 47), article counts match across
languages, and the consolidated AI Act carries the Omnibus dates.
Recorded in SOURCES.md and docs/DECISIONS.md. Six new tests.

### 7. `42c1883` Add the common Provision model and the EU Official Journal parser

Every parser will output one record, Provision, whatever the source
markup: recital, article, paragraph, point, closing text or annex item,
with its place in the law (path), heading, chapter, language and
version, saved as JSON Lines in the git-ignored data/parsed/.

The EU parser reads the GDPR, the AI Act and the Digital Omnibus in
English and Spanish from the cached XHTML. A parse is trusted only
after structural checks: unique ids, no empty leaves, numbering
without gaps, the known totals (GDPR 99 articles and 173 recitals; AI
Act 113, 180 and 13 annexes; Omnibus 4 and 47), clean text, matching
English and Spanish skeletons, and coverage of the source text. The
checks found six real markup differences, each now a test; the GDPR
parses to identical skeletons in both languages and coverage is
99.9% to 100%.

Tests on the real files skip themselves when the data is absent (CI);
fixtures taken from the real markup carry the logic tests. Adds
docs/PARSING.md and decisions 16 to 21; relaxes the line-length lint
rule for tests only.

### 8. `b19323b` Add the consolidated EU text parser and cross-check it against the OJ

Parses the consolidated GDPR and the consolidated AI Act of 27 July
2026 in English and Spanish. The markup differs completely from the
Official Journal text (paragraphs as div.norm with a number span,
two-column list grids, amendment marks inside the text), so it gets
its own parser sharing the id builder and the checks. Inline marks
(►C1 ... ◄, ▼B) and the empty brackets left by footnote markers are
removed, a second subparagraph continues its paragraph as in the
Official Journal text, and the Spanish definition tables, plain "a)"
lines, annex sections and dotted numbering are read.

Each consolidated parse is compared with the Official Journal parse id
by id, ignoring spacing: the GDPR matches exactly apart from the 2018
corrigendum (16 wording changes in English, 38 in Spanish), and every
changed AI Act article is one the Omnibus names, apart from eight that
quote other acts and differ only in typography. Coverage is 99.9% to
100%; Spanish and English skeletons differ only in the new Annex XIV.

The report now covers all ten parses and compares inserted labels
across languages (14a with 14 bis). Adds decisions 22 to 25 and the
consolidated section of docs/PARSING.md. 38 new tests; the real-file
tests still skip when the data is absent.

### 9. `dae98cc` Add the UK parser for the UK GDPR, the DPA 2018 and the new Act

Parses the three legislation.gov.uk XML files into the common
Provision shape. The XML's own ids are the citations (article-6-1-a,
section-6A-2, schedule-1-paragraph-3-2-a), so places come from them;
insertions and substitutions are read as the current wording, repealed
and not-yet-in-force provisions are left out and counted, quoted
block amendments become closing text, tables are kept row by row, and
each provision carries the date its current version applies from. The
model gains the units section and schedule.

The only article and section numbers allowed to be missing are exactly
the skipped ones (UK GDPR Articles 60 to 76, 92 and 93; ten sections
of the new Act not yet in force), and coverage is 99.96% to 100%.
Dates agree with the government's commencement table, and the UK GDPR
compares with the EU text (534 shared ids, 289 identical).

Checks now cover sections, schedules, inserted lettered articles and
headings counted per distinct title. Adds the UK section of
docs/PARSING.md and decisions 26 to 29. 32 new tests; the real-file
tests skip when the data is absent.

### 10. `f84b5bd` Add the BOE parser for the Spanish data-protection law (LOPDGDD)

Parse the BOE's consolidated XML into Provisions as of a date: the
version in force is chosen from the dated versions, and its date is
kept as in_force_from. Block titles give the citation (the block ids
are not citations); numbering markers are found by their text because
the paragraph classes are inconsistent; quoted amendments are kept as
closing text; editorial notes are skipped; the preamble becomes
recitals. Adds the "disposition" unit and a matching expected-count
check.

Result: 763 provisions in force on 14 Oct 2026 (97 articles + 53 bis,
46 dispositions, 37 recitals), coverage 100.01%, no structural
problems. Tests cover a fixture from the real markup and the real file
(skipped when it is not downloaded). Documents the findings and
decisions 30 to 34.

### 11. `67655e3` Fix the Official Journal parser: AI Act Annex VI items were dropped

Annex VI numbers its four items as a div of two inline paragraphs (label,
then text), a shape found only there. The annex parser read only direct
p and table children, so it kept the heading and none of the text. The
item divs are now turned into numbered paragraphs the list code reads.

Found by the chunk checks (an empty chunk). Coverage of the Official
Journal AI Act rises from 99.87% / 99.88% to 99.99% in English / Spanish
(4 more provisions each). The cross-check test no longer excuses Annex
VI as typography: it was missing text. Adds a fixture case and a golden
test, and records the finding in docs/PARSING.md.

### 12. `73d6a9e` Add the chunker: provisions in, retrievable chunks out

A chunk is one article, section, annex, schedule, disposition or recital
when it fits in the cap (400 words, a setting). Longer units split at
paragraphs, then points, then sentences, then words, so the cap is a firm
ceiling; a paragraph stays with its points while the pair fits. Numbering
is restored in the text, each chunk carries a context line (law, chapter,
citation, heading) and the ids of its provisions, and ids are stable so a
rebuild gives identical files.

Checks per document: no empty or duplicate chunk, none over the cap, no
provision lost, and letters and digits equal to the provisions plus their
numbering. Result: 3,876 chunks over the 14 parsed documents, no problems.
The build writes data/chunks/ and a manifest (git-ignored).

Adds docs/CHUNKING.md and decisions 35 to 40.

### 13. `f34e63c` Add the gold question set schema and its checks (Phase 2, step 2.0)

A gold question names the provisions that answer it by instrument and
unit (with optional pinpoint ids, quotes, version and language), never by
chunk, so the labels survive the chunking experiments. The set is read,
written and frozen by a hash that ignores order and changes with any edit,
and the plan for 80 questions (type, language and refusal-reason targets)
is held as data.

Checks: well-formed questions (route follows from type, a retrieval
question has a primary gold provision, a refusal has none and a reason, a
numeric question has a table key, valid as_of dates, no duplicates), the
mix against the plan, every gold unit, pinpoint id and quote found in the
parsed corpus, and a leakage warning comparing each question with its gold
text by word overlap weighted by word rarity (the first plain version
flagged ordinary topic vocabulary).

Adds docs/GOLD_SET.md and decisions 41 to 46.

### 14. `8f23875` Skip omitted UK provisions shown as lines of dots

legislation.gov.uk shows law that has been omitted as a Text of dots with
no status flag, so the UK parsers kept it as text: 181 provisions in the
UK GDPR and the Data Protection Act 2018 (for example the UK GDPR's
Articles 22 and 77), and the chunker made 36 chunks that said nothing.

A provision whose whole content is dots, or only omitted sub-provisions,
is now left out and counted like the repealed ones, a closing line of dots
(omitted words after a list) is dropped, and the coverage yardstick skips
them too. Their numbers are known gaps: UK GDPR 80 numbered articles
become 61 (19 omitted) and DPA 2018 215 sections become 202 (13 omitted).
Coverage is unchanged (100.00%, 99.96%, 99.98%); chunks 3,876 -> 3,831.

Found while reviewing the gold question set. Records the finding in
docs/PARSING.md and docs/CHUNKING.md and adds a real-data test that no
chunk is only dots.

### 15. `6a5071f` Draft 65 gold questions after a lawyer-style review

65 of the 80 gold questions (13 lookups, 6 definitions, 8 cross-references,
9 EU-UK comparisons, 7 Spanish-law, 8 as-of, 6 numeric, 8 refusals; 32
Spanish and 33 English), each with its gold provisions (instrument, unit,
pinpoint ids, quotes), a short expected answer and notes on ambiguities.
All units, pinpoints and quotes are checked against the parsed corpus and
no question copies its answer's wording.

Every answer was re-read against the whole provision as a lawyer would:
the data protection officer rule now includes Article 37(4) and national
law, the high-risk AI duties carry the postponed application dates, the
AI literacy answer is pinned to the amended text, jurisdiction cues were
added where UK and EU texts run in parallel, and before-and-after pairs
cover the original and current wording of three AI Act provisions.

Adds the metric rules for step 2.4 and decisions 47 to 52 to
docs/GOLD_SET.md and docs/DECISIONS.md.

### 16. `5154f67` Complete the gold set: 15 questions that fill the gaps in the first 65

Adds q066 to q080, chosen by listing the ways of asking the first 65 did
not cover: scope, marketing and the right to object, a false premise,
controller versus processor, a keyword-style query answered partly by a
recital, two laws applying at once, who enforces the AI Act, the UK Acts
beyond the UK GDPR, Spain's advertising-exclusion systems, application
dates, a jurisdiction-ambiguous query, a two-step numeric answer, a fact
outside the corpus, and applying the rule to the user's own facts.

The set of 80 matches the plan exactly (type, language and refusal
reason) and every gold unit, pinpoint and quote is checked against the
parsed corpus. Adds a third phrasing style, terse, tests that keep the
committed set well formed and on plan, and decisions 53 and 54.

### 17. `bd0faf0` Add the structured table of exact facts (Phase 2, step 2.3)

19 typed facts (fine ceilings, deadlines, ages, application dates for the
EU, the UK and Spain), each with a one-line answer in English and Spanish,
caveats, and its source provisions with quotes. The assistant will look
these up by key instead of reading figures out of prose.

A script proves that every number and date in a fact's value appears in
the provisions it cites (digits with grouped thousands, number words only
where they count a period or an age, dates in both languages); tests
include a negative control that corrupts an amount, a date and a period on
the real corpus and checks all three are caught. Each numeric gold
question must name an existing fact and state its figures.

Moves the provision check into a reusable function. Adds docs/FACTS.md
and decisions 55 to 58.

### 18. `20cc804` Add the retrieval metrics (Phase 2, step 2.4)

hit@k, recall@k, MRR and nDCG@k for a ranked list of chunks against a
question's gold provisions, with seeded bootstrap intervals and a paired
bootstrap for comparing two variants on the same questions. A chunk is a
hit when it has the gold provision's instrument and unit, its pinned
version and language, and (when pinpoints are listed) one of its
provision ids. Each gold provision is credited once, at its first
matching chunk, so the several copies of a text in the index neither help
nor hurt; hit, recall and MRR use primary provisions only, nDCG is graded.
Runs are files of ranked chunk ids.

Tests include real-data checks: every gold provision of every retrieval
question is reachable by a real chunk, an oracle ranking scores 1 and an
empty one 0, and version and pinpoint rules behave on real examples.

Adds docs/METRICS.md and decisions 59 to 62, and drops the owner column
from the decisions log.

### 19. `9243e0c` Review, split and freeze the gold set (Phase 2, step 2.5)

Five independent reviewer passes read the 80 questions blind (question,
expected answer and cited provision text only). The first draft had 15
questions fine, 53 with minor findings and 12 with major ones; every
finding was verified against the corpus and fixed where it held:
corrected questions built on a false premise (the original bias-detection
rule), a wrongly narrowed legal term (the UK malicious person), a wrong
article (work email), an overstated EU-UK difference, missing gold
provisions and omitted conditions.

The set is split 40 development / 40 test, stratified by type and
language, seed 20261015, with 31 retrieval questions in each half, and
frozen with a manifest holding its SHA-256 fingerprint, date, seed, counts
and an honest review statement (not reviewed by a qualified lawyer). A CI
test fails on any edit. Adds the split and manifest code, tests, decisions
63 to 67, and a rule that the gold provisions of one question must be
satisfiable by different chunks.

### 20. `be0a1f7` Add the retrieval harness and the first baselines (Phase 3, step 3.0, R1)

A retriever returns a ranked list of chunk ids for a question; the runner
scores it on the gold questions with the metrics from step 2.4. BM25 is
implemented in plain Python (no dependency), its formula checked against a
hand-computed example, ties broken by chunk id, with optional accent
folding. A random retriever gives the floor and an oracle built from the
gold gives the ceiling.

R1 is pre-registered in the script's docstring and run on the 31
development retrieval questions only: BM25 plain recall@5 0.24 (95 %
interval 0.12 to 0.39); accent folding is not better, so plain BM25 is
the baseline. A diagnostic, labelled as exploration, shows why: the right
article for one question ranks 724th of 3,831 because it says "designate
a data protection officer" where the user wrote "name a person
responsible"; every result is in the question's own language; and copies
of one article use up top-five slots.

Adds docs/PHASE3_PLAN.md (the pre-registered plan for R1 to R11),
docs/EXPERIMENTS.md (the log), docs/HOW_RETRIEVAL_WORKS.md (the ideas in
plain words, with numbers from this corpus) and decisions 68 to 70.

### 21. `195c796` Add the embedding client, cache and dense search; R1.3 script (not yet run)

A small client for Google's gemini-embedding-2 using only the standard
library: batches, paced requests, retries with growing pauses on 429 and
server errors, the key sent only in a header and never in a message or
repr. Passages are sent as "title: {context line} | text: {chunk}" and
questions as "task: search result | query: {question}", Google's
documented forms.

Vectors are cached on disk by model and prompt, so each chunk is embedded
once, an interrupted run resumes, and changing the key costs nothing.
Search is brute-force cosine in plain Python; a shorter vector is made by
truncating and renormalising. All of it is tested against a fake network
(no key used).

experiments/r1_3_embeddings.py carries its pre-registration (variant,
a preliminary check that a 768-number request matches the truncated
3,072-number vector, decision rule, stated expectation). Adds the model
specifications read from the official pages to docs/HOW_RETRIEVAL_WORKS.md.

### 22. `6986e7f` Retry rate limits properly; add version policies, collapsing, R8 and R10 (BM25)

Embedding run: Google's free tier limits sustained speed, and the first run
failed on a 429 after retrying for seconds. A 429 now waits at least 15
seconds and keeps doubling, or obeys the retry delay in the reply; other
errors keep short growing pauses; an error message keeps 1,500 characters
so the limit that was hit can be read. The preliminary check passed (a
768-number request matches the truncated 3,072-number vector, cosine 1.0).

R8 and R10, pre-registered and run with BM25 on the 31 development
questions: index policies (everything, current text only, original text
for questions dated before 27 July 2026) and collapsing copies of a
provision in the results. Nothing is adopted: R8.2 and R8.3 gain 0.008
recall@5 (interval 0.000 to 0.024) and R10 changes nothing, because BM25
finds the right article in its top 10 for only about 30 % of required
provisions, so slots and superseded copies are not the bottleneck. The
questions are repeated with embeddings. Logged with the reading against
the stated expectations in docs/EXPERIMENTS.md.

### 23. `e7f7e20` Add reciprocal rank fusion, R3 with BM25, the Phase 4 plan and the journey doc

Reciprocal rank fusion (R2): each ranked list gives each result 1 over
(60 + its place), optionally weighted; tested against the worked example.
experiments/r2_fusion.py carries its pre-registration (equal weights first,
a 2 to 1 weighting only if the equal-weight version improves on the better
single retriever, compared with that better single retriever) and refuses
to run until every chunk has a saved vector.

R3 with BM25 (chunk caps 200, 300, 600 and no context line), pre-registered
and run on the 31 development questions: nothing improves on the 400-word
baseline; logged as provisional with the reading against the stated
expectations.

Adds docs/PHASE4_PLAN.md (the LangGraph answer layer explained from scratch,
the workflow, the measures and the decisions to take together),
docs/JOURNEY.md (every step so far and why, in plain words), an updated
README status and decisions 71 to 73 (BM25-only results are provisional;
the fusion rule; identical chunks share one stored vector).

### 24. `7fbd515` Add the local BGE-M3 embedding model and run R4.1 and R2

BGE-M3 (BAAI, MIT) runs on this machine's graphics card: PyTorch 2.7.1 for
CUDA 12.6 (the build still supports the card's architecture, checked after
installing), transformers and numpy as the optional extra
open-embeddings, and a helper that downloads only the needed files (2.27 GB
weights) into the git-ignored data/models. The wrapper batches texts by
length, needs no prefix, and keeps the model call injectable so it is tested
without PyTorch; real-model tests (1,024 numbers, unit length, a sentence
closer to its translation than to an unrelated one) run when the model is
present. DenseIndex accepts another model's prompt forms.

R4.1 (pre-registered): BGE-M3 recall@5 0.53 (0.37 to 0.69) against BM25
0.24, paired +0.288 (interval +0.086 to +0.484); biggest gains on questions
that share few words with their answer and on lookups. R2: reciprocal rank
fusion of BM25 with BGE-M3 lowers recall@5 to 0.43, so it is not adopted and
the weighted variant is not run, per the pre-registered rule.

The hosted embedding run was stopped after it made no progress for 30
minutes (free-tier throttling); its 640 vectors are kept. Decisions 74 to 77,
README instructions for the optional extra, results and readings in
docs/EXPERIMENTS.md.

### 25. `2facbe9` Repeat R3, R8 and R10 with BGE-M3; add cross-language and rank-depth diagnostics

R3 with BGE-M3 (pre-registered, 31 development questions): leaving the
context line out of the embedded text lowers recall@5 from 0.53 to 0.37
(paired difference -0.161, interval -0.315 to -0.016), the first
detectable effect in Phase 3, so the line stays; no chunk cap beats 400
detectably (cap 200 +0.040, interval -0.089 to +0.177).

R8 and R10 repeated with BGE-M3: version policies and collapsing duplicate
copies change recall@5 by -0.008 to -0.024, every interval including 0;
nothing is adopted. The failures are about ranking, not about crowding.

Cross-language breakdown (three development questions): BM25 0 of 3,
BGE-M3 finds two. Rank-depth diagnostic: 44 % of the required provisions
are in BGE-M3's top 5, 65 % in the top 30 and 89 % in the top 100, which
caps what a reranker over the top 30 could add at about 21 points.

The R8/R10 script takes --model bm25|bge. Adds decisions 78 to 81 and the
readings in docs/EXPERIMENTS.md and docs/JOURNEY.md.

### 26. `3f9c7a2` Add the reranker (R5) and question rewriting (R6); document the why

R5: BAAI/bge-reranker-v2-m3 over BGE-M3's top 30/50 gives no detectable
gain (recall@5 0.52/0.53 vs 0.53) and is 32-49 times slower; not adopted.
A diagnostic rules out the 512-token cut as the cause.
R6: rewrites made by a separate agent that saw only the question texts
raise recall@5 from 0.53 to 0.68 (rewrite alone) and 0.70 (question plus
rewrite), paired intervals above 0; carried forward as the working
candidate, to be confirmed once on the test half.
Adds rerank.py, get_reranker.py, rewrite.py, the stored dev rewrites,
tests, the experiment scripts, decisions 82-83 and the dossier updates.

### 27. `ec0c219` Add the answer layer, Gemini client and rewriter experiments; document the why

Phase 4: understand/route/table/search/write/verify pipeline with
quotations checked in code, model judge, LangGraph wiring (optional).
Dev half: routing 40/40, refusals 5/5, figures 4/4; correctness 0.68 vs
0.63 from memory (not detectable), so no accuracy gain is claimed.
R6.3-R6.7: cheap in-pipeline rewriters give +0.03..+0.11, none
detectable; not adopted. Version-aware search built, not yet measured.
Both Gemini clients now stop at once on long quota waits.
Docs: answer-layer explainer, roadmap, journey, readings, decisions 84-91.

### 28. `b1e34db` Add filters experiment, service layer, web page and deployment notes

R6 filters: jurisdiction and language filters change the top five for
9-17 of 31 questions but not recall@5; none adopted.
Phase 5 groundwork: service layer (limits, error hiding, per-question
trace), standard-library web server and one-page interface, command-line
ask, factory for the real pipeline, serving index that keeps question
vectors in memory, Dockerfile (not yet built). LangGraph state fixed.
Docs: DEPLOYMENT.md, decisions 92-95, journey, roadmap, README.

### 29. `4f65e8f` Second gold review (version 2), R7 vector stores, Spanish diagnostic, Phase 5 plan

Gold v2: ten questions and one table caveat corrected after five blind AI
reviewer passes, each finding verified against the corpus; v1 fingerprint
kept in the manifest; development recall@5/MRR unchanged.
R7: NumPy scan 0.7 ms vs 113 ms for the loop with identical results;
default in DenseIndex; no library or database adopted.
Spanish diagnostic: no explanation holds; probably no real language gap.
Answer writer can show each passage's in-force date (off by default).
Phase 5: trace retention, quota-aware 503, trace report, page privacy
warning, PHASE5_PLAN.md, decisions 96-100.

### 30. `cfc1984` Add the documentation set and pre-register the test-half retrieval confirmation

Docs: INDEX (map and tracking protocol), RAG_PLAYBOOK (general guide to
building RAG tools), GLOSSARY, EXPERIMENT_INDEX, CHRONOLOGY (generated by
scripts/make_chronology.py). T1 retrieval confirmation script with its
pre-registration and a guard against a second read of the test half.

### 31. `39e9e0e` Log T1 (retriever confirmed on the test half); pre-register the answer-layer confirmation

T1: BGE-M3 recall@5 0.55 vs BM25 0.19 on the 31 unseen test questions,
paired +0.360 (+0.204 to +0.527); decision 101. P4.6 script with its rule
for choosing the configuration and a guard against a second read.
Dockerfile: pin transformers (<5.20) and fail the build on an import
error; the first image started with a version mismatch.

### 32. `91dd3f1` Build and run the container; document the results and the remaining measurements

The first image crashed at start-up (transformers 5.20 needs a newer PyTorch
than the pinned CPU build); fixed with a bound and a build-time import check.
Rebuilt: 1.74 GB, healthy in 10 s, 1.5 GiB at rest, page, /health and the
503 path verified. Decision 102, playbook and journey lessons, interview
Q81-83, ROADMAP lists the exact commands for the three measurements that
wait for the model's daily allowance.

### 35. `a8851ac` Log R4.2 (second embedding model not adopted), degraded mode, page, CI smoke test

R4.2: Qwen3-Embedding-0.6B recall@5 0.47 vs BGE-M3 0.53 (paired -0.065,
-0.202 to +0.073); fusion 0.58 not detectable; BGE-M3 stays (decision 107).
P4.7 degraded mode measured with every model call failing (decision 103).
Docs: decisions 103-107, journey, playbook, glossary, experiment index,
interview questions, chronology; README and DEPLOYMENT notes updated.

### 36. `03eedb6` Add bilingual privacy notice, hourly trace pruning, accessibility checklist; log P4.5 (variant D not adopted)

- web/privacy.html at /privacy, linked from the page; tests tie retention, trace fields and placeholders to the code
- TraceLog deletes old rows itself (first write, then hourly), not only at start-up
- start-up warning while the notice has owner placeholders; smoke test checks /privacy
- docs/ACCESSIBILITY_CHECKLIST.md; lawyer's review dropped from plans (label kept)
- P4.5 result: variant D equals A (0.68 vs 0.68), pre-registered rule fails, A stays (decisions 108 to 111)

### 37. `d45cf1b` Fill the privacy notice with the owner's details; put the lawyer's review back on the list

- notice names the owner, Glasgow (UK), a contact address and Microsoft Azure as planned host; UK GDPR and ICO first
- open points flagged as unchecked: host/region, ICO fee, EU representative
- decisions 112 (lawyer's review reinstated) and 113; tests updated

### 38. `4d94b57` Log P4.6: the answer layer on the sealed test half did not beat memory

- correctness 0.52 against 0.76 for memory, paired -0.242 (-0.387 to -0.097); equal (0.80) on the 20 answered
- routing did not generalise: refusals 2/5, figures 2/4 (case law, enforcement and adequacy questions not recognised; one wrong fine tier)
- claim restated (decision 114); router and picker not changed on the test half (decision 115)
- README, experiment index, journey, roadmap and glossary updated

### 40. `ce80ad0` Add deploy prep and routing-fix candidates: cold-start notice, data bundle, deploy workflow, batch C

- Page: after 4 s without an answer the status line says the assistant may be waking up (EN/ES); the footer carries each publisher's required credit line in both languages.
- NOTICE carries the credit lines for EUR-Lex, legislation.gov.uk and the BOE (decision 119).
- scripts/make_data_bundle.py packs the git-ignored chunks, BGE-M3 vectors and NOTICE for CI; manual keyless deploy workflow (not yet run).
- Router V2, picker V2 and a GDPR fine-tier scope overlay as options; defaults unchanged (decision 116).
- Batch C: 37 frozen unseen routing questions (decision 117); the C1 comparison is pre-registered and was stopped by the free model quota.
- Docs: decisions 116-120 (ICO fee and EU representative findings, owner decision pending), JOURNEY, DEPLOYMENT (free-tier terms, hosting options, owner steps), README, EXPERIMENT_INDEX.
