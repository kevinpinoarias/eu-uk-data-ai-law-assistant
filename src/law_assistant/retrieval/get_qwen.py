"""
Download the Qwen3-Embedding-0.6B files that are needed (about 1.2 GB, from
huggingface.co/Qwen/Qwen3-Embedding-0.6B, Apache-2.0 licence) into data/models/qwen3-embedding-0.6b:
`python -m law_assistant.retrieval.get_qwen`. Requires the optional extra
(`pip install -e ".[open-embeddings]"`). Only the weights, configuration and tokenizer files are fetched,
not the README.
"""

from __future__ import annotations

from pathlib import Path

from law_assistant import settings

REPO = "Qwen/Qwen3-Embedding-0.6B"
TARGET = settings.PROJECT_ROOT / "data" / "models" / "qwen3-embedding-0.6b"
FILES = (
    "config.json",
    "generation_config.json",
    "model.safetensors",  # 1.19 GB
    "tokenizer.json",
    "tokenizer_config.json",
    "vocab.json",
    "merges.txt",
    "modules.json",
    "1_Pooling/config.json",
)


def download(target: Path = TARGET) -> Path:
    from huggingface_hub import snapshot_download

    return Path(snapshot_download(repo_id=REPO, local_dir=str(target), allow_patterns=list(FILES)))


if __name__ == "__main__":
    print("downloaded to", download())
