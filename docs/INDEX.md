# Start here: how to read and track this project

This project has a lot of documents because every step, number and decision is meant to be traceable. This page is the map: where to start, what each document answers, and what must be updated after each kind of change so the record stays complete.

## Three ways to read it

**1. In half an hour: what is this and what did it find?**
`README.md` (what it is, the results table) then `ROADMAP.md` (what is done and next), then the last section of `JOURNEY.md` ("What the process has taught us") and `RAG_PLAYBOOK.md` section 13 (the mistakes and what caught them).

**2. To learn how RAG tools are built (and why each choice).**
`GLOSSARY.md` for the words, then `RAG_PLAYBOOK.md` end to end (the general method, step by step), then `JOURNEY.md` in order (the same story as it happened, in three parts per step: the idea, why, what we found), with `HOW_RETRIEVAL_WORKS.md` and `HOW_THE_ANSWER_LAYER_WORKS.md` for the inner workings explained from scratch.

**3. To audit a claim.**
Find the claim in `EXPERIMENT_INDEX.md` (one row per experiment, with the result, the decision number and the script), read the pre-registration at the top of that script (the plan and the expected result, written before the run), then the full numbers and the reading in `EXPERIMENTS.md`, then the reasoning in the decision in `DECISIONS.md`. The commit that made a change is in `CHRONOLOGY.md`.

## Every document, and the question it answers

| Document | The question it answers |
|---|---|
| `README.md` | What is this, what has been measured, how do I run it? |
| `ROADMAP.md` | What is done, what is next, what is not planned, what are the known limits? |
| `JOURNEY.md` | What was done at each step, why, and what was found, in plain words? |
| `RAG_PLAYBOOK.md` | How do I build a RAG tool in general, with this project as the worked example? |
| `GLOSSARY.md` | What does this word mean? |
| `DECISIONS.md` | Why was each choice made, on what evidence, and what else was considered? (100 rows, one per decision) |
| `EXPERIMENT_INDEX.md` | Which experiments were run, with what result and decision? |
| `EXPERIMENTS.md` | What are the full numbers and readings of every run, with the commit and gold version? |
| `CHRONOLOGY.md` | What was committed when? (generated from git) |
| `SOURCES.md` | Which documents are used, under what licence, with what credit line? |
| `PARSING.md` | How are the laws turned into provisions, and what bugs did the checks catch? |
| `CHUNKING.md` | How are provisions cut into chunks, and why? |
| `GOLD_SET.md` | How was the test set made, reviewed and frozen? |
| `GOLD_REVIEW_2.md` | What did the second independent review find and change? |
| `FACTS.md` | What is in the table of exact figures and how is it checked? |
| `METRICS.md` | How is retrieval scored, and what can 31 questions detect? |
| `PHASE3_PLAN.md` | What was the plan for the retrieval experiments, and the rule for adopting a variant? |
| `HOW_RETRIEVAL_WORKS.md` | How do keyword search, embeddings, fusion and reranking work, from scratch? |
| `PHASE4_PLAN.md` | What was the plan for the answer layer? |
| `HOW_THE_ANSWER_LAYER_WORKS.md` | How does each answer-layer step work and what did it measure? |
| `PHASE5_PLAN.md` | How is the demo shipped: privacy, cost, container, checks, failures? |
| `ACCESSIBILITY_CHECKLIST.md` | What is a screen reader, and how do I test the page with one in ten minutes? |
| `DEPLOYMENT.md` | What was measured for deployment and what choice is still open? |

Also in the repository: `eval/gold/` (the questions and the manifest with their fingerprints), `eval/rewrites/` (the question rewrites and who wrote them), `facts/` (the exact-figure table), `experiments/` (every experiment script with its pre-registration), `tests/` (about 650 automated checks), `scripts/` (small tools such as the chronology generator). Not in the repository, by design: the private interview-preparation material.

## Conventions

- **Pre-register before you run.** The docstring of an experiment script states the variants, data, metrics, decision rule and the expected result, before the first run. If a plan changes before anything is scored, the script gets a dated "AMENDMENT" note.
- **Dev half for tuning, test half once.** The 40 test questions are read once, for the chosen configuration. The test half has now been read once for the retriever (T1: it held) and once for the answer layer (P4.6: it did not beat memory on accuracy); both are in `EXPERIMENT_INDEX.md`. No further read is planned.
- **Honest labels.** The gold set is drafted by an AI assistant, checked by scripts, reviewed by AI passes, and **not reviewed by a lawyer**. Variants designed after seeing development results are marked "tuned". Nothing here is legal advice.
- **Versions.** The gold set has versions (now 2). A result belongs to the version it was run under; results from different versions are not compared.
- **Decisions have five columns** (number, date, decision, evidence, alternatives) and no names.
- **Nothing is pushed by the assistant;** the owner pushes.
- **Secrets** live only in a git-ignored `.env` and are never printed.

## What to update after each kind of change (the tracking protocol)

| You did this | Update this |
|---|---|
| Ran an experiment | Its script docstring (before), `EXPERIMENTS.md` (`--log` writes the raw result; add a "Reading" section), `EXPERIMENT_INDEX.md` (a row), `DECISIONS.md` (a row if anything was adopted or rejected) |
| Made a design choice | `DECISIONS.md` (a row with evidence and alternatives); `JOURNEY.md` if it changes the story |
| Changed the gold set | A new manifest version, a note on each changed question, `GOLD_REVIEW_*.md` or a decision; never compare across versions |
| Changed the answer layer | `HOW_THE_ANSWER_LAYER_WORKS.md`, a decision, and a measurement before it becomes the default |
| Learned something general | `RAG_PLAYBOOK.md` (a lesson or a row of "mistakes and what caught them"), `GLOSSARY.md` for new terms |
| Committed | `python scripts/make_chronology.py` |
| Added a term | `GLOSSARY.md` |
| Reached a milestone | `ROADMAP.md` and the README status |
