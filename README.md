# EU / UK Data and AI Law Assistant

A bilingual (English and Spanish) retrieval-augmented assistant for EU, Spanish and UK data-protection and AI law. It aims to answer questions with verified citations, say when it does not know, and measure every design choice instead of assuming it.

> **Status: building (October 2026).** Fetching, parsing, chunking, the frozen 80-question gold set, the facts table, the metrics, the retrieval experiments and a first answer layer are built and measured on the development half. The 40 test questions have not been read yet; that confirmation is the next milestone. For a plain-words walk through every step and why it was taken, see [docs/JOURNEY.md](docs/JOURNEY.md); for the answer layer, [docs/HOW_THE_ANSWER_LAYER_WORKS.md](docs/HOW_THE_ANSWER_LAYER_WORKS.md). It is not legal advice.

> **Where to start:** [docs/INDEX.md](docs/INDEX.md) is the map of every document and how to track the project; [docs/RAG_PLAYBOOK.md](docs/RAG_PLAYBOOK.md) is a step-by-step guide to building a RAG tool using this project as the worked example; [docs/EXPERIMENT_INDEX.md](docs/EXPERIMENT_INDEX.md) lists every experiment with its result and decision; [docs/GLOSSARY.md](docs/GLOSSARY.md) explains every term.

## Why this project

An earlier project of mine, a hospitality demand-forecasting system with a live chat assistant, answers numeric questions by tool-calling against structured data, because a model that retrieves a passage and paraphrases it can get a number wrong. The opposite case is unstructured prose with no schema, such as legislation, where semantic retrieval is the right fit. This project tests that reasoning on a corpus large enough to matter, and measures it.

What makes the problem interesting:

- **Three jurisdictions, two languages.** EU, Spanish and UK law, in English and Spanish, including questions that compare the EU and the UK.
- **Law changes.** Amendments and commencement dates mean an answer must say which version it used.
- **Citations must be checkable.** Every answer cites its source, and the citation is verified in code.
- **Knowing when not to answer.** Out-of-scope questions and requests for legal advice are refused.

## What has been measured so far

All numbers are on the 31 retrieval questions (or 40 questions in all) of the **development** half of the frozen gold set, with 95 % intervals in the experiment log, except where a row says it is the sealed test half (read once, for the retriever only). The gold set (version 2, after two rounds of independent AI review, see [docs/GOLD_REVIEW_2.md](docs/GOLD_REVIEW_2.md)) was drafted by an AI assistant, checked by scripts and AI reviews, and is **not lawyer-reviewed**.

| Question | Result |
|---|---|
| How well does keyword search (BM25) find the right provision? | recall@5 0.24 |
| An open embedding model (BGE-M3, run locally)? | recall@5 **0.53**, a detectable gain over keyword search |
| Is a second open embedding model (Qwen3-Embedding-0.6B) better than BGE-M3, alone or fused? | No: 0.47 against 0.53 alone; the fusion 0.58 is not detectably better, so BGE-M3 stays |
| Does merging keyword and embedding search help? A reranker? Other chunk sizes, version policies, duplicate collapsing? | No detectable gain from any (the merge was worse); the reranker was 32 times slower for no gain |
| Does BGE-M3 still beat keyword search on questions never tuned on (the sealed test half, read once)? | **Yes: recall@5 0.55 against 0.19**, paired +0.360 (+0.204 to +0.527) |
| Does the context line (law, chapter, article) in each chunk matter? | Yes: without it recall@5 falls from 0.53 to 0.37 |
| Does rewriting the question in legal vocabulary help? | A strong writer: 0.53 to 0.70. Cheap in-system models: +0.03 to +0.11, not detectable, so not adopted |
| Does a vector library or database beat a plain scan of the vectors? | No, at 3,831 chunks: identical results; NumPy takes 0.7 ms against 113 ms for the original loop, and a library only matters beyond a few hundred thousand chunks |
| Does the answer layer route correctly? | 40 of 40 questions routed right, 5 of 5 refusals, 4 of 4 exact figures from the right table row |
| Is the answer layer more *correct* than the same model answering from memory? | **Not detectably** (0.68 against 0.63). Its value is checked quotations, named sources and versions, and refusals, not a measured accuracy gain |

Everything is pre-registered and logged in [docs/EXPERIMENTS.md](docs/EXPERIMENTS.md), including the experiments that failed; the reasons behind each choice are in [docs/DECISIONS.md](docs/DECISIONS.md).

## Scope of the first version (Tier 1)

| Jurisdiction | Documents |
|---|---|
| EU | GDPR; AI Act; the AI Act amending regulation (the "Omnibus") |
| UK | UK GDPR; Data Protection Act 2018; Data (Use and Access) Act 2025 |
| Spain | LOPDGDD (Organic Law 3/2018) |

Regulator guidance, case law and adjacent laws come in later tiers. See [SOURCES.md](SOURCES.md) for licences and credit lines.

## Plan

| Phase | What |
|---|---|
| 0. Sources and licences | Confirm what may be reused and how, and which versions exist. Done |
| 1. Ingestion and chunking | Polite fetchers; chunks by legal structure with citation and as-of-date metadata. Done |
| 2. Gold question set | 80 bilingual questions with the correct articles, a table of exact facts and the metrics, frozen before any experiment. Done (not lawyer-reviewed) |
| 3. Retrieval experiments | Keyword, embeddings and hybrid; chunking; reranking; question rewriting. Pre-registered, judged by recall@k, MRR and nDCG with bootstrap intervals. Development half measured; a second embedding model and filters are open |
| 4. Answer layer ([plan](docs/PHASE4_PLAN.md), [how it works](docs/HOW_THE_ANSWER_LAYER_WORKS.md)) | Understand, route, look up exact figures, retrieve, answer with quotations checked in code, or refuse or decline. Built and measured on the development half; version-aware search built, not yet measured; test half not yet read |
| 5. Ship | Service layer with rate limit, traces and a degraded mode when the model is down; web page in English and Spanish with accessibility enforced by tests and a bilingual privacy notice tied to the code; CI smoke test; container built and run. Deployment: not started ([plan](docs/PHASE5_PLAN.md), [measurements](docs/DEPLOYMENT.md)) |

See [docs/ROADMAP.md](docs/ROADMAP.md) for what is done, what is next and what is not planned.

## Development

Python 3.12. From the repository root:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows; on Linux or macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest
ruff check . && ruff format --check .
```

Copy `.env.example` to `.env` and set `FETCHER_CONTACT` before running any fetcher: the source sites require an identifying User-Agent.

**Optional: the open embedding model (BGE-M3).** Nothing above needs it: the tests, CI and the keyword search run without it. To run the embedding experiments on your own machine you need Python packages (PyTorch, transformers, numpy) and a 2.3 GB model download. For a graphics card:

```bash
python -m pip install torch==2.7.1 --index-url https://download.pytorch.org/whl/cu126
python -m pip install -e ".[open-embeddings]"
python -m law_assistant.retrieval.get_bge
python -m law_assistant.retrieval.get_reranker  # optional, 2.3 GB, only for the reranker experiment (R5)
```

Without a graphics card install the CPU build of PyTorch instead and expect slower embedding. The saved vectors are not in the repository and are rebuilt from the chunks.

**Try it.** `python -m law_assistant.serve --demo` serves the web page with canned answers (no model, no key) at http://127.0.0.1:8000; without `--demo` it loads the real pipeline. `python -m law_assistant.ask "your question"` asks one question from the command line. Deployment notes: [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

**Optional: the answer layer.** It calls Google's Gemini API (`gemini-3.1-flash-lite`) for routing and for writing answers. Put `GEMINI_API_KEY` in `.env` (never commit it). The free tier allows about 500 requests a day for this model, which is enough for exploring but not for a full evaluation; the clients stop at once and say so when a quota is used up. To draw the pipeline as a LangGraph graph: `python -m pip install -e ".[agent]"`.

## Disclaimer

This project explains and cites public legal texts. It is not legal advice, it can be wrong or out of date, and it must not be used for decisions about real compliance. Check the official source.

## Licence

Code: [Apache-2.0](LICENSE). The legal texts it retrieves keep their own licences; see [SOURCES.md](SOURCES.md) and [NOTICE](NOTICE).
