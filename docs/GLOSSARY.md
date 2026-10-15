# Glossary: every term in this project, in plain words

Alphabetical. Each entry says what the thing is, then how it shows up in this project (with real numbers where there are any). Where a term has a longer explanation, the document is named.

**Abstain.** To decline to answer because the evidence is not enough. Here: if no quotation in a draft answer can be verified, the assistant says "I couldn't find enough in the texts I hold". 6 of 31 development questions were declined this way. Compare *refuse*. (`HOW_THE_ANSWER_LAYER_WORKS.md`)

**Answer layer.** Everything that happens after the search: reading the question, routing it, writing an answer from retrieved passages, checking it, refusing or declining. Phase 4.

**As-of date.** The date a question is about ("as of the start of 2026"). Law changes, so the same question can have different answers on different dates. Questions of this kind are the hardest here.

**Baseline.** The simplest alternative a new idea must beat. Keyword search (recall@5 0.24) was the search baseline; the same model answering from memory (correctness 0.63) is the answer-layer baseline. A result without a baseline means nothing.

**BGE-M3.** An open embedding model (BAAI, MIT licence) with 1,024 numbers per text, 8,192-token input, over 100 languages. Run locally on the graphics card; 0.12 s to embed a question on a plain CPU. The retriever of this project (recall@5 0.53).

**BM25.** A keyword scoring formula: a chunk scores higher the more of the question's words it contains, with rare words counting more and repeated words counting less and less. Needs no model. Our baseline. (`HOW_RETRIEVAL_WORKS.md`)

**Bootstrap (and paired bootstrap).** A way to put a margin of error on a score computed from few questions: resample the questions many times and see how much the score moves. "Paired" compares two variants on the same resamples so that luck cancels. Every interval in this project is a 95 % bootstrap interval over 10,000 resamples with a fixed seed.

**Chunk.** The piece of text the search finds and returns. Here: an article or a part of one, at most 400 words, with a context line in front. 3,831 chunks. (`CHUNKING.md`)

**Context line.** The first line of a chunk: law, chapter, article and its title ("GDPR | Chapter II | Article 6: Lawfulness of processing"). It tells an embedding model what it is reading. Removing it lowers recall@5 from 0.53 to 0.37.

**Cosine similarity.** How alike two embeddings are, from -1 to 1 (here mostly 0 to 1). With vectors scaled to length 1 it is just the dot product, which is why search is one matrix product.

**Corrigendum.** An official correction of a published legal text. The Spanish GDPR has 38 wording differences between the Official Journal text and the consolidated text because of one.

**Cross-encoder.** A model that reads the question and one passage together and scores the pair; sharper but slower than comparing two separate embeddings. Used as a reranker.

**Development half / test half.** The 80 gold questions are split 40 and 40. All tuning uses the development half; the test half is read once at the end, like a sealed exam, so the final number cannot be flattered by tuning.

**Dimensions (of a vector).** How many numbers make up an embedding. BGE-M3: 1,024.

**Embedding.** A list of numbers that stands for the meaning of a text, produced by a model, so that texts with similar meanings get similar lists. Lets "name a person responsible for data protection" find "designate a data protection officer" though they share few words. (`HOW_RETRIEVAL_WORKS.md`)

**Faithfulness / grounding.** An answer is grounded if every claim rests on supplied evidence. Here, checked two ways: in code (the quotation exists) and by a model judge (the claim follows from the quotation).

**FAISS.** A library for fast nearest-vector search. Compared in R7; not needed at our size.

**Fusion (reciprocal rank fusion, RRF).** Merging two ranked lists by position, not score: each list gives a result 1/(60 + place) points. Hurt here (0.43 against 0.53) because the weak keyword list dragged down the strong one.

**Gold set.** Questions with answers and sources written down by a person before the experiments, so a system's output can be compared with something trusted. 80 questions, now version 2. Not reviewed by a lawyer. (`GOLD_SET.md`, `GOLD_REVIEW_2.md`)

**Hit@k / recall@k / MRR / nDCG.** Scores for a ranked list. *hit@k*: is any right answer in the first k? *recall@k*: what share of the needed provisions is in the first k? *MRR*: how near the top is the first right answer? *nDCG*: how good is the whole ordering? The main score here is **recall@5**, because the answer writer reads about five passages. (`METRICS.md`)

**HNSW.** An approximate nearest-neighbour index (a graph of neighbours). Very fast on huge sets, slightly inexact. Not adopted.

**in_force_from.** A date stored on a chunk: when the current wording of that provision took effect, taken from the source's own dates. Needed for "since when" questions.

**Interval (95 %).** The range in which the true score probably lies. "Not detectable" means the interval of an improvement includes 0.

**Judge (model judge).** A language model that grades another model's answer. Useful, biased (the same family as the writer, so too generous): I read 12 verdicts and disagreed on 2.

**Language model (LLM).** A program that writes text. Fluent whether or not it is right, which is why answers are checked.

**LangGraph.** A library for writing a workflow as a graph of steps with conditional edges and shared state. The answer pipeline is wired in it and tested against the plain loop (`answer/graph.py`).

**Latency.** The time from a question to its answer. Reported as percentiles (median, 95th) because an average hides slow cases.

**NumPy.** A library for fast arithmetic on arrays. The search now takes 0.7 ms with it against 113 ms for plain Python.

**Pinpoint.** A provision id inside a unit ("eu-gdpr/art-6/1/f" is Article 6, paragraph 1, point (f)). A gold provision is found when a chunk contains any of its pinpoints.

**Pre-registration.** Writing down what you will test, how you will score it, the rule for adopting a variant, and what you expect, before running it. Stops you from choosing the flattering number afterwards. Every experiment script starts with one.

**Primary / acceptable.** The roles of a gold provision: primary must be found; acceptable is also fine.

**Provision.** The common record every parser produces: a recital, an article, a numbered paragraph, a lettered point, an annex item. About 20,800 across the corpus. (`PARSING.md`)

**Quota.** A limit on how much of a service you may use. Gemini's free tier: 500 requests a day for the cheap model, 20 for the larger one. When it runs out, the reply says how long to wait; waiting hours inside a script looks like a freeze, so the clients now stop at once.

**RAG (retrieval-augmented generation).** First find relevant passages, then give only those to a language model and tell it to answer from them. (`RAG_PLAYBOOK.md`)

**Refuse.** To decline because the question must not be answered: another country's law, a regulator's guide, or advice on the user's own situation. Compare *abstain*. 5 of 5 development refusals were right.

**Reranker.** A slower second-pass scorer that re-orders the first search's top candidates. Tried (bge-reranker-v2-m3): no gain, 32 times slower.

**Retrieval.** Finding the chunks that answer a question. Phase 3.

**Rewriting (query rewriting).** Restating an everyday question in the law's own words before searching. A strong writer lifted recall@5 from 0.53 to 0.70; cheap in-system models gave no detectable gain.

**Router.** The step that decides what to do with a question: retrieve, look up an exact figure, or refuse. The model router got 40 of 40.

**Seed.** The starting number of a random process, fixed so a "random" choice (the split, the bootstrap) can be repeated exactly.

**Split.** See *development half*.

**sqlite-vec.** A SQLite extension that stores vectors in a table and searches them with SQL. Compared in R7.

**Table (facts table).** 19 hand-checked exact figures (fine ceilings, deadlines, ages, application dates), each citing its source. Exact-figure questions are answered from it, not from prose.

**Tie.** Two results with exactly equal scores. Common here because copies of one text have identical vectors (3,831 chunks, 3,300 distinct vectors); the order among ties is arbitrary unless fixed (by chunk id).

**Token.** A piece of a word, the unit a model counts. A 400-word chunk is roughly 550 to 600 tokens.

**Trace.** One logged line per question handled by the demo: route, passages, step times, outcome. Never the visitor's address; deleted after 30 days.

**Vector / vector store.** An embedding is a vector; a vector store holds many and finds the nearest. At our size, a NumPy array is enough.

**Verification (of citations).** Code that checks every quotation in an answer appears in the passage it names. A failing quotation is dropped; with none left, the answer is not shown.

**Version (of a text).** The same law exists as first published ("oj") and consolidated; the GDPR and the AI Act were amended, the UK Acts are revised. Which version a question needs is half the difficulty.

**Degraded mode.** What the system does when its language model cannot be reached: rules route the question, the nearest table row answers figure questions, refusals use fixed messages, and other questions get the most relevant passages with a notice. Measured with every model call failing: refusals 5/5, figures 3/4.

**Last-token pooling.** A way to turn a model's per-token outputs into one vector by taking the last real token's output. Used by Qwen3-Embedding (BGE-M3 uses the first token instead).

**Smoke test.** A quick check that a program starts and basic things work: here, the real server process answers health, page, answer and error requests.

**WCAG contrast.** The accessibility standard's rule that text must contrast with its background by at least 4.5 to 1 (level AA). The page's lowest pair is 6.2 to 1 (light theme) and 7.0 to 1 (dark).

**Instruction prefix (for an embedding model).** A short sentence placed in front of a question telling the model what the search is for ("Given a question about EU, UK or Spanish data protection or AI law, retrieve the legal provisions that answer it"). Some models need it for questions and not for passages. Here it did not help.

**Ensemble.** Using two models together (here by reciprocal rank fusion) because they make different mistakes. R4.3: 0.58 against 0.53, not detectable.
