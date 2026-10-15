# Deploying the demo: what is built, what was measured, what is left

## What exists

| Piece | Where | State |
|---|---|---|
| The pipeline | `src/law_assistant/answer/` | Built; measured on the development half |
| A service layer: input checks, a rate limit, a trace of every question | `answer/service.py`, `answer/trace.py` | Built and tested (19 tests) |
| A web server and one page | `src/law_assistant/serve.py`, `web/index.html` | Built, tested over real HTTP, and the page checked in a browser (desktop, phone width, dark theme) with canned answers (`--demo`) |
| A command-line question | `python -m law_assistant.ask "..."` | Built, not run end to end (the model's free allowance for the day was used up) |
| A container image | `Dockerfile`, `.dockerignore` | **Built and run** (15 October 2026): 1.74 GB, healthy 10 seconds after start, 1.5 GiB of memory at rest, the page and `/health` served, a question answered with the model allowance used up returned the plain 503 and wrote a trace without an address. Not yet run with a working model key |

## What was measured for deployment

- **A hosted server has no graphics card, and that is fine.** BGE-M3 on this machine's CPU (an i7-8700) embeds one question in about **0.12 s** (six questions, EN and ES, 0.11 to 0.12 s each) and loads in 11 s from a warm disk. The chunk vectors are computed once and saved: 3,831 chunks, 51 MB; the chunk text is 8 MB.
- **Memory.** Measured in the running container: **1.5 GiB** at rest with the model loaded (my earlier estimate of 4 GB was too high: the search indexes use NumPy arrays, 16 MB each). A host with 2 GiB should do; confirm under load.
- **Where the time goes.** Search is a fraction of a second. The two model calls (route, write the answer) were 1.7 s on average for the answer step on the free tier; the router and table-picker calls add to that. A full per-question latency on uncached calls has not been measured yet.
- **A serving bug found while measuring.** The search index rewrote its whole 51 MB vector file after every new question (right for experiments, which resume from it; wrong for a server). A serving index now keeps new question vectors in memory only (`persist_queries=False`), with tests.

**Note:** the image described here was built before the Spanish interface, the accessibility changes and the degraded mode; rebuild it (`docker build -t law-assistant .`, layers are cached so it is quick) before any deployment.

## What building and running the image taught

The first image built without error and then **failed at start-up**: it had installed `transformers` 5.20.0, which needs a newer PyTorch than the pinned 2.7.1 CPU build, so importing the model class failed (the tested environment had 5.19.0). Only running the image found it. The fix is a version bound in `pyproject.toml` (`transformers>=4.40,<5.20`) and a build-time import check in the `Dockerfile`, so a mismatch fails the build. (The first attempt at the fix also wrote a literal backslash-n into the Dockerfile; reading the file back before the rebuild finished caught that.) Lesson recorded in `RAG_PLAYBOOK.md`.

## The choice that is still open: where do question embeddings come from?

| | A. BGE-M3 on the server's CPU | B. Gemini's embedding model over the API |
|---|---|---|
| What it needs | The 2.3 GB model in the image; 4 GB or more of memory | Embeddings of the whole corpus made once with the same model |
| Measured quality | recall@5 0.53 (development half) | **Not measured**: the first run stopped at 640 of 3,304 vectors on the free tier |
| Image size and start-up | Several GB; a cold start loads the model (11 s warm, longer cold) | Small and quick |
| Running cost | Compute only | A small cost per question once billing is on (Google's page: $0.20 per million tokens, so the whole corpus is under $1, read 15 October) |
| Risk | Cold starts if the platform scales to zero | Needs a billing key; quality unknown until measured |

Billing would also unlock B's measurement (it doubles as the second embedding model of experiment R4). Until then A is the tested path.

## Protecting a public demo's budget

Every question costs model calls. The service limits **6 questions a minute per client** and **300 a day for everyone** (`RateLimiter`, both adjustable), refuses questions over 1,000 characters, and logs every question without the client's address to `data/traces/traces.jsonl` (the page says questions are logged). Still to do on the Google side: a **budget alert** on the billing project, and the key held only as a hosting secret (never in the image or the repository).

The step-by-step plan, with privacy, cost, CI and failure handling, is in [PHASE5_PLAN.md](PHASE5_PLAN.md).

## Steps left (in order)

1. Billing on the Gemini project, with a budget alert (yours).
2. Build and run the image locally once; measure the uncached latency of 20 questions.
3. Create the hosting account and a deployment that scales to zero (your account details; the hosting plan and its free grant should be re-read on the provider's pricing page before choosing sizes).
4. A deployment workflow that builds the image and publishes it, using keyless authentication, not a stored password.
5. Put the live link in the README only after the test-half confirmation, so the demo and the reported numbers are the same system.
