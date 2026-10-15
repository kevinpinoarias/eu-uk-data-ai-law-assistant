"""
Tests for the question-rewriting retriever (R6) and for the stored rewrites.
"""

from __future__ import annotations

import json
import re

import pytest

from law_assistant import settings
from law_assistant.evaluation.gold import read_gold
from law_assistant.retrieval.rewrite import RewriteRetriever, read_rewrites
from law_assistant.retrieval.runner import select

REWRITES = settings.PROJECT_ROOT / "eval" / "rewrites" / "r6_dev.jsonl"


class Recorder:
    name = "inner"

    def __init__(self):
        self.asked = []

    def search(self, query, k):
        self.asked.append((query, k))
        return ["a", "b"][:k]


def test_replace_sends_only_the_rewrite_to_the_search():
    inner = Recorder()
    retriever = RewriteRetriever(inner, {"my question": "legal wording"}, mode="replace")
    assert retriever.search("my question", 2) == ["a", "b"]
    assert inner.asked == [("legal wording", 2)]
    assert retriever.name == "rewrite-replace(inner)"


def test_append_sends_the_question_and_then_the_rewrite_as_one_text():
    inner = Recorder()
    RewriteRetriever(inner, {"my question": "legal wording"}, mode="append").search("my question", 1)
    assert inner.asked == [("my question\nlegal wording", 1)]


def test_a_question_without_a_rewrite_is_an_error_not_a_silent_fallback():
    with pytest.raises(KeyError, match="no rewrite"):
        RewriteRetriever(Recorder(), {}, mode="replace").search("unknown", 1)


def test_an_unknown_mode_is_refused():
    with pytest.raises(ValueError, match="mode"):
        RewriteRetriever(Recorder(), {}, mode="other")


def test_read_rewrites_maps_question_text_to_rewrite(tmp_path):
    f = tmp_path / "r.jsonl"
    f.write_text(json.dumps({"id": "q1", "rewrite": "R"}) + "\n", encoding="utf-8")
    questions = [type("Q", (), {"id": "q1", "text": "T"})()]
    assert read_rewrites(f, questions) == {"T": "R"}
    with pytest.raises(ValueError, match="q2"):
        read_rewrites(f, [*questions, type("Q", (), {"id": "q2", "text": "U"})()])


def test_the_stored_rewrites_cover_exactly_the_development_retrieval_questions():
    dev = {q.id for q in select(read_gold(settings.GOLD_DIR / "questions.jsonl"), "dev")}
    stored = {json.loads(line)["id"] for line in REWRITES.read_text(encoding="utf-8").splitlines() if line}
    assert stored == dev


def test_the_stored_rewrites_cite_no_article_numbers():
    pattern = re.compile(r"\b(art(?:icle|ículo|iculo|\.)?|section|sección|seccion|s\.)\s*\d", re.IGNORECASE)
    for line in REWRITES.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        assert not pattern.search(row["rewrite"]), row["id"]
