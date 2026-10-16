# Roadmap

What is done, what comes next and what is deliberately not planned. Dates are 2026. For the reasoning behind each step see [JOURNEY.md](JOURNEY.md); for the numbers see [EXPERIMENTS.md](EXPERIMENTS.md).

## Done

| Phase | Result |
|---|---|
| 0. Sources and licences | Seven laws usable with conditions; the Spanish regulator's guides kept out (non-commercial licence). |
| 1. Ingestion and chunking | 14 documents fetched politely, parsed into provisions with checks that can fail, cut into 3,831 chunks (none over 400 words). |
| 2. Gold set and metrics | 80 bilingual questions, frozen with a fingerprint; 40 for development and 40 for one final test. A table of 19 exact figures. Metrics with paired bootstrap intervals. |
| 3. Retrieval experiments | Keyword 0.24 recall@5; embeddings (BGE-M3, local) 0.53; context line essential; fusion, reranker, chunk sizes, version policies and jurisdiction/language filters gave nothing detectable; a strong question-rewriter 0.70, cheap in-system rewriters not detectable. |
| 4. Answer layer (development half) | LangGraph wiring tested against the plain loop. Understand, route, exact-figure table, search, grounded answer, quotations checked in code, refusals and declines. Routing 40/40; 5/5 refusals; 4/4 figures; no detectable accuracy gain over the model's memory on the development half; on the sealed test half it was detectably worse (0.52 against 0.76, because it declines without checked evidence) and its routing of refusals and figures did not generalise (P4.6). Checked quotations and named versions are the benefit. |

## Next, in this order

**Done on 16 October 2026:** the version-aware repair was measured and not adopted (P4.5, decision 111), and the 40 test questions were read once for the answer layer (P4.6): it did not beat memory on accuracy (0.52 against 0.76), and its refusal and exact-figure routing did not hold on unseen questions (decisions 114 and 115). Still to do from that batch: time 20 different uncached questions through a rebuilt image and summarise with `python -m law_assistant.answer.trace_report`.

**Because of that result, the next measurable work is on the answer layer, on new unseen questions, not on the test half:**

1. **Write a third batch of gold questions** (a new gold version, with its own development/test discipline) that includes out-of-scope kinds the first set lacked (case law, enforcement decisions, adequacy decisions) and fine-tier questions, so a fix can be measured honestly.
2. **Candidate fixes, each pre-registered and measured on those new questions:** name case law, enforcement decisions and adequacy lists as out of corpus in the router; have the fact picker check the tier of a fine; and look at why ten retrieve questions were declined (retrieval missed, or the writer found the evidence insufficient).
3. **A lawyer's review of the gold set**, if one is willing. The second round of AI review is done (version 2, `GOLD_REVIEW_2.md`).
4. **Phase 5, shipping.** Built: a service layer with a rate limit and a trace of every question, a web server and a bilingual one-page interface (checked in a browser), a privacy notice in both languages (owner details filled in; the server would warn if a placeholder came back), a command-line question, and a container image (built and run). Left: billing and a budget alert, rebuilding the image, a hosting account, a deployment workflow, and a screen-reader pass ([ACCESSIBILITY_CHECKLIST.md](ACCESSIBILITY_CHECKLIST.md)). The full plan, step by step, is in [PHASE5_PLAN.md](PHASE5_PLAN.md); measurements and the open choice of embedding source are in [DEPLOYMENT.md](DEPLOYMENT.md).

## If time allows

- The fusion of BGE-M3 and Qwen3-Embedding (R4.2: 0.58 against 0.53, not detectable) as its own pre-registered decision with its own test read, if the retrieval ceiling matters more than doubling the models per question.
- A larger Gemini Flash model as the question rewriter and as the answer writer (needs a paid key; the free tier allows 20 requests a day for it).
- An open answer model for comparison.
- More cross-language test questions (the development half has three).

## Not planned

- Regulator guidance, case law and enforcement decisions (later tiers of the corpus; see `SOURCES.md`).
- Legal advice, document drafting or compliance checks: the assistant refuses these by design.
- Training or fine-tuning a model.

## Known limits

- The gold set was drafted by an AI assistant, checked by scripts and AI reviews, and has **not been reviewed by a lawyer**. A lawyer's review stays on the list (decision 112); until it happens, the label stays on the set, the page and the write-ups.
- All results so far are on the 31 development retrieval questions, so only large differences are detectable.
- The judge that grades answers is a language model of the same family as the writer; a person read a sample of 12 verdicts and found it too generous on two.
- The free tier of the answer model limits how many experiments can run in a day.
