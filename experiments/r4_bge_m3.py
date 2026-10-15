"""
R4, first candidate: BGE-M3 (BAAI, open, on this machine). How well does it retrieve on the development
questions, compared with BM25 (R1.1)? Same protocol as R1.3 (gemini-embedding-2) so the two models can be
compared.

PRE-REGISTRATION (written 15 October 2026, before the model has embedded any chunk; see docs/PHASE3_PLAN.md)

Variant: BGE-M3 on the graphics card in half precision, the first token's vector scaled to length 1 (its
pooling configuration is read from the downloaded files and must say CLS pooling and normalisation, else
stop), vectors of 1,024 numbers, no instruction prefix, sequences cut at 1,024 tokens (the number of chunks
that are cut is reported), brute-force cosine. Passage text "{context line}\n{chunk text}", question text as
typed. Vectors cached in data/indexes/bge-m3.
Data: the 3,831 chunks and the 31 development retrieval questions of the frozen gold set. Test half untouched.

Primary metric recall@5; also MRR, nDCG@10, hit@5, recall@10; 95 % bootstrap intervals (10,000 resamples,
seed 0). Paired bootstrap against R1.1 on recall@5. Breakdowns as in R1.

Decision rule: R4 adopts nothing from one model alone. BGE-M3 is recorded as a candidate; the model choice is
made when all R4 candidates have run, by the paired comparison on recall@5 (a model is preferred over another
only if the lower end of its paired interval is above 0; otherwise the free, local, simpler one is preferred).

Stated expectation (can be wrong): BGE-M3 beats BM25 on recall@5 with a lower paired bound above 0, most on
lay-worded and cross-language questions, and stays below 0.9.

Run: python experiments/r4_bge_m3.py [--log]
"""

from __future__ import annotations

import subprocess
import sys
from datetime import date

from law_assistant import settings
from law_assistant.chunk.store import read_chunks
from law_assistant.evaluation.checks import Corpus, overlap_ratio
from law_assistant.evaluation.freeze import read_manifest
from law_assistant.evaluation.gold import read_gold
from law_assistant.evaluation.metrics import metric_values, paired_bootstrap, write_run
from law_assistant.retrieval.bge import BGEEmbedder, document_prompt, query_prompt
from law_assistant.retrieval.bm25 import BM25Index
from law_assistant.retrieval.dense import DenseIndex
from law_assistant.retrieval.report import format_table, summarise_with_ci
from law_assistant.retrieval.runner import breakdown, evaluate, run_retriever, select

K = 10
MODEL_DIR = settings.PROJECT_ROOT / "data" / "models" / "bge-m3"
STORE = settings.PROJECT_ROOT / "data" / "indexes" / "bge-m3"
RUNS = settings.PROJECT_ROOT / "data" / "runs"
LOG = settings.PROJECT_ROOT / "docs" / "EXPERIMENTS.md"
MAX_LENGTH = 1024


def check_pooling() -> None:
    import json

    pooling = json.loads((MODEL_DIR / "1_Pooling" / "config.json").read_text(encoding="utf-8"))
    modules = json.loads((MODEL_DIR / "modules.json").read_text(encoding="utf-8"))
    cls_pooling = pooling.get("pooling_mode_cls_token") is True
    normalises = any("Normalize" in m.get("type", "") for m in modules)
    print(f"pooling config: CLS token {cls_pooling}, normalisation module {normalises}")
    if not cls_pooling:
        raise SystemExit("the model's pooling is not CLS; stop (see the pre-registration)")


def main() -> int:
    import torch
    from transformers import AutoTokenizer

    check_pooling()
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print("device:", device, torch.cuda.get_device_name(0) if device == "cuda" else "")
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    questions = select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")
    manifest = read_manifest(settings.GOLD_DIR / "MANIFEST.json")

    tokenizer = AutoTokenizer.from_pretrained(str(MODEL_DIR))
    lengths = [len(tokenizer(document_prompt(c))["input_ids"]) for c in chunks]
    print(
        f"chunk lengths in tokens: mean {sum(lengths) / len(lengths):.0f}, max {max(lengths)}, "
        f"cut at {MAX_LENGTH}: {sum(1 for n in lengths if n > MAX_LENGTH)} chunks"
    )

    embedder = BGEEmbedder.load(MODEL_DIR, device=device, max_length=MAX_LENGTH)
    index = DenseIndex(
        chunks, embedder, STORE, name="bge-m3",
        document_prompt_fn=document_prompt, query_prompt_fn=query_prompt,
    )  # fmt: skip
    run = run_retriever(index, questions, k=K)
    write_run(RUNS / "r4_bge-m3.jsonl", run)
    scores = evaluate(questions, run, chunks)
    bm25 = evaluate(questions, run_retriever(BM25Index(chunks, name="bm25-plain"), questions, k=K), chunks)

    results = {"R1.1 BM25 plain": summarise_with_ci(bm25), "R4.1 BGE-M3": summarise_with_ci(scores)}
    paired = paired_bootstrap(metric_values(bm25, "recall@5"), metric_values(scores, "recall@5"))
    corpus = Corpus.from_dir()

    def shared_words(q) -> str:
        texts = [t for g in q.gold if g.role == "primary" for t in corpus.unit_texts(g, q.language)]
        many = overlap_ratio(q.text, texts, corpus.idf(q.language)) >= 0.25
        return "shares many words" if many else "shares few words"

    out = [
        f"### R4.1 BGE-M3 on the development questions ({len(questions)} retrieval questions)",
        "",
        format_table(results),
        "",
        f"R4.1 against R1.1, recall@5: difference {paired.difference:+.3f}, 95 % interval "
        f"{paired.low:+.3f} to {paired.high:+.3f}; share of resamples in which BGE-M3 is not better "
        f"{paired.p_not_better:.2f}.",
        f"Chunks cut at {MAX_LENGTH} tokens: {sum(1 for n in lengths if n > MAX_LENGTH)} of {len(chunks)}.",
    ]
    groupings = (
        ("question type", lambda q: q.type),
        ("question language", lambda q: q.language),
        ("shared words with its gold text", shared_words),
    )
    for title, key in groupings:
        out += ["", f"Recall@5 by {title} (R1.1 BM25, R4.1 BGE-M3; number of questions):", ""]
        by1 = breakdown(questions, bm25, key, "recall@5")
        by2 = breakdown(questions, scores, key, "recall@5")
        out += [
            f"- {name}: {by1[name][0]:.2f}, {by2[name][0]:.2f} (n = {by1[name][1]})" for name in sorted(by1)
        ]
    report = "\n".join(out)
    print(report)
    if "--log" in sys.argv:
        git = ["git", "rev-parse", "--short", "HEAD"]
        commit = subprocess.run(git, capture_output=True, text=True).stdout.strip()
        header = (
            f"\n\n## R4.1 BGE-M3, run {date.today().isoformat()} "
            f"(commit {commit}; gold fingerprint {manifest['sha256'][:8]})\n\n"
        )
        LOG.write_text(LOG.read_text(encoding="utf-8") + header + report + "\n", encoding="utf-8")
        print(f"\nlogged to {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
