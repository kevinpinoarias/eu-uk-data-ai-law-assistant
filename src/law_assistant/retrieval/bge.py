"""
BGE-M3 (BAAI, MIT licence) as an embedding model that runs on this machine: no key, no network once the files
are downloaded. It needs no instruction prefix: a passage is its context line and its text, and a
question is the question. Its vectors have 1,024 numbers and it reads up to 8,192 tokens.

BGEEmbedder is a thin wrapper that groups texts of similar length into batches (less padding, so faster,
and the longest batch first so a memory problem shows at once) and returns the vectors in the original
order. The actual model call is an injectable function so the wrapper can be tested without PyTorch; `load`
builds the real one (PyTorch and transformers are imported only there, because they are an optional extra
of the project).
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path

from law_assistant.chunk.chunker import Chunk

MODEL_NAME = "bge-m3"
Encode = Callable[[list[str]], list[list[float]]]


def document_prompt(chunk: Chunk, *, with_context: bool = True) -> str:
    return chunk.embed_text if with_context and chunk.context else chunk.text


def query_prompt(text: str) -> str:
    return text


class BGEEmbedder:
    name = MODEL_NAME

    def __init__(self, encode: Encode, *, batch_size: int = 16) -> None:
        self._encode, self.batch_size = encode, batch_size

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        order = sorted(range(len(texts)), key=lambda i: -len(texts[i]))
        vectors: dict[int, list[float]] = {}
        for start in range(0, len(order), self.batch_size):
            indices = order[start : start + self.batch_size]
            batch = [texts[i] for i in indices]
            out = self._encode(batch)
            if len(out) != len(batch):
                raise RuntimeError(f"expected {len(batch)} vectors, got {len(out)}")
            vectors.update(zip(indices, out, strict=True))
        return [vectors[i] for i in range(len(texts))]

    @classmethod
    def load(
        cls, model_dir: Path, *, device: str = "cuda", max_length: int = 1024, batch_size: int = 16
    ) -> BGEEmbedder:
        """Load the downloaded model. Pooling is the first token's vector (the model's own pooling config says
        so, checked after download) followed by scaling to length 1; half precision on a graphics card."""
        import torch
        from transformers import AutoModel, AutoTokenizer

        tokenizer = AutoTokenizer.from_pretrained(str(model_dir))
        dtype = torch.float16 if device == "cuda" else torch.float32
        model = AutoModel.from_pretrained(str(model_dir), torch_dtype=dtype).to(device).eval()

        def encode(texts: list[str]) -> list[list[float]]:
            batch = tokenizer(
                texts, padding=True, truncation=True, max_length=max_length, return_tensors="pt"
            ).to(device)
            with torch.no_grad():
                hidden = model(**batch).last_hidden_state[:, 0]
            hidden = torch.nn.functional.normalize(hidden.float(), p=2, dim=1)
            return hidden.cpu().tolist()

        return cls(encode, batch_size=batch_size)
