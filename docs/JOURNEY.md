# How this was built, and why (in plain words)

A walk through every step so far, written so that someone new to retrieval and to law can follow it. Each step has the same three parts: **the idea** (what it is, in general), **why we did it** (what would go wrong without it), and **what we found** (including the surprises). The numbers are from the project's own logs; the detail is in the other files in `docs/`.

## The big picture

The goal is an assistant that answers questions about EU, Spanish and UK data-protection and AI law, in English or Spanish, and shows exactly which provision each answer comes from. The honest way to build it is as a pipeline in which every stage can be checked on its own:

```
fetch the laws -> parse them into pieces -> cut the pieces into chunks -> search the chunks -> answer with citations
 (Phase 1)         (Phase 1)                 (Phase 1)                    (Phase 3)             (Phase 4)
                                                        measured against a frozen set of questions (Phase 2)
```

The rule behind everything: **never trust a stage because it looks right; test it against something that can say it is wrong.**

## Phase 0: knowing what we may use

**The idea.** Laws are not all free to reuse in the same way. Each publisher sets terms (credit lines, no distortion, non-commercial only, and so on).
**Why.** Building on text we may not reuse could force us to take the project down later, and some terms (a non-commercial licence on the Spanish regulator's guides) would clash with our own open licence.
**What we found.** Seven laws are usable with conditions (the GDPR, the AI Act and its 2026 amendment, the UK GDPR, the UK Data Protection Act 2018, the new UK Data (Use and Access) Act 2025, and Spain's data-protection law). The regulator's guides were kept out. Facts such as the amendment's date were checked at the source and not guessed. (`SOURCES.md`, `DECISIONS.md`)

## Phase 1.1 to 1.3: fetching politely

**The idea.** A fetcher is a program that downloads the documents. Websites allow this on conditions: say who you are, follow the site's robots file, wait between requests, and never get past a bot check.
**Why.** The sites are public services; hammering them or hiding who we are would be rude and could get us blocked. One of them (EUR-Lex) answers scripts with a bot challenge, which we do not bypass, so we use the publisher's official API instead.
**What we found.** 14 documents downloaded, each with a record of where it came from, when, its fingerprint and its licence (so any answer can be traced back to its source file).

## Phase 1.4: parsing, the hardest step

**The idea.** The downloaded files are web or XML pages. Parsing turns them into a clean list of small labelled pieces, called provisions (a recital, an article's text, a numbered paragraph, a lettered point). Each gets an id such as `eu-gdpr/art-6/1/f`, meaning GDPR, Article 6, paragraph 1, point (f).
**Why.** Everything after depends on this being right, and a parser fails quietly: if it drops an article, nothing complains.
**How we kept it honest.** Before trusting any parse we made it pass checks that can fail:
- ids are unique and numbering has no gaps (a missing Article 47 would show);
- the totals match the known ones (99 GDPR articles, 173 recitals);
- English and Spanish have the same skeleton;
- the letters and digits kept add up to those in the source (coverage);
- the consolidated text matches the original Official Journal text except where an amendment explains the difference.
**What we found.** The checks caught real problems: Spanish Article 4 uses a different layout from the English one, an annex of the AI Act had silently lost its body (coverage 99.87 % had looked like rounding), and the UK files showed omitted law as lines of dots, which had become 36 meaningless chunks. Each became a test. (`PARSING.md`)

## Phase 1.5: chunking

**The idea.** A chunk is the piece of text the search will find and return. A single provision is too small to mean anything ("(f) legitimate interests" needs Article 6(1) around it) and a whole schedule is too big to search precisely.
**Why.** The size and shape of the chunk decides what the search can find. We cut along the law's own structure (an article, or its paragraphs when it is long), put the numbering back, and prefix a context line ("GDPR | Chapter II | Article 6: Lawfulness of processing").
**What we found.** 3,831 chunks, none over 400 words, nothing lost, and 400 recorded as a starting guess, not a result. (`CHUNKING.md`)

## Phase 2: the scoreboard (the gold set)

**The idea.** To know whether the search is any good you need questions whose right answers a person wrote down in advance. This is the gold set.
**Why before the experiments.** If you write the test after building the system, you write questions it already handles and the score flatters you.
**How.** 80 questions, half English and half Spanish, in lay wording (most users do not quote article numbers), including questions that must be refused, questions with exact figures (answered from a table, not by reading prose), questions whose answer depends on the date, and questions that compare the EU and the UK. Every cited article, paragraph and quotation is checked by script to exist in our text, and no question may copy its own answer's wording. Five independent AI reviewers then read them blind and found 12 serious problems in the first draft, such as a question built on a false premise and a legal term defined too broadly; each was verified and fixed. The set was then split 40 for tuning and 40 for a single final test, and **frozen**: a fingerprint in a manifest changes if anyone edits it, and a test fails on any edit. (`GOLD_SET.md`)
**The honest label.** Drafted by an AI assistant, checked by scripts and reviewed by AI passes; **not reviewed by a lawyer.**

## Phase 2: the table of exact facts

**The idea.** A language model reading prose can misread or mis-copy a number. For figures that must be exact (a fine ceiling, a deadline, an age, an application date), we keep a small table where each row cites its source.
**Why.** "What is the biggest fine?" should return the same verified number every time. A script proves every number and date in a row appears in the provision it cites, and a deliberately corrupted number is caught. (`FACTS.md`)

## Phase 2: measuring retrieval

**The idea.** Retrieval returns a ranked list. We score the list with four numbers: **hit@k** (is a right answer anywhere in the first k?), **recall@k** (what share of the needed provisions is in the first k?), **MRR** (how near the top is the first right answer?), **nDCG** (how good is the whole ordering?). Because only 31 questions are used for tuning, every score carries an interval, and two variants are compared on the same questions so noise cancels.
**Why.** "It feels better" is not evidence. Each right answer is credited once, because our index holds several copies of each article (two languages, two versions), and counting every copy would reward duplicates. (`METRICS.md`)

## Phase 3: the first experiments

**Plan before results.** Before any run, the plan, the main score (recall@5, what the answer-writing model will see), and the rule (adopt a variant only if its improvement is clearly bigger than the noise) were written down. About 25 variants will be tried and every one counted. (`PHASE3_PLAN.md`)

**Step 3.0 and R1: keyword search (BM25).** BM25 scores a chunk by how many of the question's words it contains, with rare words counting more. It needs no model.
**Result.** recall@5 = 0.24: it finds a quarter of what a question needs. Looking at why: the question "name a person responsible for data protection" never matches the article that says "designate a data protection officer", which ranks 724th of 3,831. Keyword search sees letters, not meaning; it cannot cross languages; and copies of an article use up slots. (`EXPERIMENTS.md`, `HOW_RETRIEVAL_WORKS.md`)

**R8, R10, R3 (with BM25): versions, duplicates, chunk size.** Nothing moved: none of the variants improved the baseline detectably. **The lesson:** if the search rarely finds the right article at all, tidying slots, versions or chunk sizes cannot show much. These questions are repeated once a better search exists; the BM25 versions are marked provisional.

**Embeddings (R1.3) in progress.** An embedding model turns text into a list of numbers so that similar meanings land near each other. It should fix the vocabulary gap. We built the client, the cache and the search test first, against a fake network; checked on real data that asking Google for 768 numbers matches cutting its 3,072 down; and found that the free tier limits sustained speed, so the client now waits properly after a "slow down" reply. Identical chunks share one stored vector. The first full run is slow but costs nothing.

**R2: hybrid search.** The code for merging two ranked lists by place (reciprocal rank fusion) is written and tested; the experiment runs when vectors exist.

## What the process has taught us so far

1. **Checks that can fail beat checks that cannot.** Every serious bug (a dropped annex, dotted "law", a wrong article in a gold answer) was found by a check or a review, not by looking.
2. **Write the plan and the decision rule before the result.** It stops us from picking the flattering number.
3. **A weak stage hides the effect of the stages after it.** BM25's 0.24 made three experiments uninformative; fixing retrieval first makes the rest measurable.
4. **Say what was and was not verified.** Model specifications were read from the official pages; sizes that the pages did not state are marked as unknown until checked.
5. **Keep the labels honest.** The gold set is not lawyer-reviewed, and every provisional result says so.

## Where we are now

Phases 0 to 2 are complete and committed. Phase 3 has its harness, a keyword baseline, three provisional BM25 experiments and the code for embeddings and fusion. The embedding run and the open-model option are the next steps; the answer layer is planned in `PHASE4_PLAN.md`.
