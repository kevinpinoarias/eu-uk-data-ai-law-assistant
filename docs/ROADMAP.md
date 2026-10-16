# Roadmap

What is done, what comes next and what is deliberately not planned. Dates are 2026. For the reasoning behind each step see [JOURNEY.md](JOURNEY.md); for the numbers see [EXPERIMENTS.md](EXPERIMENTS.md).

## Done

| Phase | Result |
|---|---|
| 0. Sources and licences | Seven laws usable with conditions; the Spanish regulator's guides kept out (non-commercial licence). |
| 1. Ingestion and chunking | 14 documents fetched politely, parsed into provisions with checks that can fail, cut into 3,831 chunks (none over 400 words). |
| 2. Gold set and metrics | 80 bilingual questions, frozen with a fingerprint; 40 for development and 40 for one final test. A table of 19 exact figures. Metrics with paired bootstrap intervals. |
| 3. Retrieval experiments | Keyword 0.24 recall@5; embeddings (BGE-M3, local) 0.53; context line essential; fusion, reranker, chunk sizes, version policies and jurisdiction/language filters gave nothing detectable; a strong question-rewriter 0.70, cheap in-system rewriters not detectable. |
| 4. Answer layer (development half) | LangGraph wiring tested against the plain loop. Understand, route, exact-figure table, search, grounded answer, quotations checked in code, refusals and declines. Routing 40/40; 5/5 refusals; 4/4 figures; no detectable accuracy gain over the model's memory; checked quotations and named versions are the benefit. |

## Next, in this order

**The exact commands for the three measurements that wait for the cheap model's daily allowance (about 500 requests; resets once a day) or a paid key.** Run them in this order, on a day with at least 350 requests available; each caches its answers, so an interrupted run resumes:

1. `python experiments/p4_version_aware.py --log` (finishes variant D; about 90 calls). Then apply the rule written in `experiments/p4_test_confirmation.py` to choose A or D.
2. `python experiments/p4_test_confirmation.py --config A --log` (or `--config D`): the one read of the test half for the answer layer, about 200 calls; it refuses a second read.
3. Build the image (done) and time 20 different uncached questions through it, then summarise with `python -m law_assistant.answer.trace_report`.

Then update `EXPERIMENT_INDEX.md`, the README results table and `DECISIONS.md`, and regenerate `CHRONOLOGY.md`.

1. **Measure version-aware search and in-force dates** (text as first published for questions dated before the 2026 amendment; each passage's 'in force from' date shown to the writer). Built and unit-tested; the measurement needs one day's allowance of the model's free tier, and the answer-layer results must be re-run under gold version 2.
2. **Read the 40 test questions once**, for the chosen configuration, against the baselines. About 250 model calls. Whatever comes out is reported, including a failure.
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
