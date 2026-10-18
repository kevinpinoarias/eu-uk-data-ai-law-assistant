# How the answer layer works, step by step (in plain words)

Retrieval (see `HOW_RETRIEVAL_WORKS.md`) finds passages of law. The **answer layer** is everything that happens around that search so that a person gets a short, sourced answer, or an honest "I won't answer that". Each step below has the same three parts: **in this project** (what it is here), **in general** (the idea, anywhere), and **the basics applied** (real numbers from our own runs). All numbers are for the 40 *development* questions; the 40 *test* questions have not been read.

## The big idea: why not just ask the language model?

**In general.** A language model (LLM) writes fluent text from patterns it learned in training. Two problems for law: it may state something wrong in a confident voice, and it knows nothing newer than its training (here, a 2025 UK Act and a 2026 amendment to the EU AI Act). **Retrieval-augmented generation (RAG)** fixes both by searching a trusted text first and telling the model to answer *only from what was found*. The remaining risk is that the model still strays, so a careful system also **checks** the answer instead of trusting it.

**In this project.** The model is `gemini-3.1-flash-lite`. It writes the answer from five numbered passages. Plain code, not the model, decides whether to answer, looks up exact figures, checks every quotation and refuses what must not be answered.

**The basics applied.** The pipeline has these boxes in this order: understand, route, (look up a figure | refuse | retrieve, write, verify), and finish. The same boxes are drawn as a LangGraph graph in `answer/graph.py` (LangGraph 1.2.15) and tested against the plain loop: both give identical results on an answer, a table figure and a refusal.

```
question -> [1 understand] -> [2 route] --refuse--------------------------------> refusal
                                 |--table--> [3 look up a row] --found--------> the figure, cited
                                 |                 \--- no row ---+
                                 \--retrieve ---------------------+
                                         [4 search] -> [5 write] -> [6 check quotes] -> answer, or "not enough"
```

## Step 1: understand the question (`answer/understand.py`)

**In this project.** Read three things from the question text: its language (English or Spanish), which jurisdictions it names (EU, UK, Spain) and whether it states a date ("the start of 2026"), and also whether it asks about the wording "as first published".
**In general.** Before spending money on a model, cheap rules can read obvious features. Rules are free, instant and explainable; they fail on anything unusual.
**The basics applied.** Language right on 40 of 40 questions; jurisdictions exactly right on 35 of 40 (the five misses are listed in `EXPERIMENTS.md`); the one question with a written date was read correctly. Caveat: I wrote the rules knowing what the development labels look like, so the test half is the real check.

## Step 2: route the question (`answer/router.py`)

**In this project.** Three outcomes. *Retrieve*: look the answer up in the law. *Table*: the question wants one exact figure (a fine ceiling, a deadline, an age), which is answered from a small hand-checked table so it cannot be mis-copied from prose. *Refuse*: the question is about another country's law or a regulator's guidance (outside our texts), or asks for advice on the user's own situation or a document written for them.
**In general.** "Routing" sends each request to the right tool. It matters twice: using the wrong tool gives a wrong answer, and not refusing what you should refuse is a safety failure.
**The basics applied.** Two routers were compared. Rules (readable patterns) got 39 of 40 right; a model given the definitions got 40 of 40. Neither refused a question it should have answered, and both caught all 5 refusals with the right reason. Only 5 refusals and 4 table questions are in the development half, so I treat this as encouraging, not proven.

## Step 2b: find the table row (`answer/facts_lookup.py`)

**In this project.** The table has 19 rows, such as "GDPR fine ceiling, upper tier". For a figure question we need *which row*.
**In general.** Matching a question to a short list can use similarity (the same embeddings as search) or a model that reads the list. Similarity is cheap but confuses near neighbours; a model reads the options.
**The basics applied.** Embedding similarity found the right row for 3 of 4 (it mixed up "deadline to answer a rights request" with "deadline to report a breach"). The model picker got 4 of 4, but it also offered a row for 3 of 36 questions that are not figure questions; that broke my own pre-registered limit of one, so it is used only *after* the router, and end to end no ordinary question was answered from the table.

## Step 3: search (the Phase 3 retriever, plus version choice)

**In this project.** BGE-M3 search over the 3,831 chunks, returning five passages, with copies of one provision (two languages, two versions) collapsed. Which *version* of the text to search depends on the question: the current consolidated text by default; the text as first published, without the 2026 amending regulation, for a question dated before 27 July 2026; every version for a question about the original wording. (The last two rules are built and unit-tested but **not yet measured**, see below.)
**In general.** Law changes. Offering today's text to a question about last year, or an amendment to a question that predates it, is a wrong answer even if the text is real.
**The basics applied.** Eight passages instead of five changed correctness by +0.016 (interval -0.065 to +0.113): nothing detectable, so five stays. The version rules came from reading two failures: q044 ("as of the start of 2026") was answered with the dates from the July 2026 amendment, and q048 (the wording "as first published") was searched in the current text only.

## Step 4: write the answer (`answer/generate.py`)

**In this project.** One model call. The model gets the question, the language to answer in, the date the question is about, and five numbered passages. It must answer only from them, in at most 150 words, say if they are not enough, and support the answer with **quotations copied exactly**, each tied to a passage number. It replies in a fixed JSON shape so the code can read it.
**In general.** "Grounding" is forcing an answer to rest on supplied evidence. Asking for exact quotations makes grounding *checkable*.
**The basics applied.** The labels that say which law, provision and version an answer used ("GDPR, Article 6 (consolidated text of 4 May 2016)") are written by code from the chunk's own fields, never by the model.

## Step 5: check the answer in code (`answer/verify.py`)

**In this project.** For every quotation: the passage number must be one the model was given, and the quotation must really appear in that passage (ignoring capital letters, line breaks and curly quotes; "..." may skip words but the pieces must appear in order). A bad quotation is dropped. If no valid quotation is left, **no answer is shown**; the user gets "I couldn't find enough in the texts I hold".
**In general.** Do not ask a model whether it was right; check what can be checked with ordinary code. It is exact, free, and cannot be talked round.
**The basics applied.** Of the 31 retrieve questions, 25 were answered and 6 declined (about one in five); every quotation in the 25 exists in the text. The check cannot tell whether a claim *follows from* its quotation: a model judge scored the support of the claims by their quotations at 0.86 on average (1 means fully supported), so some claims go a little beyond them.

## Step 6: refuse and decline

**In this project.** Fixed, polite messages in the user's language: "outside the texts I hold" (another country's law, a regulator's guide) and "I can explain what the law says, but I can't judge your own situation, check your compliance or draft documents for you". Every answer ends with "this explains what the text says; it is not legal advice".
**Changed on 18 October 2026 (decision 124).** The live service no longer refuses the second kind (a question about the user's own situation). It searches and answers in general terms, never deciding the case, with every quotation still checked, and shows a notice above the answer: general information, not legal advice, see a qualified lawyer or your data-protection authority. For these questions the model first restates the question as a general one in the law's own vocabulary and the search uses both, because the person's own words found the wrong articles. The refusal of other countries' law, case law, enforcement decisions and guidance is unchanged. This is unmeasured; `--refuse-advice` and the library default keep the earlier refusal so the earlier numbers below still describe what was measured.
**In general.** A system that always answers is unsafe in law. Declining is a feature, and it must be tested like one.
**The basics applied.** 5 of 5 development refusals refused with the right reason, no retrieve question refused. **On the sealed test half this did not hold**: 2 of 5 refusals had the right reason, because the router's definition of out-of-scope never named case law, enforcement decisions or adequacy lists (the three misses ended as "not enough evidence", not as invented answers), and one Spanish question about work messages on holiday was refused as legal advice by mistake (experiment P4.6, decisions 114 and 115).

## Measuring it honestly

**In this project.** Three kinds of evidence: *code* (routing, rows, citations, refusals can be counted exactly), a *model judge* (does the answer say what the expert's reference answer says? are its claims supported by its quotations?) and *a person* (I read 12 of the judge's verdicts, as an AI assistant, not a lawyer). A baseline answers the same questions from the model's memory with no search.
**In general.** A judge that is the same kind of model as the writer tends to be generous, so a sample must be read by someone else and the agreement reported.
**The basics applied.**

| | 5 passages | 8 passages | 5 passages + blind rewrites (upper bound) | memory only |
|---|---|---|---|---|
| judged correctness | 0.68 | 0.69 | 0.79 | 0.63 |

The differences are small compared with the noise of 31 questions: the 95 % interval of "5 passages minus memory" is -0.10 to +0.18. I read 12 verdicts and disagreed with the judge on 2, both times because it was too generous, so every correctness figure is probably a little high, the baseline's too.

**What this does and does not say.** It does **not** show that search makes the model more correct on these questions. It shows what the design adds on top: quotations proven to exist, labelled sources and versions, refusals, and texts newer than the model's memory (where the gap was largest: questions that depend on the date, 0.40 against 0.20, five questions). If a reader wants a headline accuracy gain, this project does not have one, and says so.

## What is still open

- **Version-aware search** (above) is built and tested but not measured: the free tier of the model allows 500 requests a day and the day's allowance was used up. It needs one more run, then the same questions' verdicts re-read.
- **The test half** (40 questions nobody has tuned on) is read once, for the chosen configuration. A full run is about 250 model calls.
- **The rewriting step** (see `EXPERIMENTS.md`, R6): a strong writer lifts search recall@5 from 0.53 to 0.70, but the cheap in-pipeline models did not show a detectable gain, so the live pipeline does not rewrite yet.
- **LangGraph** is wired in `answer/graph.py` as an optional extra and its tests pass. The first run failed because a plain `dict` cannot be the graph's state (LangGraph needs named keys it can merge), which the skipped test had been hiding; the state is now a typed dictionary.
- **Not legal advice and not lawyer-reviewed.** The gold answers were drafted by an AI assistant, checked by scripts and by AI reviews.

## Words used here

- **LLM**: a program that writes text. **Prompt**: what you send it. **System instruction**: standing rules sent with every prompt.
- **Grounded**: resting only on supplied evidence. **Citation / quotation**: the exact words and where they came from.
- **Abstain**: decline to answer because the evidence is not enough. **Refuse**: decline because the question must not be answered.
- **Judge**: a model that grades another model's answer. **Baseline**: the simplest alternative you must beat.
- **Free tier**: the no-cost allowance of an API, with daily limits (500 requests a day for this model).
