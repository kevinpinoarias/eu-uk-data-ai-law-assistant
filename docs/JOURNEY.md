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

## Phase 3, continued: a real embedding model

**The idea.** An embedding model turns text into a list of numbers so that similar meanings sit close together. A question like "name a person responsible for data protection" and an article that says "designate a data protection officer" then land near each other even though they share few words.
**Why a local model.** Google's hosted model has a free tier that slowed to a halt after a few hundred requests (its last save was 30 minutes old when we noticed), so we switched to an open model, BGE-M3, that runs on the project owner's own graphics card. It needs no key and no network once downloaded. It is optional: the tests, CI and keyword search do not need it.
**What it took.** Check the computer (a GTX 1060 card), choose a PyTorch version that still supports that older card and verify it works after installing, download only the needed files (2.27 GB), read the model's own pooling configuration instead of assuming it, and test the real model (right size, unit length, a sentence closer to its translation than to an unrelated one).
**What we found.**
- Embeddings find far more: recall@5 rose from 0.24 (keyword) to 0.53, a clear improvement even allowing for only 31 questions.
- They work across languages where keyword search scores zero (3 test cases: keyword 0 of 3, embeddings 2 of 3).
- **Mixing the two searches made things worse** (0.43), because the equal-weight merge lets the weak keyword list drag down the strong one. The plan's rule forbade tuning until it looked better, so the variant was recorded as a miss.
- Tidying the index (which version of a text to keep, merging duplicate copies, chunk sizes) still changes nothing detectable. The real remaining problem is ranking: a diagnostic shows only 44 % of required provisions sit in the top 5, 65 % in the top 30 and 89 % in the top 100.
**What that implies.** A reranker (a slower second-pass scorer) could at best lift provisions that are already in the top 30, so its gain is capped at about 21 points, and the provisions beyond rank 30 need a better first search (another model, or a rewritten question).

## Phase 3, continued: does a second look help? (R5, the reranker)

**The idea.** The first search compares a summary of the question with a summary of each chunk, which is fast but coarse. A **reranker** reads the question and one chunk *together* and gives that pair a score, which is sharper but slow: one model run per candidate. So it is used as a second pass over the first search's top 30 and re-orders them.
**Why we tried it, and what we checked first.** The rank-depth diagnostic (above) showed that a reranker can only reorder what the first search already retrieved, so it could add about 21 points at most. We asked your approval before downloading it (2.27 GB, Apache-2.0), tested it on the real card, and wrote the plan and decision rule before running it.
**What we found.**
- **No gain.** recall@5 was 0.52 (top 30) and 0.53 (top 50), against 0.53 without it; the paired difference was -0.011 with an interval of -0.151 to +0.129, so it could be a little better or a little worse, and there is no evidence it is better.
- **A lot slower.** 0.12 s per question without it, 3.83 s over the top 30, 5.91 s over the top 50 (32 to 49 times).
- **We checked the obvious excuse.** 28 % of the pairs were longer than the model's 512-token limit and got cut. If that were the cause, cut pairs would do worse. They did not (4 of 8 required provisions in the top 5 before and after), so the cut is not why it did not help. We do not know why; the honest entry is "not explained".
- **A reminder about expectations.** The plan said it would probably help. It did not. Writing the expectation down first is what lets us say so plainly. Decision 82: not adopted; the code stays as an optional experiment.

## Phase 3, continued: rewriting the question (R6)

**The idea.** People ask "do I need to name a person responsible for data protection?" and the law says "designate a data protection officer". A rewrite step turns the first into the second before searching, using a language model that knows the legal vocabulary. The model sees only the question, never the answers.
**Why it was tested this way.** The first draft of this idea was for you to rewrite the questions by hand. You know the gold answers, so your rewrites would drift toward the right articles and flatter the result. Instead a separate agent got only the 31 question texts (no gold set, no files, no tools) and a fixed set of instructions (same language, legal terms, no article numbers, at most 40 words). Its 31 rewrites were saved before anything was scored (`eval/rewrites/`).
**What we found.**
- recall@5 rose from 0.53 to 0.68 (rewrite alone) and 0.70 (question followed by the rewrite). Both gains are detectable: the paired intervals (+0.030 to +0.282 and +0.040 to +0.315) exclude 0. This is the first clear gain since switching to embeddings.
- hit@5 rose from 0.61 to 0.81: for four questions in five, at least one required provision is now in the top five.
- Two of our guesses were wrong: the gain was **not** bigger for the questions that share few words with the law (+0.09 against +0.23 for the ones that share many), and the date-dependent questions were not hurt.
- English questions gained far more (0.51 to 0.79) than Spanish ones (0.55 to 0.59).
**What it costs and what is still open.** In the final assistant this is one extra language-model call per question, whose time and price we have not measured. The 31 rewrites come from a strong model that knows a lot of law, so part of the gain is that knowledge. The result is on the development half only: rewrites for the test half will be made once, with the same instructions, when we confirm the whole pipeline. Decision 83.

## Phase 3, finished for now: can the rewrite step run inside the system? (R6.3 to R6.7)

**The idea.** The 0.70 came from rewrites written by a strong writer in one batch. The finished assistant must rewrite every *new* question by itself, with a cheap model it can call. So the same idea was tried with Google's smallest models (Gemini 3.1 and 3.5 Flash-Lite), once with a plain instruction and once with an instruction that also asks for the legal terms the provision would contain.
**What we found.** All four cheap rewriters raised recall@5 a little (0.56 to 0.64 against 0.53) but **none was detectable**: every lower bound is below zero (the best is -0.032). So the project does *not* claim the 0.70 for the system; it is an upper bound with a stronger writer. By my own rule I stopped tuning on the development half.
**What got in the way, and what it taught.** The larger Flash model allows only 20 requests a day on the free tier, so it could not be tested. The reply to the blocked request said "retry in 9 hours 28 minutes", and my code obediently slept: the run looked frozen for 11 minutes. Both Gemini clients now stop at once and say so. The same thing may be what happened to the first embedding run. Lesson: read an error's full text, and design for limits you do not control.

**One more cheap idea: filters.** If a question names the UK, why search EU text, and why search the Spanish copy of a law for an English question? Filters were tried (they need no model calls). They changed the top five for 9 to 17 of 31 questions but not the recall: even a filter using the gold labels left recall@5 at 0.53. So the missing provisions are not being pushed out by the wrong jurisdiction's text; they simply rank lower inside the right one. Decision 92: no filter.

## Phase 4: the answer layer, built and measured on the development half

**The idea.** Search finds passages; the answer layer turns them into a short, sourced answer, or an honest refusal. Its steps are explained from scratch in `HOW_THE_ANSWER_LAYER_WORKS.md`: read the question, route it (look up a figure, refuse, or search), write the answer from five numbered passages with exact quotations, **check every quotation in code**, and decline when nothing valid is left.
**Why it was built this way.** A language model is fluent whether or not it is right, so everything that can be done by ordinary code is: rules for the language and the jurisdiction, a small hand-checked table for exact figures, a quotation check that makes a fabricated citation impossible to show, labels for the law and the version written from the data and not by the model, and fixed refusal messages.
**What we found (40 development questions).**
- Routing: the model router sent 40 of 40 questions the right way, the rule router 39 of 40; all 5 refusals were refused with the right reason; all 4 figure questions got the right table row; no ordinary question was refused.
- Of the 31 ordinary questions, 25 were answered and 6 declined. The judged correctness was 0.68. Eight passages instead of five made no detectable difference (0.69).
- **The surprise.** The same model answering from memory with no search scored 0.63. The difference (+0.05) is well inside the noise (interval -0.10 to +0.18). So this design does **not** make answers detectably more *correct*. What it adds is what the memory answer cannot give: quotations proven to exist, named provisions and text versions, refusals, and knowledge newer than the model's training (where search helped most: the date-dependent questions, 0.40 against 0.20). That is the claim the project makes, and no more.
- **A person read the judge.** Of 12 verdicts I read, I agreed with 10; on the other two the judge was too generous. One of them showed a real flaw: asked about the law "as of the start of 2026", the system quoted the July 2026 amendment's dates as if they applied then.
- **A repair, written and tested but not yet measured.** For questions dated before the amendment, the system now searches the text as first published, without the amending regulation, and for questions about the original wording it searches every version. The measurement is waiting for the free tier's daily allowance (500 requests) to renew.

## Phase 5 groundwork: turning it into something a person can use

**The idea.** A pipeline you can only run from a terminal is not a product. Wrapping it in a service means deciding who may ask how often, what happens on bad input or an error, what is logged, and what the page says.
**Why it was built this way.** Every question costs model calls, so a public demo needs limits before it needs anything else: 6 questions a minute per visitor and 300 a day in total, a length limit, and a plain message when something fails (no internal details). Every question is logged without the visitor's address, because the log is the only way to see what people ask and why an answer failed, and the page tells the visitor so. The page itself is one file with no outside libraries, readable on a phone and in dark mode, and it states the legal disclaimer above the question box.
**What we found.** A question embeds in 0.12 s on an ordinary CPU, so the demo does not need a graphics card. Measuring it exposed a bug that only a server would hit: the search index rewrote its 51 MB vector file after every new question; serving now keeps new question vectors in memory only.
**What is left.** Billing, building and measuring the container image, a hosting account (see `DEPLOYMENT.md`).

## The first read of the sealed test half (T1)

**The idea.** All tuning used 40 development questions; the other 40 were kept sealed so that one final number could not be flattered by tuning. The retriever (BGE-M3, context line, no rewriting) was settled, so it was the first decision to earn its read. The plan, including the rule and the result I expected, was committed to git before the run, and the script refuses a second read.
**What we found.** On 31 unseen questions BGE-M3 reached recall@5 0.55 against 0.19 for keyword search (paired +0.360, interval +0.204 to +0.527). The development numbers were 0.53 and 0.24, so there is no sign that the choices were fitted to the development questions. English questions are where keyword search collapses (0.02): the words of an English lay question and of the law barely overlap.
**What it does not say.** Only the retriever was read. Rewriting, the answer layer and the date/version repairs are still unread on the test half; each gets one read, once the model's daily allowance allows.

## Building and running the container

**The idea.** A container is a sealed folder that runs the same everywhere. Writing the recipe (the Dockerfile) is not enough: you have to build it and run it.
**What we found.** The first build succeeded and the container then crashed at start-up: the newest `transformers` had been installed and it needed a newer PyTorch than the one pinned for the CPU image. Pinning it, and adding a check that imports the libraries during the build, fixed it. The rebuilt image is 1.74 GB, starts healthy in 10 seconds and uses 1.5 GiB of memory at rest, which is much less than I had estimated. Asked a question while the model's daily allowance was used up, it returned the plain "allowance used up" message and wrote a trace without any address.
**The lesson.** "It built" and "it runs" are different claims. Test the artefact you will ship.

## Does a vector database help? (R7)

**The idea.** A "vector database" is a place to keep the numbers that stand for each chunk and find the closest ones to a question. The question is whether one is needed at our size.
**What we found.** Five ways of finding the nearest vectors (the original Python loop, NumPy, FAISS exact, FAISS approximate, a SQLite database extension) return the same results, so the choice is about speed and convenience. On our 3,831 vectors the original loop took 113 ms, NumPy 0.7 ms and the others 0.2 to 7 ms; NumPy alone stays under 100 ms up to about half a million vectors. A "perfect-tie" subtlety taught us something: 3,831 chunks have only 3,300 distinct vectors (copies of one text), so equal scores can be listed in any order, which looked like a disagreement between methods and was not.
**What changed.** The search now uses NumPy when it is installed. No library or database is added; the honest answer to "does a vector store beat scanning?" is "not at this size". The size at which that changes, and the things a database adds beyond speed (storing the vectors in a file, filtering by metadata), are in `EXPERIMENTS.md`.

## A question about Spanish: why did rewriting help English more?

**The idea.** In the rewriting experiment English recall@5 rose from 0.51 to 0.79 and Spanish from 0.55 to 0.59. Before concluding that Spanish is somehow harder, we looked for a reason with no model calls.
**What we found.** I had guessed that Spanish questions need English-only UK law that a Spanish rewrite cannot match. It is the reverse: English questions need more of it (32 % against 12 %). Spanish questions did not start higher or get weaker rewrites either. On the required provisions, Spanish improves everywhere, only less, and with 14 questions the difference is within the noise. The one real language finding is that half the top five for a Spanish question are English copies of the same law until the rewrite pulls Spanish text up (50 % to 79 %).
**The lesson.** A striking contrast between two small groups is often not a finding. We wrote down three explanations, tested them, and all three failed; the right conclusion was "probably no real gap", not a fourth story.

## The second review of the gold set, and what it taught

**The idea.** The test only means something if its questions and labels are right. A first round of five independent AI reviewers had fixed 12 serious problems before the set was frozen. A second round, on the corrected set, was promised before anyone reads the sealed test questions.
**What it found.** Of 80 questions, 29 were fine, 48 had minor findings and 3 were flagged major. We checked every finding against the corpus before adopting any. The three "major" ones were not errors: they were "since when" dates that come from the chunks' date metadata, which the reviewers were not shown. A suspected parser bug turned out to be a 2018 corrigendum. About 25 label comments could not change any score, because a provision counts once if a chunk holds any of its pinpoint ids.
**What changed.** Ten questions and one table caveat: two acceptable labels that rewarded a text of the wrong date were removed, one provision was promoted, and seven expected answers lost an unsupported or wrong sentence, a garbled Spanish phrase, a wrong term or a language mix. This is gold version 2; development recall@5 and MRR are identical, nDCG@10 moved 0.002.
**The useful accident.** The "false alarms" pointed at a real hole in the system: the answer writer was never shown the in-force date, which is why two development questions were declined or judged incomplete. An option now shows it; it is measured with the version-aware search when the model's daily allowance allows (decision 98).
**The lesson.** An independent reviewer can only judge what it is shown. When a reviewer says "the date is not in the text", either the gold is wrong or the evidence the system uses is not what the reviewer saw; here it was the second, and it improved the system. Details: `GOLD_REVIEW_2.md`.

## Why each major choice, in one place

| Choice | Why | What showed it |
|---|---|---|
| Use seven laws, leave out the regulator's guides | Licence terms: the guides are non-commercial, which clashes with an open project | `SOURCES.md` |
| Official API and polite fetchers; never get past a bot check | The sites are public services; hiding who we are is rude and risky | EUR-Lex bot challenge, so the official API |
| Parse with checks that can fail | A parser fails quietly; a dropped article never complains | Annex VI body lost, 36 chunks of dots |
| Chunk by the law's structure, 400-word cap | A piece must mean something alone and be small enough to find precisely | 3,831 chunks, none over 400 words |
| Put a context line (law, chapter, article, title) in each chunk | It tells the embedding model what it is reading | Without it recall@5 falls from 0.53 to 0.37 |
| Write and freeze 80 gold questions before experimenting | A test written after the system flatters the system | Five blind reviewers found 12 serious problems in the draft |
| A table for exact figures | A model can misread or mis-copy a number | Every figure checked against its provision |
| recall@5 as the main score, with paired intervals | The answer-writing model sees about five chunks; 31 questions is few | `METRICS.md` |
| BGE-M3 on your own card, not Google's free tier | The free tier slowed to a stop after 640 of 3,304 vectors; the local model has no key, no limit, no cost | recall@5 0.24 (keyword) to 0.53 |
| No hybrid keyword + embedding merge | The equal-weight merge let the weak keyword list drag down the strong one | 0.43 against 0.53; the plan forbade tuning until it won |
| Keep all versions and do not collapse copies | Neither changed anything detectable | R8 and R10 with both searches |
| No reranker | No gain for 32 to 49 times the time | R5: 0.52 against 0.53 |
| A question-rewriting step (tried, not adopted) | The gap between everyday and legal wording was the main failure | A strong writer: 0.53 to 0.70. Cheap in-pipeline models: +0.03 to +0.11, none detectable |
| Check every quotation in code | A model's citations cannot be trusted; ordinary code can check them exactly | A fabricated or misplaced quotation cannot be shown; an answer with no valid quotation becomes a decline |
| Exact figures from a table, not from prose | A model can misread or mis-copy a number | 4 of 4 development figure questions answered from the right row |
| Refuse out-of-corpus and advice questions | Wrong or unsafe to answer; the corpus excludes regulators' guides | 5 of 5 development refusals right, no ordinary question refused |
| Do not claim better accuracy than memory | The measurement does not show it | 0.68 against 0.63, interval -0.10 to +0.18 |

## What the process has taught us so far

1. **Checks that can fail beat checks that cannot.** Every serious bug (a dropped annex, dotted "law", a wrong article in a gold answer) was found by a check or a review, not by looking.
2. **Write the plan and the decision rule before the result.** It stops us from picking the flattering number.
3. **A weak stage hides the effect of the stages after it.** BM25's 0.24 made three experiments uninformative; fixing retrieval first makes the rest measurable.
4. **Say what was and was not verified.** Model specifications were read from the official pages; sizes that the pages did not state are marked as unknown until checked.
5. **Keep the labels honest.** The gold set is not lawyer-reviewed, and every provisional result says so.
6. **Look where the failures are before choosing a fix.** The rank-depth diagnostic showed what a reranker can and cannot do before any reranker was downloaded.
7. **A rule that forbids tuning is worth having.** Fusion lost, and the plan did not let us hunt for weights until it won.
8. **A better tool in theory still has to win the measurement.** The reranker is standard practice and was a good bet; here it gave nothing and cost 32 times the time. We checked the obvious excuse (the cut) instead of assuming it.
9. **The wording of the question mattered more than the machinery.** Rewriting the question moved recall@5 by 17 points; chunk sizes, version policies, duplicate collapsing, fusion and a reranker together moved it by nothing detectable.
10. **Keep the person who knows the answers away from the test.** The rewrites came from an agent that saw only the questions, for the same reason the gold set was frozen first.
11. **A cheap model may not do what an expensive one did.** The rewrite gain (+0.17) did not carry over to a small model that could run in the system; saying "upper bound" and not "result" is the difference between a claim and a hope.
12. **The headline you hoped for may not be there.** Search did not make the answers detectably more correct than the model's memory. The honest write-up names what the design does add (checked quotations, versions, refusals) and does not claim the rest.
13. **Read the judge.** An automated grader is a measurement tool with its own errors; reading a sample found two it passed that it should not have, and one of them exposed a real bug in how versions of the law are chosen.
14. **Limits you do not control are part of the design.** A daily quota, an unexpected 9-hour wait, a model closed to new users: each cost time until the code failed fast and the plan allowed for it.

## Where we are now

Phases 0 to 2 are complete. Phase 3 measured keyword search (recall@5 0.24), BGE-M3 (0.53), fusion (worse), chunking and index variants (nothing detectable), a reranker (nothing), and question rewriting (0.70 with a strong writer, not shown with a cheap in-system model). Phase 4's answer layer is built, tested (about 540 automated tests) and measured on the development half. Still to do: measure the version-aware repair; read the 40 test questions once for the final configuration (about 250 model calls, so a day's allowance of the free tier or a paid key); a second embedding model and filters if time allows; the optional LangGraph install; and Phase 5 (a small web page, packaging and deployment). The gold set still needs its second independent review before the final write-up.
