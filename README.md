# EU / UK Data and AI Law Assistant

A bilingual (English and Spanish) retrieval-augmented assistant for EU, Spanish and UK data-protection and AI law. It aims to answer questions with verified citations, say when it does not know, and measure every design choice instead of assuming it.

> **Status: planning. Nothing is built yet.** This repository currently holds the project scaffolding and the source and licence research. It is not legal advice.

## Why this project

An earlier project of mine, a hospitality demand-forecasting system with a live chat assistant, answers numeric questions by tool-calling against structured data, because a model that retrieves a passage and paraphrases it can get a number wrong. The opposite case is unstructured prose with no schema, such as legislation, where semantic retrieval is the right fit. This project tests that reasoning on a corpus large enough to matter, and measures it.

What makes the problem interesting:

- **Three jurisdictions, two languages.** EU, Spanish and UK law, in English and Spanish, including questions that compare the EU and the UK.
- **Law changes.** Amendments and commencement dates mean an answer must say which version it used.
- **Citations must be checkable.** Every answer cites its source, and the citation is verified in code.
- **Knowing when not to answer.** Out-of-scope questions and requests for legal advice are refused.

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
| 0. Sources and licences | Confirm what may be reused and how, and which versions exist. Licences, document manifest and fetch rules are done; technology decisions (models, cloud) are pending |
| 1. Ingestion and chunking | Polite fetchers; chunks by legal structure with citation and as-of-date metadata |
| 2. Gold question set | 60 to 100 bilingual questions with the correct articles, frozen before any experiment |
| 3. Retrieval experiments | Keyword, embeddings and hybrid; chunking; embedding models; reranking; filters; vector store comparison. Pre-registered, judged by hit@k, recall@k, MRR and nDCG with bootstrap intervals |
| 4. Answer layer | A LangGraph workflow: route, retrieve, grade, answer with citations, verify, or abstain; compared with no retrieval and with the whole corpus in the prompt |
| 5. Ship | API, interface, Docker, CI, deployment and retrieval traces |

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

## Disclaimer

This project explains and cites public legal texts. It is not legal advice, it can be wrong or out of date, and it must not be used for decisions about real compliance. Check the official source.

## Licence

Code: [Apache-2.0](LICENSE). The legal texts it retrieves keep their own licences; see [SOURCES.md](SOURCES.md) and [NOTICE](NOTICE).
