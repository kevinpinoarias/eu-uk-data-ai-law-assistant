"""
Download the BGE-M3 files that are needed (about 2.3 GB, from huggingface.co/BAAI/bge-m3, MIT licence) into
data/models/bge-m3: `python -m law_assistant.retrieval.get_bge`. Requires the optional extra
(`pip install -e ".[open-embeddings]"`). Only the weights, configuration and tokenizer files are fetched,
not the other retrieval modes or the images in the repository.
"""

from __future__ import annotations

from pathlib import Path

from law_assistant import settings

REPO = "BAAI/bge-m3"
TARGET = settings.PROJECT_ROOT / "data" / "models" / "bge-m3"
FILES = (
    "config.json",
    "pytorch_model.bin",  # 2.27 GB
    "tokenizer.json",
    "tokenizer_config.json",
    "special_tokens_map.json",
    "sentencepiece.bpe.model",
    "modules.json",
    "sentence_bert_config.json",
    "config_sentence_transformers.json",
    "1_Pooling/config.json",
)


def download(target: Path = TARGET) -> Path:
    from huggingface_hub import snapshot_download

    return Path(snapshot_download(repo_id=REPO, local_dir=str(target), allow_patterns=list(FILES)))


if __name__ == "__main__":
    print("downloaded to", download())
