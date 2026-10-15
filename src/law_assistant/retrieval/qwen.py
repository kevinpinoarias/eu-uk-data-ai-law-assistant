"""
Qwen3-Embedding-0.6B (Alibaba, Apache-2.0) as a second local embedding model, to compare with BGE-M3
(R4.2). Facts read from its model card on 15 October 2026 and from the downloaded pooling configuration:
1,024 numbers per text, last-token pooling (the final real token's hidden state), padding on the left,
vectors scaled to length 1, no instruction for passages and a one-line task instruction in front of each
question (the card says queries "must come with a one-sentence instruction"). It needs transformers 4.51
or newer.

The batching wrapper is the one BGE-M3 uses (`BGEEmbedder`): texts of similar length are batched together
and the vectors come back in the original order; the actual model call is injected so the wrapper is
tested without PyTorch, and `load` builds the real one (PyTorch is imported only there).
"""

from __future__ import annotations

from pathlib import Path

from law_assistant.chunk.chunker import Chunk
from law_assistant.retrieval.bge import BGEEmbedder

MODEL_NAME = "qwen3-embedding-0.6b"
# One instruction, written before any result was seen and never tuned (R4.2 pre-registration).
INSTRUCTION = (
    "Given a question about EU, UK or Spanish data protection or AI law, retrieve the legal provisions "
    "that answer it"
)


def document_prompt(chunk: Chunk, *, with_context: bool = True) -> str:
    return chunk.embed_text if with_context and chunk.context else chunk.text


def query_prompt(text: str) -> str:
    return f"Instruct: {INSTRUCTION}\nQuery:{text}"


class QwenEmbedder(BGEEmbedder):
    name = MODEL_NAME

    @classmethod
    def load(
        cls, model_dir: Path, *, device: str = "cuda", max_length: int = 1024, batch_size: int = 16
    ) -> QwenEmbedder:
        import torch
        from transformers import AutoModel, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(str(model_dir), padding_side="left")
        dtype = torch.float16 if device == "cuda" else torch.float32
        model = AutoModel.from_pretrained(str(model_dir), dtype=dtype).to(device).eval()

        def encode(texts: list[str]) -> list[list[float]]:
            batch = tokenizer(
                texts, padding=True, truncation=True, max_length=max_length, return_tensors="pt"
            ).to(device)
            with torch.no_grad():
                hidden = model(**batch).last_hidden_state
            mask = batch["attention_mask"]
            if bool(mask[:, -1].all()):  # left padding: the last position is every text's last real token
                pooled = hidden[:, -1]
            else:
                last = mask.sum(dim=1) - 1
                pooled = hidden[torch.arange(hidden.shape[0], device=hidden.device), last]
            return torch.nn.functional.normalize(pooled.float(), p=2, dim=1).cpu().tolist()

        return cls(encode, batch_size=batch_size)
