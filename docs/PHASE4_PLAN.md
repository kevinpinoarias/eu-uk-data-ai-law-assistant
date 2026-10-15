# Phase 4 plan: the answer layer (15 October 2026)

**Status (end of 15 October 2026).** Approved and built, except as noted: steps 1, 2, 3, 5 and 6 and the table lookup are built and tested; the five design decisions of section 5 were taken as recommended; the router is a model router with a rule router as the baseline; the baselines of 4.4 were run on the development half except "the whole corpus in the prompt" (it is about 1.2 million tokens and does not fit); the comparison of answer models (4.6) has not been run (the larger Gemini model allows 20 free requests a day, so it needs a paid key); LangGraph (1.2.15) is installed and wired in `answer/graph.py` as an optional extra, with tests showing it matches the plain loop. Results: `EXPERIMENTS.md` (P4.1 to P4.4); explanation: `HOW_THE_ANSWER_LAYER_WORKS.md`.

Original plan, kept as written. Nothing below was built when it was written. It follows the project's rules: plan first, test first for deterministic code, pre-register the experiments, tune on the 40 development questions and touch the 40 test questions once per decision.

## 1. The ideas, from scratch

**A language model (LLM)** is a program that writes text. Given a question and some passages, it can write a fluent answer. Fluency is the danger: it will also write a fluent answer that is wrong, or that cites a provision it never saw.

**Retrieval-augmented generation (RAG)** means: first find the relevant passages (Phase 3), then give *only those* to the model and tell it to answer from them. The answer layer is everything that happens after the search.

**An agent (or workflow)** is a program that does several steps in order, sometimes choosing the next step by looking at what it found. Ours has to: decide what kind of question this is, look things up, check the evidence, write the answer, check the answer, or decline.

**LangGraph** is a library for writing such a workflow as a **graph**: each step is a box (a function), the arrows say what can follow, an arrow can be conditional ("if the evidence is weak, go to *decline*"), and one shared **state** (the question, the language, the chunks found, the draft answer) is passed along. It is the tool named in the job description, and it makes the flow visible and testable: each box can be tested alone. It is not installed; installing it needs your approval, and I would read its current documentation before writing any code.

**Grounding, citation and abstention** are the three behaviours that make it trustworthy: every claim comes from a retrieved passage (grounding), the answer names the exact provision (citation), and when the evidence is missing or the question is outside the corpus or asks for legal advice, it says so (abstention).

## 2. The workflow we will build

```
question
   |
[1 understand]  detect language; guess jurisdiction (EU, UK, Spain); read any date ("as of 2025")
   |
[2 route] ---- numeric question ----> [table lookup] ---------------------------+
   |---------- out of scope / advice ---------------------------> [decline] ----+
   |
 retrieve
   |
[3 retrieve]  search the chunks (the Phase 3 winner), with the right filters
   |
[4 grade]  is there enough evidence? ---- no ----> [decline or ask for detail] --+
   |
[5 answer]  the model writes the answer from the chunks, quoting and citing
   |
[6 verify]  in code: every cited chunk was retrieved; every quote appears in it;
            the answer states the version date it used
   |
 answer with citations  <----------------------------------------------------------+
```

What each box is, and how it is tested:

| Step | What it does | Plain test |
|---|---|---|
| 1 understand | Detects the question's language, the jurisdictions it mentions, a requested date. Mostly rules and the gold labels as a check. | Language and jurisdiction accuracy against the gold labels. |
| 2 route | Chooses retrieve, table or decline. A first version is rule-based (words such as "fine", "how long", "from what date"); a second asks the model. | Routing accuracy on the 80 labelled questions: this is the project's central claim (roadmap 4.5). |
| 3 retrieve | Calls the retriever chosen in Phase 3. | The Phase 3 metrics, unchanged. |
| 4 grade | Decides whether the retrieved chunks can support an answer (a rule on scores, then possibly a model). | Does it decline the refusal questions and answer the rest? |
| 5 answer | The model writes a short answer in the question's language, quoting the provisions, in plain words, not as legal advice. | Faithfulness and citation precision (below). |
| 6 verify | Deterministic code, no model: cited ids must have been retrieved, quoted text must appear in them, and the date used is named. A failure sends the answer back or turns it into a decline. | Unit tests on small cases, written first. |

## 3. What we measure (pre-registered)

All on the development questions first; the test questions once, for the final system against the baselines.

| Measure | Plain meaning | How |
|---|---|---|
| Routing accuracy | Did the question go to the right tool? | Against the gold route (retrieve 62, table 8, refuse 10). |
| Citation precision | Of the provisions the answer cites, how many are real and were retrieved? | Computed in code. |
| Faithfulness | Is every claim in the answer supported by the retrieved text? | A checklist of the key points from each gold answer plus a review of the claims; where a model is used as the judge, its agreement with a human sample is reported. |
| Abstention correctness | Does it decline exactly when it should? | On the 10 refusal questions and on questions with deliberately removed evidence. |
| Cost and latency | Money and time per question. | Logged for every run, with percentiles. |

## 4. The comparisons (roadmap 4.4 and 4.6)

- **4.4 Baselines for the whole system:** no retrieval at all (the model answers from memory), and the whole corpus in the prompt where it fits. If the full RAG system does not clearly beat them, we say so. These show what retrieval buys.
- **4.6 Answer model:** the default is Gemini 3.1 Flash-Lite; compare with a larger Gemini Flash model and an open model (gpt-oss-120b through a free host), with retrieval and questions held fixed. The default stays unless another is clearly better on faithfulness and abstention at an acceptable cost.
- **Rules as in Phase 3:** the plan and decision rule are written before each run, every variant is counted, results carry intervals, and the test half is touched once per decision.

## 5. Design decisions to take together

1. **Rule-based router first, then a model router.** The rule-based version is free, explainable and gives a baseline to beat. Recommended.
2. **Verification in code, not a second model.** Cheap, exact and repeatable. Recommended.
3. **Answers in the question's language**, with citations in the law's own form (Article 6(1)(f), artículo 6.1.f). Recommended.
4. **Stance:** it explains what the text says; it does not tell anyone what to do, and every answer says so briefly.
5. **As-of dates:** the answer names the version it used, and says when the question's date falls before an amendment (the AI Act changed in July 2026).

## 6. Order of work

1. Install LangGraph (with your approval) and read its documentation.
2. Build and test steps 1 and 6 (language detection, verification), which need no model.
3. Rule-based router and its accuracy on the development questions.
4. Retrieve and grade, using the best Phase 3 retriever.
5. The answer step with the default model (needs the Gemini key, free tier for development).
6. Baselines, then the answer-model comparison, then one confirmation on the test half.

## 7. What I need from you

- Approval of this plan (or changes), especially the five decisions in section 5.
- Later: approval to install LangGraph, and a decision on which answer models to compare.
- An honest warning: the answer layer can only be as good as retrieval. With keyword search at 0.24 recall@5, an answer layer would mostly decline or cite the wrong law, so I would not start step 4 before Phase 3 has a better retriever.
