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

## Protecting a public demo's budget, and what it knows about its visitors

Every question costs model calls. As built on 16 October 2026 (decision 121):

- **Hard limits on the whole service, not per visitor**: at most 10 questions a minute and 300 a day in total (`QUESTIONS_PER_MINUTE` and `QUESTIONS_PER_DAY` change them), questions over 1,000 characters refused, a plain 429 when a limit is reached. The service is never given a visitor's address, so it cannot hold one (a test checks the function signatures and that the server code never reads an address); one visitor can use up the allowance for everyone, which is the trade for holding no addresses.
- **Traces without the question text**: a row holds the route, outcome, retrieved passage ids and timings, never the question, and rows are deleted after 30 days. The request log has no address either (a test captures it).
- **An access code**: when the host sets `ACCESS_CODE`, only requests carrying it in the `X-Access-Code` header can ask a question. The invited visitor's link is `https://HOST/#code=THE-CODE`: the page takes the code from the link's fragment (which a browser never sends to a server), removes it from the address bar and keeps it for that tab only. The pages and `/health` stay open. With no code set the server answers anyone, which is right for a local run and prints a note.
- **What remains**: the question text still goes to Google's Gemini to produce the answer, and the hosting platform sees each visitor's address in its own infrastructure logs, which this project does not read. This reduces what the demo processes a great deal; it does not settle the ICO-fee or EU-representative questions (decision 120), which the ICO's self-assessment and, for the representative, the audience decide.

The step-by-step plan, with privacy, cost, CI and failure handling, is in [PHASE5_PLAN.md](PHASE5_PLAN.md).

## Written on 16 October 2026 and not yet run (they need accounts)

- **A cold-start notice** on the page: after 4 seconds without an answer the status line says the assistant may be waking up (English and Spanish, announced to screen readers, cleared when the answer arrives). Built and tested; checked in the browser by slowing the request.
- **A data bundle** (`scripts/make_data_bundle.py` writes `dist/data-bundle.zip`: the chunks, the saved BGE-M3 vectors and NOTICE, 18 files, 47.8 MB). The Dockerfile copies those files, and Git does not hold them, so CI could not build the image from a clean checkout; the bundle is uploaded once to a GitHub release and the workflow unpacks it. It carries the law texts under their publishers' reuse terms (SOURCES.md, NOTICE, decision 119).
- **A one-time Azure setup script** (`scripts/azure_setup.sh`, for Azure Cloud Shell): registers the services, creates a resource group, a Container Apps environment with no log workspace, the app (a placeholder image until the first deploy, one replica at most and none kept idle, 1 vCPU, 2 GiB) with the Gemini key and the access code stored as the app's own secrets (typed hidden), and a keyless GitHub sign-in that only this repository's main branch can use and that can change only this resource group. Syntax checked with bash; never run.
- **A manual deploy workflow** (`.github/workflows/deploy.yml`): builds the image, pushes it to GitHub's container registry with the workflow's own token, signs in to Azure keylessly, points the app at the image and waits for `/health`. Every deploy re-asserts port 8000, at most one replica, none idle, and the references to the two secrets, so an app set up carelessly is corrected and a deploy to an app without the secrets fails instead of going live open. Tests check its trigger, permissions, that it stores no key and those settings; nothing proves it works until it runs once with the accounts below.

## Free-tier terms read on 16 October 2026 (confirm in the portal)

- **Azure Container Apps (Consumption plan)**: per subscription each month, 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million requests are free, then billed per second; an app scaled to zero is not charged. At 1 vCPU and 2 GiB that is about 50 hours a month of active running (my arithmetic). The usual cause of a surprise bill is a minimum replica count above zero. Image size is not a billed quantity in what I read.
- **The Azure free account** is separate from that grant: it gives a 200 US dollar credit for 30 days, and when the 30 days (or the credit) end the account is disabled until it is upgraded to pay-as-you-go. Upgrading needs the card already given at sign-up; Microsoft says it never charges unless you choose pay-as-you-go, and the monthly grant above still applies after upgrading, so a demo that stays inside it costs nothing. Without the upgrade the demo stops after 30 days.
- **The "12 months free" list the owner pasted from the Azure free account page** (16 October): every item on it ends after 12 months, so none is the permanent tier we want. Three items matter here. *Container Registry* (one Standard registry, 100 GB) is free for 12 months, which corrects the project's earlier note that Azure's registry has no free tier at all; after the year it costs roughly 20 US dollars a month (from memory, to confirm), so the image stays in GitHub's registry. *Linux virtual machines* (750 hours of B2pts v2 or B2ats v2) are free for 12 months but, as I recall, have about 1 GiB of memory, too little for the 1.5 GiB the model needs, and would be a machine to look after. *Key Vault* (10,000 operations) could hold the secrets, but the Container App's own secrets already do and cost nothing. Container Apps' monthly grant is not on that list; I read it on the Container Apps pricing page, and the page of always-free services did not load its list for me, so confirm it in the portal when you sign up.
- **GitHub container registry**: public packages are free and container storage and bandwidth are "currently free" in GitHub's billing documentation, with no published end date. The image must be public so the app can pull it without a stored credential; it holds the law texts and the BGE-M3 model and no key.
- **Gemini billing** is separate: prepay at least 5 US dollars (requests fail with HTTP 402 when the balance reaches zero) or postpay, with a monthly spend cap on AI Studio's Spend page. A budget alert (Google Cloud or Azure) only emails; it does not stop spending.

## Hosting options (re-checked on 16 October 2026; the owner chose to stay on Azure, decision 123)

The service needs about 1.5 GiB of memory because BGE-M3 runs on the server's CPU. That rules out the free tiers that are small or need no card.

| Option | Free and permanent? | Fit | Read from |
|---|---|---|---|
| **Azure Container Apps** (chosen) | The monthly grant is per subscription with no end date in what I read; the free account and its credit last 30 days and then need an upgrade to pay-as-you-go (a card) | Fits | azure.microsoft.com pricing pages |
| Google Cloud Run (considered, decision 122, dropped) | Yes: the same size of monthly grant, resetting monthly, billing account required (a card) | Fits; would share billing with the Gemini key; the image would need Google's Artifact Registry | cloud.google.com/run/pricing |
| **Hugging Face Spaces** | No: Docker Spaces need a paid plan (PRO) to create; only static Spaces are free | Does not fit | huggingface.co/docs/hub/spaces-overview |
| Small free web hosts (512 MB, e.g. Render) and Oracle's always-free VM | Not checked; from general knowledge the first is too small for the model and the second is a VM to look after and needs a card | Unverified | none |

## What was done, and what is left (18 October 2026)

**Done.** The Azure account and a budget alert; the Gemini key; `scripts/azure_setup.sh` run in Cloud Shell; the five repository variables; the `data-v1` release; the Deploy workflow, which went green after three fixes found on the first real runs (an `unzip` that waited for an answer, the NumPy tests CI could not run, and the sign-in subject, which GitHub presents with numbers); the package made public; the live site opened with the access code and a question answered; the new key put into Azure and the app restarted. The checks of the address, the pages, the 401 without a code and CI are repeatable with the commands in this file.

**Still open**
1. **Upgrade the Azure account** to pay-as-you-go within the 30 days (Subscriptions, your subscription, Upgrade), or the demo stops. The Container Apps monthly grant continues after upgrading.
2. **The Gemini billing choice.** A key in a project linked to a prepaid account fails with HTTP 402 when the credit is used up; a key in a project with no billing is on the free tier, which changes what the privacy notice may say about the terms Google applies. Either way a spend cap on AI Studio's Spend page is the hard limit.
3. **The ICO self-assessment** and the EU-representative question (decision 120): the minimal data and the closed audience reduce what is processed but do not settle them.
4. **The 20-question timing** on the running container (`az containerapp exec`, then `python -m law_assistant.answer.trace_report`).
5. **A screen-reader pass** on the page (NVDA is free on Windows): listen for whether a result is announced once or twice.
6. **The wake-up message.** The first request after a quiet spell took 91 to 98 seconds here; the page says "up to a minute".
7. Keep the **package public** on GitHub, or a new deploy cannot pull the image.
