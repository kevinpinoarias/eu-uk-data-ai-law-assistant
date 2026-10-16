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

## Written on 16 October 2026 and not yet run (they need accounts)

- **A cold-start notice** on the page: after 4 seconds without an answer the status line says the assistant may be waking up (English and Spanish, announced to screen readers, cleared when the answer arrives). Built and tested; checked in the browser by slowing the request.
- **A data bundle** (`scripts/make_data_bundle.py` writes `dist/data-bundle.zip`: the chunks and the saved BGE-M3 vectors, 17 files, 47.8 MB). The Dockerfile copies those files, and Git does not hold them, so CI could not build the image from a clean checkout; the bundle is uploaded once to a GitHub release and the workflow unpacks it. It carries the law texts under their publishers' reuse terms (SOURCES.md, NOTICE).
- **A manual deploy workflow** (`.github/workflows/deploy.yml`): builds the image, pushes it to GitHub's container registry with the workflow's own token, signs in to Azure keylessly, points the Container App at the new image and waits for `/health`. It runs only when started by hand. Tests check its triggers, permissions and that it stores no password; nothing proves it works until it runs once with the accounts below.

## Free-tier terms read on 16 October 2026 (secondary sources for prices; confirm in the portal)

- **Azure Container Apps (Consumption plan)**: per subscription each month, 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million requests are free, then billed per second; an app scaled to zero is not charged. At 1 vCPU and 2 GiB that is about 50 hours a month of active running (my arithmetic). The usual cause of a surprise bill is a minimum replica count above zero. Image size is not a billed quantity in what I read.
- **GitHub container registry**: public packages are free and container storage and bandwidth are "currently free" in GitHub's billing documentation, with no published end date. The image must be public so the app can pull it without a stored credential; it holds the law texts and the BGE-M3 model and no key.
- The Gemini bill is separate and starts when billing is enabled on the key.

## Hosting options re-checked on 16 October 2026 (the owner wants a permanently free tier)

The service needs about 1.5 GiB of memory because BGE-M3 runs on the server's CPU. That rules out the free tiers that are small or need no card.

| Option | Free and permanent? | Fit | Read from |
|---|---|---|---|
| **Google Cloud Run** | Yes: 180,000 vCPU-seconds, 360,000 GiB-seconds and 2 million requests a month, resetting monthly, applied as a spending discount at Tier 1 prices; billing account required (a card) | Fits (2 GiB, scale to zero). Same Google billing account as the Gemini key. The image must sit in Google's Artifact Registry (0.5 GB free, then a few cents a month for a 1.7 GB image; to confirm) or be pulled through a remote repository | cloud.google.com/run/pricing |
| **Azure Container Apps** | The monthly grant is per subscription with no end date in what I read; the $200 credit and the free account last 30 days, after which the account is disabled until upgraded to pay-as-you-go (a card), and the grant then still applies | Fits; the plan on file | azure.microsoft.com pricing pages |
| **Hugging Face Spaces** | No: Docker Spaces need a paid plan (PRO) to create; only static Spaces are free, and the free CPU hardware (2 vCPU, 16 GB) is for paid-plan Docker/Gradio Spaces | Does not fit the free requirement | huggingface.co/docs/hub/spaces-overview |
| Small free web hosts (512 MB, e.g. Render) and Oracle's always-free VM | Not checked today; from general knowledge the first is too small for the model and the second is a VM to look after and needs a card | Unverified | none |

Whichever host: the Gemini key needs billing for a public demo in the UK or EEA (decision at the start of the project), so a card is needed anyway. The deploy workflow is written for Azure; Cloud Run would need its own version (keyless sign-in works there too).

## Steps left (in order)

Mine, already done: cold-start notice, data bundle, deploy workflow, the candidate router and picker fixes and batch C (decisions 116 to 118). Waiting on the model's daily quota or a paid key: finishing the batch C comparison (`python experiments/c1_routing_fixes.py --log` resumes from its cache; about 90 calls remain, by the cache counts).

Needs you (accounts and approvals; commands below are written from general knowledge and not run, so check each against the provider's current documentation):

1. **Gemini billing with a budget alert.** In Google AI Studio or the Cloud console, attach a billing account to the project that owns the key and create a budget alert (an amount you are happy to lose, with an email at 50 % and 100 %). Then tell me; I run the measurements that wait for a paid key. Never paste the key in chat: it stays in `.env` (git-ignored) and, for the host, in the Container App's secrets.
2. **Docker Desktop running, and your approval of the build.** The image build downloads the 2.27 GB BGE-M3 model (BAAI/bge-m3 from Hugging Face, MIT licence); the image comes to about 1.74 GB. Start Docker Desktop and say yes, and I rebuild, run it locally and time 20 uncached questions.
3. **An Azure subscription** (card and phone verification), then, in a terminal:
   - a resource group and a Container Apps environment in a region you choose (the privacy notice names the host; say the region so I can add it);
   - the app, created once with a placeholder image, minimum replicas 0, maximum 1, 1 vCPU and 2 GiB, external ingress, and the model key stored as a Container App secret exposed as the environment variable `GEMINI_API_KEY` (plus `TRUST_PROXY=1`);
   - an app registration with a federated credential for this repository on branch `main` (issuer `https://token.actions.githubusercontent.com`, subject `repo:kevinpinoarias/eu-uk-data-ai-law-assistant:ref:refs/heads/main`, audience `api://AzureADTokenExchange`) and the Contributor role on that resource group only;
   - the five repository variables the workflow names (`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID`, `AZURE_RESOURCE_GROUP`, `AZURE_CONTAINER_APP`). They are identifiers, not secrets.
4. **A release holding the bundle** (licences checked 16 October, decision 119): `python scripts/make_data_bundle.py`, then on GitHub create a release tagged `data-v1` (the workflow's default tag) with `dist/data-bundle.zip` attached (the `gh` command-line tool is not installed here, so use the web page: Releases, Draft a new release). Paste the credit lines from `NOTICE` into the release notes. Re-do it after any re-chunking or re-embedding.
5. **Run the workflow once** (Actions, Deploy, Run workflow). When the first image is pushed, set the package to public in GitHub, and set the app's target port to 8000 if the placeholder used another.
6. **The privacy notice**: confirm the host and region. The ICO fee and EU representative questions were researched on 16 October (decision 120): probably both apply as things stand, so decide between paying and appointing, processing less, or not hosting publicly. Take the ICO's self-assessment ("Do I need to pay a fee?" on ico.org.uk) yourself; it is about your circumstances.
7. **A screen-reader pass** on the page (NVDA is free on Windows). An automated audit in the browser on 16 October found a sound structure (skip link first, logical tab order with a 3 px focus outline, labelled controls, a status line, a live result region that receives focus, headings and landmarks on both pages, table headers with `scope`) and no problems, but that is not hearing it: listen for whether a result is announced once or twice (focus moves to the result and the region is also live).
8. Put the live link in the README only after the test-half confirmation, so the demo and the reported numbers are the same system. The test-half numbers are in the README already (decision 114); any later change to the router or picker must be labelled and measured on new questions first.
