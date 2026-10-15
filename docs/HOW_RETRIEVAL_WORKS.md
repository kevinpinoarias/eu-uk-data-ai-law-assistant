# How retrieval works, one level deeper

Written for the project owner, with numbers measured on our own corpus (15 October 2026). Each idea comes in three parts: what it is in general, what it means here, and what we measured.

## The shape of the system

```
question -> [find candidate chunks] -> [re-order them] -> top k chunks -> answer model -> answer with citations
              keyword search                reranker
              embedding search
              fusion of the two
```

The index holds **3,831 chunks** of about **239 words** each (13,635 distinct words). Finding the right chunk among them is the retrieval problem. Everything below is a different way of scoring "how well does this chunk answer this question".

## 1. Keyword search (BM25)

**Generic.** Count the question's words in each document and score the document. Two refinements make it work: a word found in few documents is worth more than one found everywhere (**inverse document frequency**), and a long document should not win just by being long (**length normalisation**). BM25 is the standard formula that does both. It needs no model, no training, no download, and runs in milliseconds.

**Here.** The score of a chunk is the sum, over each distinct word of the question that it contains, of `idf × tf × (k1 + 1) / (tf + k1 × (1 − b + b × length / average length))`, with k1 = 1.2 and b = 0.75. Measured word weights (idf) over our 3,831 chunks:

| word | in how many chunks | weight |
|---|---|---|
| the | 2,319 | 0.50 |
| data | 1,716 | 0.80 |
| person | 511 | 2.01 |
| responsible | 102 | 3.62 |
| name | 68 | 4.02 |
| designate | 39 | 4.57 |
| erasure | 82 | 3.84 |

So "designate" counts nine times what "the" does. The formula is checked in `tests/test_retrieval.py` against a hand-computed example.

**Measured (R1).** On the 31 development questions BM25 finds 24 % of the required provisions in its top five (recall@5 0.24, interval 0.12 to 0.39). Where it fails is instructive:

- **Vocabulary gap.** q004 asks "Do I need to *name* a *person responsible* for data protection...". The right article, GDPR Article 37, says "*designate* a data protection *officer*". It shares only common words with the question, and ranks **724th of 3,831**. A keyword search cannot know that a "person responsible for data protection" is a "data protection officer".
- **No cross-language.** All 155 chunks in the top fives were in the question's own language.
- **Copies use up slots.** On average 0.77 repeated units sit in a top five (the same article in two versions, or two pieces of it).
- **Accent folding did nothing useful** (R1.2: 0.23 against 0.24).

## 2. Embeddings and embedding search

**Generic.** An **embedding model** is a neural network that turns a piece of text into a list of numbers (a **vector**, for example 768 numbers) so that texts with similar meaning get vectors that point in similar directions. It is trained on very many pairs of related texts (a question and its answer, a sentence and its translation) to pull related pairs together and push unrelated ones apart. To search, you embed every chunk once and store the vectors; at query time you embed the question and find the chunks whose vectors are closest. Closeness is usually **cosine similarity**: the angle between two vectors (1 means the same direction, 0 unrelated). If vectors are scaled to length 1, cosine is just a dot product.

**Properties that matter when choosing a model** (these are what R4 compares):

| property | what it is | why it matters here |
|---|---|---|
| Languages | which languages share one vector space | A Spanish question must land near its English answer text; the UK Acts exist only in English, the LOPDGDD only in Spanish. |
| Dimensions | length of the vector (commonly 384 to 3,072) | More dimensions can hold more nuance but cost memory and time. 3,831 chunks at 768 dimensions is about 12 MB, at 3,072 about 47 MB: trivial either way. |
| Maximum input length | how many tokens it reads | A chunk longer than this is silently cut off. Our 400-word cap is roughly 550 to 600 English tokens, and Spanish needs more; this has to be checked against each model's limit. |
| Query and passage handling | some models want a prefix such as "query:" or "passage:" or a task instruction | Getting this wrong quietly lowers quality. |
| Where it runs | a hosted service (an API key, a request per call, rate limits, terms of use) or on our machine (a download, memory, speed) | Cost, privacy, reproducibility, and whether a public demo may use it. |
| Version stability | a hosted model can change under you | An experiment is only repeatable if the model is pinned. |

**Here.** Our chunks carry a context line ("GDPR | Chapter II | Article 6: Lawfulness of processing") that is part of the embedded text (decision 37), so the model sees where each passage sits. Brute-force search over 3,831 vectors is one matrix-vector product: about three million multiplications, milliseconds on any laptop. That is why R7 expects a vector database to add nothing in accuracy at this size.

**What embeddings are good and bad at.** Good: paraphrase and lay wording ("name a person responsible" can land near "designate a data protection officer"), and across languages. Weaker: exact strings such as "Article 83(5)", a rare defined term, or a number, which keyword search handles well. This is why R1 measures both and R2 tests combining them. **Not yet measured:** we have not run any embedding model, so none of this is a result for our corpus.

## 3. Combining the two: reciprocal rank fusion (RRF)

**Generic.** You have two ranked lists from two searches. Their scores cannot be added: BM25 scores here run from about 18 to 36, cosine similarities from 0 to 1. RRF ignores scores and uses only ranks: each document earns `1 / (k + rank)` from every list it appears in (k = 60 is the usual constant), and the earned amounts are added. A document that is high in both lists beats one that is first in only one. There is nothing to tune.

**Worked example** (invented, to show the arithmetic). Keyword list: X, Y, Z. Embedding list: Y, W, X.

| document | from keyword | from embeddings | total |
|---|---|---|---|
| Y | 1/62 = 0.01613 | 1/61 = 0.01639 | 0.03252 |
| X | 1/61 = 0.01639 | 1/63 = 0.01587 | 0.03227 |
| W | | 1/62 = 0.01613 | 0.01613 |
| Z | 1/63 = 0.01587 | | 0.01587 |

The fused order is Y, X, W, Z: Y wins by being second in one list and first in the other. **Here:** R2 asks whether this helps on legal text. Not yet run.

## 4. Reranking

**Generic.** An embedding model (a **bi-encoder**) reads the question and each chunk separately, which is why the chunk vectors can be computed once in advance. A **reranker** (a **cross-encoder**) reads the question and one chunk *together* and outputs a relevance score, which is more accurate because it can compare them word by word. The price: nothing can be precomputed, so it must run once per candidate for every question. The usual pattern is to retrieve 30 to 50 candidates cheaply and rerank only those.

**Here.** R5 tests whether re-ordering the top 30 puts the right provision into the top five often enough to justify the extra time. Not yet run.

## 5. Latency

**Generic.** Latency is the time from a question to its answer, measured in percentiles because the average hides slow cases: p50 is the typical request and p95 the slow tail. It is a sum of stages: embedding the question, searching, reranking, and (usually the largest) the language model generating the answer. Each stage added for accuracy must pay for its delay.

**Here.** BM25 is already in the milliseconds. Query embedding is one call (a network round trip if hosted, a short computation if local); reranking is the stage most likely to cost real time, because it runs 30 passes per question. We have not measured any of these yet; R5 will report latency next to accuracy, and Phase 5 logs it for every real query.

## 6. What this means for the design

- The current baseline (R1.1, BM25) is weak (recall@5 0.24), and the failures are the kind embeddings are designed to fix (vocabulary and language). That is a prediction, not a result.
- Copies of one provision cost slots, so duplicate handling (R10) and the index version policy (R8) may matter as much as the choice of model.
- With only 31 development questions, only large improvements will be detectable; the decision rule in `docs/PHASE3_PLAN.md` is written for that.

## 7. In plain words (written after the owner asked for the basics)

### Words used above
- **Corpus:** all the law texts we hold. **Chunk:** one searchable piece of it (about 240 words). **Index:** the prepared list of all chunks that the search runs over.
- **Query:** the question typed in. **Rank:** a result's place in the list (1 = best). **Top k:** the first k results (top 5 = the first five).

### Who sets the weight of a word in keyword search?
Nobody sets it by hand. The weight is worked out automatically from the corpus: count how many chunks contain the word, and the fewer there are, the more the word is worth. A word found in nearly every chunk ("the") says nothing about which chunk is the answer; a word found in a few ("designate") says a lot. Then each chunk is scored by adding up the weights of the question's words that it contains (a word that appears several times counts a little more each time, up to a limit, and long chunks are slightly discounted), and the chunks are listed from highest score to lowest.

A tiny invented example. Question: "designate data officer". Weights worked out from the corpus (invented numbers): designate 4.5, officer 4.0, data 0.8.

| chunk | words it contains from the question | score |
|---|---|---|
| A "the controller shall designate a data protection officer" | designate, data, officer | 4.5 + 0.8 + 4.0 = 9.3 |
| B "the data subject has the right to data portability" | data | 0.8 |
| C "the data controller and the data processor" | data | 0.8 |

A wins because it matches the rare, meaningful words. This is also why keyword search fails when a question uses different words for the same idea: it only sees matching letters, not meaning.

### The scores that measure retrieval
Each one answers a different plain question about the list of results a search returned. Example used below: a question needs two provisions, A and B. The search returned five chunks in this order: wrong, **A**, wrong, **B**, wrong.

| Score | The plain question it answers | In the example | Why we care |
|---|---|---|---|
| **hit@k** | Is at least one right answer somewhere in the first k? (yes = 1, no = 0) | hit@1 = 0, hit@2 = 1, hit@5 = 1 | "Did it find anything useful at all?" |
| **recall@k** | Of everything the question needed, what share is in the first k? | recall@3 = 1 of 2 = 0.5, recall@5 = 2 of 2 = 1.0 | "Did it find all the pieces the answer needs?" Our main score, at k = 5, because the answer-writing model will be given about five chunks. |
| **MRR** (mean reciprocal rank) | How near the top is the first right answer? Score = 1 divided by its place, averaged over all questions | first right answer at place 2, so 1/2 = 0.5 | "How soon does a user see something useful?" |
| **nDCG@k** | How good is the whole ordering compared with the best possible one? A right answer counts for less the lower it sits (divided by log base 2 of place + 1), then the total is divided by the best possible total, so 1 is perfect | right answers at places 2 and 4: 0.631 + 0.431 = 1.062; best possible (places 1 and 2): 1 + 0.631 = 1.631; so 1.062 / 1.631 = 0.65 | "Are the best results at the top, not just somewhere in the list?" (In our version a main provision counts 3 and an acceptable extra counts 1.) |

Our headline number, **recall@5 = 0.24**, means: on average, 24 % of the provisions a question needs were in the top five results.

**The interval** (for example 0.12 to 0.39) answers a different question: with only 31 questions, how much could this number move if we had a different 31? It is the range the true value probably lies in. A wide range means we know little; an improvement counts only if it is clearly bigger than that wobble.

### The vector length: who decides, and is it fixed?
Think of a map. Two numbers (how far east, how far north) pin a place on a flat map, and places that are near each other on the map are near in the world. An embedding gives a text a position on a "map of meaning" that has hundreds of directions instead of two. Texts with similar meaning sit near each other. No single number means anything a person could name; it is the whole list that places the text.

- **The model's designers decide the length**, when they build and train the model (for example 384, 768, 1,024 or 3,072 numbers). More numbers can capture more nuance but need more memory and time. It is fixed for a given model.
- **We decide only which model to use**, and so indirectly the length. Some newer models let you ask for a shorter vector at a small cost in quality.
- **Everything must use the same model.** Vectors from different models live on different maps and cannot be compared, so the chunks and the questions must be embedded by the same model, and changing model means re-embedding all chunks.

### Reciprocal rank fusion, in everyday terms
Two friends each give you a ranked list of restaurants, but one scores out of 10 and the other in stars, so you cannot add their scores. Instead you ignore the scores and use only the **places** each gave: a restaurant that is near the top of both lists is probably good, even if neither put it first.

The rule: every list gives each item **1 divided by (60 + its place)** points, and you add the points from all lists. Worked example with four documents:

| document | place in keyword list | place in embedding list | points |
|---|---|---|---|
| A | 1 | 3 | 1/61 + 1/63 = 0.0323 |
| B | 2 | 1 | 1/62 + 1/61 = 0.0325 |
| C | 3 | not listed | 1/63 = 0.0159 |
| D | not listed | 2 | 1/62 = 0.0161 |

Fused order: B, A, D, C. B wins although it was first in only one list, because it was high in both. The 60 is only a smoothing number: it keeps first place from being worth far more than second, so agreement between the lists matters more than one list's first place. Nothing needs tuning. In our project the two lists are the keyword search and the embedding search, and experiment R2 tests whether fusing them finds more of the right law than either alone.
