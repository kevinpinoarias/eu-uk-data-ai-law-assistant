"""Choosing which documents a fetch command runs: all by default, or only the keys asked for."""

from __future__ import annotations

import pytest

from law_assistant.fetch.documents import SourceDocument
from law_assistant.fetch.runner import select_documents


def _doc(key: str) -> SourceDocument:
    return SourceDocument(
        key=key,
        title=key,
        source="s",
        url=f"https://example.org/{key}",
        suffix=".xml",
        licence="l",
        credit="c",
    )


DOCS = (_doc("a"), _doc("b"), _doc("c"))


def test_no_selection_means_every_document():
    assert select_documents(DOCS, None) == list(DOCS)


def test_only_the_requested_keys_are_chosen_in_manifest_order():
    assert [d.key for d in select_documents(DOCS, ["c", "a"])] == ["a", "c"]


def test_an_unknown_key_is_an_error_that_names_it():
    with pytest.raises(ValueError, match="zzz"):
        select_documents(DOCS, ["a", "zzz"])
