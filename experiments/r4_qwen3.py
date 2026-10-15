"""
R4.2: a second open embedding model. Does Qwen3-Embedding-0.6B (Alibaba, Apache-2.0, 0.6 billion parameters,
last-token pooling, 1,024 numbers) retrieve better than BGE-M3 (R4.1), or help when fused with it?

PRE-REGISTRATION (written 15 October 2026, before Qwen3-Embedding has embedded any chunk or any question)

Variants (all three counted in the experiment tally), all over the 3,831 chunks, brute-force cosine, passages as
"{context line}\n{chunk text}" with no instruction, sequences cut at 1,024 tokens (the number of chunks cut is
reported), fp16 on the graphics card, vectors cached in data/indexes/qwen3-embedding-0.6b:
  R4.2   Qwen3-Embedding with the model card's instruction in front of each question, the one sentence fixed in
         src/law_assistant/retrieval/qwen.py before any result ("Given a question about EU, UK or Spanish data
         protection or AI law, retrieve the legal provisions that answer it");
  R4.2b  the same model with the question as typed (no instruction), to measure what the instruction is worth;
  R4.3   reciprocal rank fusion (k = 60, equal weights, depth 50) of BGE-M3 and R4.2.
Data: the 3,831 chunks and the 31 development retrieval questions of the frozen gold set (version 2). The test
half is untouched.
Primary metric recall@5; also MRR, nDCG@10, hit@5, recall@10; 95 % bootstrap intervals (10,000 resamples, seed 0).
Paired bootstrap on recall@5 against R4.1 (BGE-M3). Also reported: time to embed the chunks (index build) and the
time to embed one question on the graphics card; breakdowns by language and question type.
Decision rule: Qwen3-Embedding replaces BGE-M3 only if the lower end of R4.2's paired interval against R4.1 is
above 0, and then only after its own confirmation on the test half (a new decision, a new pre-registration); the
fusion is adopted only on the same terms against BGE-M3 alone. Otherwise BGE-M3 stays: it is already confirmed on
the test half, is integrated and measured end to end, and its licence (MIT) is as simple as Apache-2.0.
Stated expectation (can be wrong): R4.2 lands near BGE-M3 (recall@5 0.45 to 0.65) with a paired interval that
includes 0; the instruction helps a little (R4.2 at least as good as R4.2b); the fusion is within 0.05 of the
better model and not detectably better than BGE-M3 alone.

Run: python experiments/r4_qwen3.py [--log]   (needs the Qwen3-Embedding files: python -m law_assistant.retrieval.get_qwen)
"""

from __future__ import annotations

import subprocess
import sys
import time
from datetime import date

from law_assistant import settings
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.metrics import metric_values, paired_bootstrap, write_run
from law_assistant.retrieval import bge, qwen
from law_assistant.retrieval.dense import DenseIndex
from law_assistant.retrieval.fusion import FusedRetriever
from law_assistant.retrieval.report import format_table, summarise_with_ci
from law_assistant.retrieval.runner import breakdown, evaluate, run_retriever, select

K = 10
MODELS = settings.PROJECT_ROOT / "data" / "models"
INDEXES = settings.PROJECT_ROOT / "data" / "indexes"
RUNS = settings.PROJECT_ROOT / "data" / "runs"
LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"
MAX_LENGTH = 1024


class NoInstruction:
    """The same index as R4.2 (same cached passage vectors) but the question is embedded as typed."""

    def __init__(self, index: DenseIndex) -> None:
        self._index, self.name = index, "qwen3-embedding-0.6b-noinstr"

    def search(self, query: str, k: int) -> list[str]:
        return self._index.search(query, k)


def main() -> int:
    import torch
    from transformers import AutoTokenizer

    device = "cuda" if torch.cuda.is_available() else "cpu"
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")

    tokenizer = AutoTokenizer.from_pretrained(str(MODELS / "qwen3-embedding-0.6b"))
    lengths = [len(tokenizer(qwen.document_prompt(c))["input_ids"]) for c in chunks]
    cut = sum(1 for n in lengths if n > MAX_LENGTH)
    print(
        f"chunk lengths in Qwen tokens: mean {sum(lengths) / len(lengths):.0f}, max {max(lengths)}, cut: {cut}"
    )

    bge_index = DenseIndex(
        chunks, bge.BGEEmbedder.load(MODELS / "bge-m3", device=device, max_length=1024), INDEXES / "bge-m3",
        name="bge-m3", document_prompt_fn=bge.document_prompt, query_prompt_fn=bge.query_prompt,
    )  # fmt: skip
    embedder = qwen.QwenEmbedder.load(MODELS / "qwen3-embedding-0.6b", device=device, max_length=MAX_LENGTH)
    started = time.perf_counter()
    qwen_index = DenseIndex(
        chunks, embedder, INDEXES / "qwen3-embedding-0.6b", name="qwen3-embedding-0.6b",
        document_prompt_fn=qwen.document_prompt, query_prompt_fn=qwen.query_prompt,
    )  # fmt: skip
    build_seconds = time.perf_counter() - started
    raw_index = DenseIndex(
        chunks, embedder, INDEXES / "qwen3-embedding-0.6b", name="qwen3-embedding-0.6b",
        document_prompt_fn=qwen.document_prompt, query_prompt_fn=lambda text: text,
    )  # fmt: skip

    base = evaluate(questions, run_retriever(bge_index, questions, k=K), chunks)
    variants = {
        "R4.2 Qwen3-Embedding, with the instruction": qwen_index,
        "R4.2b Qwen3-Embedding, question as typed": NoInstruction(raw_index),
        "R4.3 fusion of BGE-M3 and R4.2": FusedRetriever(
            [bge_index, qwen_index], depth=50, name="rrf(bge-m3+qwen3)"
        ),
    }
    results = {"R4.1 BGE-M3": summarise_with_ci(base)}
    scored = {}
    for name, retriever in variants.items():
        run = run_retriever(retriever, questions, k=K)
        write_run(RUNS / f"r4_2_{name.split()[0].lower().replace('.', '_')}.jsonl", run)
        scored[name] = evaluate(questions, run, chunks)
        results[name] = summarise_with_ci(scored[name])

    start = time.perf_counter()
    for q in questions:
        embedder.embed_texts([qwen.query_prompt(q.text + " ")])  # a fresh text each time: not cached
    per_question = (time.perf_counter() - start) / len(questions)

    out = [
        f"### R4.2 a second embedding model on the development questions ({len(questions)} retrieval questions)",
        "",
        format_table(results),
        "",
    ]
    base_values = metric_values(base, "recall@5")
    for name in variants:
        p = paired_bootstrap(base_values, metric_values(scored[name], "recall@5"))
        out.append(
            f"{name} against R4.1, recall@5: difference {p.difference:+.3f}, 95 % interval "
            f"{p.low:+.3f} to {p.high:+.3f}; share of resamples in which it is not better {p.p_not_better:.2f}."
        )
    out += [
        "",
        f"Chunks cut at {MAX_LENGTH} tokens: {cut} of {len(chunks)}; mean {sum(lengths) / len(lengths):.0f} tokens, "
        f"longest {max(lengths)}. Time to embed the chunks (index build, graphics card, fp16): "
        f"{build_seconds:.0f} s (0 s if the vectors were already saved); time to embed one question: "
        f"{per_question * 1000:.0f} ms.",
    ]
    for title, key in (("question language", lambda q: q.language), ("question type", lambda q: q.type)):
        out += ["", f"Recall@5 by {title} (R4.1, R4.2, R4.2b, R4.3; number of questions):", ""]
        cols = [base, *scored.values()]
        by = [breakdown(questions, s, key, "recall@5") for s in cols]
        out += [
            f"- {name}: " + ", ".join(f"{b[name][0]:.2f}" for b in by) + f" (n = {by[0][name][1]})"
            for name in sorted(by[0])
        ]
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## R4.2 a second embedding model, run {date.today().isoformat()} "
            f"(commit {commit}; gold version {manifest['version']}, fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
        print(f"\nlogged to {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
