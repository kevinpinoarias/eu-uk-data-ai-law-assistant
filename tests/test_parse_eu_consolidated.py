"""
Tests for the EU consolidated-text parser, on a fixture built from EUR-Lex's consolidated markup: paragraphs as
`div.norm` with a number span, lists as two-column grids, amendment markers (▼B, ►C1) that must not reach the text,
footnote markers, inserted articles such as "3a", and an annex.
The checks against the full downloaded files live in test_parse_eu_consolidated_real.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from law_assistant.parse.eu_consolidated import parse_eu_consolidated

FIXTURE = Path(__file__).parent / "fixtures" / "eu_consolidated_sample.xhtml"


@pytest.fixture(scope="module")
def provisions():
    return parse_eu_consolidated(
        FIXTURE.read_bytes(), instrument="eu-test", language="en", version="consolidated-20260727"
    )


def find(provisions, id_):
    matches = [p for p in provisions if p.id == id_]
    assert len(matches) == 1, f"{id_}: {[p.id for p in provisions]}"
    return matches[0]


def test_a_numbered_paragraph_keeps_its_number_as_a_label_and_its_text_clean(provisions):
    p = find(provisions, "eu-test/art-1/1")
    assert (p.unit, p.kind, p.path) == ("article", "paragraph", ("1", "1"))
    assert p.text == "This Regulation lays down rules relating to:"
    assert p.heading == "Subject-matter"
    assert p.chapter == "CHAPTER I — General provisions"
    assert p.version == "consolidated-20260727"


def test_lettered_points_are_read_from_the_two_column_grid(provisions):
    assert find(provisions, "eu-test/art-1/1/a").text == "the protection of natural persons; and"
    assert find(provisions, "eu-test/art-1/1/b").text == "the free movement of such data."


def test_a_paragraph_after_the_list_at_article_level_is_closing_text_of_the_paragraph_above(provisions):
    closing = find(provisions, "eu-test/art-1/1~closing")
    assert (closing.kind, closing.path) == ("closing", ("1", "1"))
    assert closing.text == "The first subparagraph is without prejudice to national law."


def test_amendment_markers_and_footnote_markers_never_reach_the_text(provisions):
    assert find(provisions, "eu-test/art-1/2").text == "This Regulation protects fundamental rights."
    assert not any("▼" in p.text or "►" in p.text for p in provisions)


def test_an_unnumbered_article_with_a_list_keeps_its_intro_and_definitions(provisions):
    intro = find(provisions, "eu-test/art-2")
    assert (intro.kind, intro.heading, intro.text) == (
        "article",
        "Definitions",
        "For the purposes of this Regulation:",
    )
    assert find(provisions, "eu-test/art-2/1").text == "‘data’ means any information;"


def test_nested_lists_and_continuation_text_inside_a_list_item(provisions):
    parent = find(provisions, "eu-test/art-2/2")
    assert parent.text == "‘controller’ means a body which, alone or jointly:"
    assert find(provisions, "eu-test/art-2/2/a").text == "determines the purposes; or"
    assert (
        find(provisions, "eu-test/art-2/2/b").text == "determines the means; Both may be exercised together."
    )


def test_a_one_paragraph_article_and_an_inserted_article_with_a_letter(provisions):
    assert find(provisions, "eu-test/art-3").chapter == "CHAPTER II — Principles"
    inserted = find(provisions, "eu-test/art-3a")
    assert (inserted.path, inserted.text) == (("3a",), "An article inserted by an amending act.")


def test_an_annex_keeps_title_intro_items_and_nested_items(provisions):
    intro = find(provisions, "eu-test/anx-I")
    assert (intro.unit, intro.kind, intro.heading) == ("annex", "annex", "List of areas")
    assert intro.text == "The following areas are listed:"
    assert find(provisions, "eu-test/anx-I/1").text == "Biometrics:"
    assert (
        find(provisions, "eu-test/anx-I/1/a").text
        == "remote identification systems. This does not include verification."
    )


def test_the_disclaimer_is_not_part_of_any_provision_and_nothing_is_duplicated(provisions):
    assert not any("documentation tool" in p.text for p in provisions)
    assert len({p.id for p in provisions}) == len(provisions)
    assert [p.order for p in provisions] == sorted(p.order for p in provisions)


def test_inline_amendment_marks_and_the_empty_brackets_left_by_footnote_markers_are_removed(provisions):
    assert find(provisions, "eu-test/art-4/1").text.startswith("The criteria requirements apply.")


def test_a_paragraph_after_a_list_free_paragraph_continues_it_instead_of_being_closing_text(provisions):
    # the Official Journal keeps such a second subparagraph inside the paragraph; the skeletons must agree
    p = find(provisions, "eu-test/art-4/1")
    assert not any(q.id == "eu-test/art-4/1~closing" for q in provisions)
    assert find(provisions, "eu-test/art-4/2").text == "Paragraph two."
    assert p.text == "The criteria requirements apply. A second subparagraph without any list."


def test_numbered_paragraph_points_and_the_lettered_grid_items_under_them(provisions):
    assert find(provisions, "eu-test/art-5").text == "A efectos del presente Reglamento:"
    assert find(provisions, "eu-test/art-5/1").text == "«datos»: toda información;"
    assert find(provisions, "eu-test/art-5/2/a").text == "determine los fines; o"
    assert find(provisions, "eu-test/art-5/2/b").path == ("5", "2", "b")
    assert find(provisions, "eu-test/art-5/3").text == "«encargado»: quien trata datos."


def test_annex_sections_and_dotted_numbering_become_part_of_the_path(provisions):
    section_a = find(provisions, "eu-test/anx-II/A")
    assert section_a.text.startswith("Information from providers")
    assert find(provisions, "eu-test/anx-II/A/1").text == "The name of the provider;"
    assert find(provisions, "eu-test/anx-II/B/1").text == "The name of the deployer;"
    quality = find(provisions, "eu-test/anx-II/3")
    assert quality.text.startswith("Quality management system")
    assert find(provisions, "eu-test/anx-II/3/3.1").text == "The application shall include:"
    assert find(provisions, "eu-test/anx-II/3/3.1/a").text == "the name of the provider;"


def test_lettered_points_written_as_paragraphs_sit_under_the_numbered_point_above(provisions):
    assert find(provisions, "eu-test/art-6/1").text == "«establecimiento principal»:"
    assert find(provisions, "eu-test/art-6/1/a").text == "el lugar de su administración central; o"
    assert find(provisions, "eu-test/art-6/1/b").path == ("6", "1", "b")
    assert find(provisions, "eu-test/art-6/2").path == ("6", "2")


def test_definitions_laid_out_as_a_label_and_text_table_are_points_with_nested_grid_items(provisions):
    # the Spanish consolidated GDPR Article 4 uses dlist-term | dlist-definition tables
    assert find(provisions, "eu-test/art-7/1").text == "«datos» : toda información;"
    assert find(provisions, "eu-test/art-7/2").text == "«establecimiento» :"
    assert find(provisions, "eu-test/art-7/2/a").text == "el lugar de su administración;"
    assert find(provisions, "eu-test/art-7/2/b").path == ("7", "2", "b")


def test_a_table_of_data_is_kept_row_by_row_as_closing_text(provisions):
    assert find(provisions, "eu-test/art-8").text == "The codes are the following:"
    assert find(provisions, "eu-test/art-8~closing").text == "Code | Description"
    assert find(provisions, "eu-test/art-8~closing2").text == "AIP 0102 | First description"
