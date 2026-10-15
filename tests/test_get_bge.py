"""The list of BGE-M3 files to download: it must hold what loading and the pooling check need (no network)."""

from __future__ import annotations

from law_assistant.retrieval.get_bge import FILES, REPO, TARGET


def test_the_download_list_has_the_weights_the_tokenizer_and_the_pooling_configuration():
    assert REPO == "BAAI/bge-m3"
    assert {
        "pytorch_model.bin",
        "config.json",
        "tokenizer.json",
        "1_Pooling/config.json",
        "modules.json",
    } <= set(FILES)


def test_the_files_go_into_the_git_ignored_models_folder():
    assert TARGET.parts[-3:] == ("data", "models", "bge-m3")
