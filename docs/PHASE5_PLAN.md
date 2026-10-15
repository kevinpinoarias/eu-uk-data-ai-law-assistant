# Phase 5: shipping, in plain words (15 October 2026)

Phases 1 to 4 built and measured the system. Phase 5 turns it into something a stranger can use safely, cheaply and without you watching it. It is a separate phase because most of what goes wrong with a public AI demo is not in the model: it is cost, abuse, privacy, slow starts and silent failures. Each step below has the same three parts as the other documents: **in this project**, **in general**, and **the basics applied** (real numbers or the real state).

## The map

```
 visitor -> [5.3 web page] -> [5.1 service: checks, limits, errors, trace] -> the answer pipeline (Phase 4)
                                         |                                        |-> BGE-M3 on CPU (0.12 s)
                                         |                                        |-> Gemini (route, write)
                                         v
                              [5.7 trace log] -> [5.7 report]        [5.4 container] -> [5.5 CI] -> [5.6 hosting]
 around all of it: [5.2 privacy]   [5.8 cost and budget]   [5.9 what happens when things fail]   [5.10 done means]
```

| Step | State |
|---|---|
| 5.1 Service layer | Built and tested |
| 5.2 Privacy of the demo | Retention and warning built; notice and legal basis to decide |
| 5.3 Web page | Built, checked in a browser |
| 5.4 Container image | Built and run; healthy in 10 s, 1.5 GiB; model-key run pending |
| 5.5 Continuous integration | Lint, tests and secret scan exist; image build and smoke test to add |
| 5.6 Hosting | Not started (needs your account) |
| 5.7 Traces and their report | Built and tested |
| 5.8 Cost and budget | Tokens measured; price and budget alert need billing |
| 5.9 Failure handling | Quota and error responses built; more to add |
| 5.10 Definition of done | Written below |

## 5.1 The service layer (`answer/service.py`)

**In this project.** One function turns a request into an answer: it checks the input (a non-empty question of at most 1,000 characters), refuses too many questions (6 a minute per visitor, 300 a day for everyone), runs the pipeline, hides internal errors behind a plain message, and writes a trace.
**In general.** Anything public needs a front door that does not trust its callers. The limits are the cost control, the input checks keep junk out of the model, and hiding error details keeps internals (and keys) out of the browser.
**The basics applied.** 24 tests cover every rule with a fake pipeline and a fake clock, so nothing waits and nothing is called for real. A model allowance that is used up now returns a 503 "the assistant's allowance is used up for now" and not a generic error.

## 5.2 Privacy of the demo itself

**In this project.** The irony is worth saying out loud: a data-protection assistant that logs what people type is processing personal data, because people paste real situations ("my employer fired me on 3 May, my name is..."). So the demo does four things: it never stores the visitor's address; it asks visitors not to type personal data (on the page); it deletes traces after 30 days (`TRACE_RETENTION_DAYS`, tested); and it says on the page that questions are logged and why.
**In general.** The same rules the assistant explains apply to its own operator: collect little, say what and why, keep it briefly, and be able to delete it.
**The basics applied, and what is still open.** A fuller privacy notice (who runs it, what is logged, for how long, how to ask for deletion, the lawful basis) must be written by a person who can take that responsibility; I can draft it but it is not legal advice and I would not publish it for you. Also, the questions go to Google's API: from my reading of Google's terms on 13 October 2026, content sent on the **free tier may be used to improve Google's products**, and the terms require paid services for apps available to users in the EEA, Switzerland and the UK. A public demo should therefore use a billing-enabled key, not the free tier, and the page should say that questions are processed by Google. (Re-read the terms before launch; they change.)

## 5.3 The web page (`web/index.html`)

**In this project.** One file, no outside libraries, no tracking: a question box, four example questions (English, Spanish, an exact figure, an out-of-scope one), a result card with a label (answer, exact figure, not answered, not enough evidence), the sources with their quotations, the disclaimer, and a link to the repository.
**In general.** For a demo the page matters less than the three things it must get right: say clearly what the tool is and is not, show where an answer came from, and work on a phone.
**The basics applied.** Checked in a browser at desktop and phone width and in dark mode, no console errors; text is inserted with `textContent` (never as HTML) so an answer cannot inject markup; a security header restricts what the page may load. Still open: Spanish interface text (the examples are bilingual but the labels are English), and an accessibility pass with a screen reader.

## 5.4 The container image (`Dockerfile`)

**In this project.** An image that runs the service on a plain CPU: CPU-only PyTorch (much smaller than the default), the BGE-M3 weights (2.27 GB) downloaded at build time, the chunks (8 MB) and saved chunk vectors (51 MB) copied in, a health check, and `TRUST_PROXY=1` so the rate limit sees the visitor's address behind the host's proxy.
**In general.** A container is a sealed folder that runs the same everywhere. Building it once and running that same image on your machine and in the cloud removes "it worked on mine".
**The basics applied.** Measured: a question embeds in 0.12 s on an ordinary CPU; the built image is 1.74 GB, starts healthy in 10 s and uses 1.5 GiB of memory at rest. The first build failed at start-up because of an unpinned `transformers` version (fixed with a bound and a build-time import check). Verified against the real container: the page, `/health`, and the plain 503 for a used-up model allowance with a trace written. Not yet done: timing 20 uncached questions end to end, which needs the model's daily allowance.

## 5.5 Continuous integration

**In this project.** Today every push runs the linter, the formatter check, all tests (about 640) and a secret scan. To add: build the image on every change to the Dockerfile without publishing it; start the container in demo mode and check that `/health` answers and the page loads (a smoke test that needs no key); and, when deployment exists, publish the image and deploy with **keyless** authentication (the repository proves who it is to the cloud with a short-lived token, so no password is stored anywhere).
**In general.** CI is the safety net that makes small, frequent changes safe. Keyless deployment is the current good practice because a stored password is the thing that leaks.
**The basics applied.** The tests that need a model or key are written to skip without them, so CI stays free and fast; the 5.4 smoke test follows the same rule.

## 5.6 Hosting

**In this project.** The plan from 13 October: Azure Container Apps, which can scale to zero (nothing running, nothing charged, when nobody is asking), with the image stored in GitHub's container registry because Azure's own registry has no free tier. The consequence of scaling to zero is a **cold start**: the first visitor after a quiet spell waits for the container to start and the model to load (11 s on this machine, likely more cold).
**In general.** Free tiers are real but narrow: they cap compute, memory and time. The design question is what the cheapest honest setup is, and what a visitor sees when it is cold.
**The basics applied, and open.** I have not re-read the provider's current free grant, so no size or price here is a promise; that must be done when you create the account. The cold start can be hidden by a "waking the assistant up" message on the page, or avoided by keeping one instance warm (which costs).

## 5.7 Traces and their report

**In this project.** Every question writes one line: its route, language, the passages retrieved, whether quotations were dropped, the time of each step and the total, how it ended, never the visitor's address. `python -m law_assistant.answer.trace_report` turns the file into numbers: questions, outcomes, languages, median and 95th-percentile latency, share declined, answers with a dropped quotation, slowest step.
**In general.** You cannot fix what you cannot see. Percentiles, not averages, because one slow question hides in an average and hurts a real person.
**The basics applied.** Built and tested with fake traffic. The first real numbers (and the first real failures) come from the first 20 uncached questions.

## 5.8 Cost and budget

**In this project.** Each answered question made about 1.7 thousand prompt tokens and 0.25 thousand output tokens in the development runs, plus a router call, so about three small model calls. A paid key turns those into money.
**In general.** Cost per question is a design number, not an accident: it is tokens times price, times the limits you set.
**The basics applied.** I have not verified a price, so none is stated here. The ceilings that protect the budget already exist (300 questions a day in total). Still needed from you: billing on the key and a **budget alert**, then I compute the real cost of the 20-question run and set the daily cap from it.

## 5.9 When things fail

**In this project.** What a visitor sees when something breaks: the allowance used up (503, plain message), any other model error (500, plain message, details only in the trace), a question too long or empty (400), too many questions (429). Built: **degraded mode** (decision 103): with the model unreachable, rules route the question, the nearest table row answers figure questions, refusals use fixed messages and other questions get the three most relevant passages with a notice. Measured with every model call failing: refusals 5/5, figures 3/4, no false refusals or figures. Not yet built: a friendly page for the cold start.
**In general.** Decide failure behaviour before launch. The worst failure of an AI demo is not an error; it is a confident wrong answer, and that is what Phase 4's quotation check exists to prevent.
**The basics applied.** Tested: each status code, that the user never sees an internal message, and the degraded mode on the 40 development questions. Open: a cold-start notice.

## 5.10 What "done" means for Phase 5

1. The image builds, starts, and answers 20 different questions with the key supplied only as a hosting secret (not in the image or the repository).
2. The test half has been read once and its numbers are in the README **before** the live link is, so the demo and the reported numbers are the same system.
3. A budget alert exists and the daily cap is set from the measured cost.
4. A privacy notice written by a person is on the page; traces are deleted after 30 days.
5. The trace report shows median and 95th-percentile latency from real use.
6. A short runbook says how to take it down (set the daily cap to zero or scale to zero).

## Who does what

| | You | Me |
|---|---|---|
| Billing and budget alert on the Gemini project | yes | compute cost and caps afterwards |
| Hosting account (card and phone verification) | yes | write the workflow and the setup notes |
| Approve the 2.3 GB image build | yes | build, run, time 20 questions |
| Privacy notice and its lawful basis | decide | draft it, not as legal advice |
| Everything else in 5.1 to 5.9 | | build, test, document |

The order I would do it in: billing, then the measurements that wait for it (version-aware search, the one test-half read, the 20-question timing), then the image build, then hosting and CI, then the live link last.
