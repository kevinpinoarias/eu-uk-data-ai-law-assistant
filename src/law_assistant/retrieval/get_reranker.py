"""
Download the BGE reranker files that are needed (about 2.3 GB, from huggingface.co/BAAI/bge-reranker-v2-m3,
Apache-2.0 licence) into data/models/bge-reranker-v2-m3: `python -m law_assistant.retrieval.get_reranker`.
Requires the optional extra (`pip install -e ".[open-embeddings]"`). Only the weights, configuration and
tokenizer files are fetched, not the README or the images in the repository.
"""

from __future__ import annotations

from pathlib import Path

from law_assistant import settings

REPO = "BAAI/bge-reranker-v2-m3"
TARGET = settings.PROJECT_ROOT / "data" / "models" / "bge-reranker-v2-m3"
FILES = (
    "config.json",
    "model.safetensors",  # 2.27 GB
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "sentencepiece.bpe.model",
)


def download(target: Path = TARGET) -> Path:
    from huggingface_hub import snapshot_download

    return Path(snapshot_download(repo_id=REPO, local_dir=str(target), allow_patterns=list(FILES)))


if __name__ == "__main__":
    print("downloaded to", download())
