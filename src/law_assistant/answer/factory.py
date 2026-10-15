"""
Build the real answer pipeline from what is on this machine: the parsed chunks, the BGE-M3 model and its
saved vectors, the facts table, and the Gemini key in `.env`. Heavy imports (PyTorch, transformers) happen
only here, so importing the rest of the package stays light.

`version_aware` and `include_dates` are off by default: the repairs for questions dated before the 2026
amendment and for 'since when' questions are built and tested but not yet measured (decisions 90 and 98), so
the shipped default is the configuration that was measured.
"""

from __future__ import annotations

from law_assistant import settings
from law_assistant.answer.facts_lookup import LLMFactPicker
from law_assistant.answer.generate import AnswerWriter
from law_assistant.answer.pipeline import AnswerPipeline
from law_assistant.answer.router import LLMRouter
from law_assistant.chunk.store import read_chunks
from law_assistant.facts.table import read_facts
from law_assistant.llm.gemini import GeminiGenerator
from law_assistant.retrieval.bge import BGEEmbedder, document_prompt, query_prompt
from law_assistant.retrieval.dense import DenseIndex
from law_assistant.retrieval.policies import CollapsedRetriever, before_amendment_text, current_text_only


def build_pipeline(
    *, k: int = 5, version_aware: bool = False, include_dates: bool = False, device: str | None = None
):
    """Return (pipeline, generator); the generator is returned so callers can read tokens and timings."""
    import torch

    settings.load_env_file()
    device = device or ("cuda" if torch.cuda.is_available() else "cpu")
    chunks = [c for f in sorted(settings.CHUNKS_DIR.glob("*.jsonl")) for c in read_chunks(f)]
    by_id = {c.id: c for c in chunks}
    embedder = BGEEmbedder.load(settings.PROJECT_ROOT / "data" / "models" / "bge-m3", device=device)
    store = settings.PROJECT_ROOT / "data" / "indexes" / "bge-m3"

    def search(cs, name):
        index = DenseIndex(
            cs, embedder, store, name=name, document_prompt_fn=document_prompt,
            query_prompt_fn=query_prompt, persist_queries=False,
        )  # fmt: skip
        return CollapsedRetriever(index, by_id, by="copies", depth=50)

    generator = GeminiGenerator.from_env()
    facts = read_facts(settings.FACTS_DIR / "legal_facts.jsonl")
    pipeline = AnswerPipeline(
        router=LLMRouter(generator),
        picker=LLMFactPicker(facts, generator),
        current=search(current_text_only(chunks), "bge-m3-current"),
        full=search(chunks, "bge-m3"),
        original=search(before_amendment_text(chunks), "bge-m3-original"),
        writer=AnswerWriter(generator, include_dates=include_dates),
        chunks=chunks,
        k=k,
        version_aware=version_aware,
    )
    return pipeline, generator
