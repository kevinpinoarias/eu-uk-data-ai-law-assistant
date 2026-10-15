"""The list of Qwen3-Embedding files to download: it must hold what loading and the pooling check need (no network)."""

from __future__ import annotations

from law_assistant.retrieval.get_qwen import FILES, REPO, TARGET


def test_the_download_list_has_the_weights_the_tokenizer_and_the_pooling_configuration():
    assert REPO == "Qwen/Qwen3-Embedding-0.6B"
    assert {
        "model.safetensors", "config.json", "tokenizer.json", "vocab.json", "merges.txt", "1_Pooling/config.json",
    } <= set(FILES)  # fmt: skip


def test_the_readme_is_not_downloaded_and_the_files_go_into_the_git_ignored_models_folder():
    assert "README.md" not in FILES
    assert TARGET.parts[-3:] == ("data", "models", "qwen3-embedding-0.6b")
