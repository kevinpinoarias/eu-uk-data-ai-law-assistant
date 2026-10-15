"""
Tests for step 6 of the answer layer: deterministic checks on an answer before anyone sees it. No model, so
every rule can be tested with small hand-made cases.
"""

from __future__ import annotations

from law_assistant.answer.verify import Citation, normalise, verify_citations
from law_assistant.chunk.chunker import Chunk


def chunk(cid: str, text: str, citation: str = "Article 6", context: str = "GDPR | Article 6") -> Chunk:
    return Chunk(
        id=cid, instrument="eu-gdpr", jurisdiction="EU", language="en", version="consolidated",
        unit="article", unit_path=("6",), citation=citation, heading=None, chapter=None, context=context,
        text=text, provision_ids=("eu-gdpr/art-6/1",), part=1, parts=1, words=len(text.split()), order=0,
    )  # fmt: skip


PASSAGES = [
    chunk("c1", "Processing shall be lawful only if the data subject has given consent to the processing."),
    chunk("c2", "The controller shall designate a data protection officer\nwhere the processing is carried out by a public authority."),
]  # fmt: skip


def test_normalise_ignores_case_whitespace_and_typographic_quotes_and_dashes():
    assert normalise("  The  “Data”\nSubject – is ") == normalise('the "data" subject - is')


def test_a_quote_copied_from_the_passage_is_accepted_even_across_a_line_break():
    result = verify_citations(
        [Citation(2, "designate a data protection officer where the processing is carried out")], PASSAGES
    )
    assert [c.chunk.id for c in result.valid] == ["c2"] and not result.invalid


def test_a_quote_that_is_not_in_the_passage_is_rejected_with_the_reason():
    result = verify_citations([Citation(1, "processing is lawful in all cases")], PASSAGES)
    assert not result.valid and result.invalid[0][1] == "the quote is not in the passage"


def test_a_citation_to_a_passage_that_was_not_given_is_rejected():
    result = verify_citations([Citation(7, "anything")], PASSAGES)
    assert result.invalid[0][1] == "there is no passage 7"


def test_an_ellipsis_joins_fragments_that_must_each_appear_in_order():
    ok = Citation(1, "Processing shall be lawful only if ... has given consent")
    out_of_order = Citation(1, "has given consent ... Processing shall be lawful")
    result = verify_citations([ok, out_of_order], PASSAGES)
    assert len(result.valid) == 1 and result.invalid[0][1] == "the quote is not in the passage"


def test_a_very_short_quote_does_not_count_as_support():
    result = verify_citations([Citation(1, "the")], PASSAGES)
    assert result.invalid[0][1] == "the quote is too short to support a claim"


def test_the_same_passage_cited_twice_is_listed_once_in_the_sources():
    cites = [Citation(1, "Processing shall be lawful only if"), Citation(1, "has given consent")]
    result = verify_citations(cites, PASSAGES)
    assert [c.id for c in result.sources] == ["c1"] and len(result.valid) == 2


def test_the_context_line_can_be_quoted_too_because_the_reader_was_shown_it():
    result = verify_citations([Citation(1, "GDPR | Article 6")], PASSAGES + [])
    assert len(result.valid) == 1
