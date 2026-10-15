"""The list of reranker files to download: it must hold what loading needs (no network)."""

from __future__ import annotations

from law_assistant.retrieval.get_reranker import FILES, REPO, TARGET


def test_the_download_list_has_the_weights_the_tokenizer_and_the_configuration():
    assert REPO == "BAAI/bge-reranker-v2-m3"
    assert {"model.safetensors", "config.json", "tokenizer.json", "sentencepiece.bpe.model"} <= set(FILES)


def test_the_readme_and_the_images_are_not_downloaded():
    assert not any(f.startswith("assets/") or f == "README.md" for f in FILES)


def test_the_files_go_into_the_git_ignored_models_folder():
    assert TARGET.parts[-3:] == ("data", "models", "bge-reranker-v2-m3")
