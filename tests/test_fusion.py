"""
Tests for reciprocal rank fusion (R2): merging ranked lists by place, not by score.
"""

from __future__ import annotations

import pytest

from law_assistant.retrieval.fusion import FusedRetriever, rrf


class Fixed:
    def __init__(self, ranking, name="fixed"):
        self.ranking, self.name, self.asked = list(ranking), name, []

    def search(self, query, k):
        self.asked.append(k)
        return self.ranking[:k]


def test_the_worked_example_from_the_documentation():
    keyword = ["A", "B", "C"]
    embedding = ["B", "D", "A"]
    fused = dict(rrf([keyword, embedding], k=60))
    assert fused["A"] == pytest.approx(1 / 61 + 1 / 63)
    assert fused["B"] == pytest.approx(1 / 62 + 1 / 61)
    assert fused["C"] == pytest.approx(1 / 63) and fused["D"] == pytest.approx(1 / 62)
    assert [d for d, _ in rrf([keyword, embedding], k=60)] == ["B", "A", "D", "C"]


def test_a_document_high_in_both_lists_beats_one_that_is_first_in_only_one():
    order = [d for d, _ in rrf([["X", "Y", "Z"], ["Z", "Y", "W"]])]
    assert order.index("Y") < order.index("X") and order.index("Y") < order.index("W")


def test_ties_are_broken_by_id_so_results_are_reproducible():
    assert [d for d, _ in rrf([["b"], ["a"]])] == ["a", "b"]


def test_a_list_can_be_given_more_weight():
    plain = [d for d, _ in rrf([["A", "B"], ["B", "A"]])]
    weighted = [d for d, _ in rrf([["A", "B"], ["B", "A"]], weights=[1.0, 3.0])]
    assert plain == ["A", "B"] and weighted == ["B", "A"]
    with pytest.raises(ValueError, match="weights"):
        rrf([["A"], ["B"]], weights=[1.0])


def test_an_empty_input_gives_an_empty_result():
    assert rrf([]) == [] and rrf([[], []]) == []


def test_the_fused_retriever_asks_each_retriever_for_its_depth_and_returns_the_top_k():
    first, second = Fixed(["A", "B", "C", "D"], "kw"), Fixed(["B", "E", "A"], "emb")
    fused = FusedRetriever([first, second], depth=30)
    assert fused.search("q", 2) == ["B", "A"]
    assert first.asked == [30] and second.asked == [30]
    assert fused.name == "rrf(kw+emb)"


def test_a_document_missing_from_one_list_still_counts_from_the_other():
    fused = FusedRetriever([Fixed(["A"]), Fixed(["B"])], depth=5)
    assert fused.search("q", 5) == ["A", "B"]
