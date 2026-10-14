"""
Tests for the EU Official Journal parser, on a small fixture built from the real markup: recitals as two-column
tables, chapters, articles with numbered paragraphs, lettered points, nested points, closing text and an annex.
The checks against the full downloaded files live in test_parse_eu_real.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from law_assistant.parse.eu_oj import parse_eu_oj

FIXTURE = Path(__file__).parent / "fixtures" / "eu_oj_sample.xhtml"


@pytest.fixture(scope="module")
def provisions():
    return parse_eu_oj(FIXTURE.read_bytes(), instrument="eu-test", language="en", version="oj")


def find(provisions, id_):
    matches = [p for p in provisions if p.id == id_]
    assert len(matches) == 1, f"{id_}: {[p.id for p in provisions]}"
    return matches[0]


def test_recitals_are_read_from_their_two_column_tables(provisions):
    r1 = find(provisions, "eu-test/rct-1")
    assert (r1.unit, r1.kind, r1.path) == ("recital", "recital", ("1",))
    assert r1.text == "The protection of natural persons is a fundamental right."


def test_whitespace_is_normalised_and_footnote_markers_are_dropped(provisions):
    assert find(provisions, "eu-test/rct-2").text == (
        "The principles of protection should respect fundamental rights."
    )


def test_a_numbered_paragraph_loses_its_number_and_keeps_its_article_and_chapter(provisions):
    p = find(provisions, "eu-test/art-1/1")
    assert (p.unit, p.kind, p.path) == ("article", "paragraph", ("1", "1"))
    assert p.text == "This Regulation lays down rules relating to:"
    assert p.heading == "Subject-matter"
    assert p.chapter == "CHAPTER I — General provisions"


def test_lettered_points_sit_under_their_paragraph(provisions):
    a = find(provisions, "eu-test/art-1/1/a")
    assert (a.kind, a.path, a.text) == ("point", ("1", "1", "a"), "the protection of natural persons; and")
    assert find(provisions, "eu-test/art-1/1/b").text == "the free movement of such data."


def test_text_after_a_list_is_kept_as_closing_text_of_that_paragraph(provisions):
    closing = find(provisions, "eu-test/art-1/1~closing")
    assert (closing.kind, closing.path) == ("closing", ("1", "1"))
    assert closing.text == "The first subparagraph is without prejudice to national law."


def test_a_second_paragraph_is_read_from_its_own_container(provisions):
    assert find(provisions, "eu-test/art-1/2").text == "This Regulation protects fundamental rights."


def test_an_article_without_numbered_paragraphs_keeps_its_intro_text_and_points(provisions):
    intro = find(provisions, "eu-test/art-2")
    assert (intro.kind, intro.path, intro.heading) == ("article", ("2",), "Definitions")
    assert intro.text == "For the purposes of this Regulation:"
    assert find(provisions, "eu-test/art-2/1").text == "‘data’ means any information;"


def test_nested_points_get_a_longer_path(provisions):
    parent = find(provisions, "eu-test/art-2/2")
    assert parent.text == "‘controller’ means a body which, alone or jointly:"
    nested = find(provisions, "eu-test/art-2/2/a")
    assert (nested.kind, nested.path, nested.text) == (
        "point",
        ("2", "2", "a"),
        "determines the purposes; or",
    )


def test_nested_points_are_read_once_at_their_own_depth_and_never_again_one_level_up(provisions):
    ids = {p.id for p in provisions}
    assert "eu-test/art-2/2/a" in ids
    assert "eu-test/art-2/a" not in ids and "eu-test/art-2/b" not in ids
    assert "eu-test/anx-I/a" not in ids


def test_a_one_paragraph_article_is_a_single_article_provision_in_its_own_chapter(provisions):
    p = find(provisions, "eu-test/art-3")
    assert p.text == "Processing shall be lawful only if a legal basis applies."
    assert p.chapter == "CHAPTER II — Principles"


def test_an_annex_keeps_its_title_intro_items_and_nested_items(provisions):
    intro = find(provisions, "eu-test/anx-I")
    assert (intro.unit, intro.kind, intro.path, intro.heading) == ("annex", "annex", ("I",), "List of areas")
    assert intro.text == "The following areas are listed:"
    assert find(provisions, "eu-test/anx-I/1").text == "Biometrics:"
    assert find(provisions, "eu-test/anx-I/1/a").text == "remote identification systems."


@pytest.fixture(scope="module")
def variants():
    path = Path(__file__).parent / "fixtures" / "eu_oj_variants.xhtml"
    return parse_eu_oj(path.read_bytes(), instrument="eu-test", language="es", version="oj")


def test_definitions_written_as_numbered_paragraphs_give_the_same_provisions_as_list_tables(variants):
    # the Spanish Official Journal text of GDPR Article 4 uses "1) ..." paragraphs where the English uses tables
    intro = find(variants, "eu-test/art-4")
    assert intro.text == "A efectos del presente Reglamento se entenderá por:"
    assert find(variants, "eu-test/art-4/1").text == "«datos»: toda información;"
    assert find(variants, "eu-test/art-4/1").kind == "point"
    assert (
        find(variants, "eu-test/art-4/2").text == "«responsable»: el organismo que, solo o junto con otros:"
    )
    assert (
        find(variants, "eu-test/art-4/3").text
        == "«encargado»: el organismo que trata datos por cuenta del responsable."
    )


def test_sub_points_in_tables_attach_to_the_numbered_paragraph_above_them(variants):
    assert find(variants, "eu-test/art-4/2/a").text == "determine los fines; o"
    assert find(variants, "eu-test/art-4/2/b").path == ("4", "2", "b")


def test_an_opening_quote_on_a_list_label_is_not_part_of_the_label(variants):
    quoted = find(variants, "eu-test/art-5/21")
    assert quoted.path == ("5", "21")
    assert quoted.text == "El texto insertado dice así.’;"


def test_lettered_tables_that_follow_a_numbered_table_are_its_sub_points(variants):
    # GDPR Article 4(22) in English: the (a), (b) tables are siblings of the "(22)" table, not nested in it
    assert find(variants, "eu-test/art-6/2/a").path == ("6", "2", "a")
    assert find(variants, "eu-test/art-6/2/b").text == "the authority where data subjects reside;"
    # and the next numbered table starts again at the article level
    assert find(variants, "eu-test/art-6/3").path == ("6", "3")


def test_annex_sections_become_part_of_the_path_so_restarted_numbering_does_not_collide(variants):
    section_a = find(variants, "eu-test/anx-I/A")
    assert section_a.kind == "annex"
    assert section_a.text == "Information from providers" + chr(10) + "The following shall be provided:"
    assert find(variants, "eu-test/anx-I/B").text == "Information from deployers"
    assert find(variants, "eu-test/anx-I/A/1").text == "The name of the provider;"
    assert find(variants, "eu-test/anx-I/A/2").text == "The address of the provider;"
    assert find(variants, "eu-test/anx-I/B/1").text == "The name of the deployer;"


def test_a_numbered_annex_heading_is_a_section_and_its_lettered_items_sit_under_it(variants):
    assert find(variants, "eu-test/anx-II/1").text == "Sistema de Información de Schengen"
    assert find(variants, "eu-test/anx-II/1/a").text == "Reglamento (UE) 2018/1860;"
    assert find(variants, "eu-test/anx-II/2/a").text == "Reglamento (UE) 2021/1133;"


def test_a_three_column_list_table_with_an_empty_indent_cell_still_gives_label_and_text(variants):
    # Spanish AI Act Annex X: <td/> (indent) | "a)" | text
    assert find(variants, "eu-test/anx-II/3").text == "Eurodac"
    assert find(variants, "eu-test/anx-II/3/a").text == "Reglamento (UE) 2024/1358;"


def test_quoted_blocks_wrapped_in_divs_inside_a_list_cell_are_read_not_dropped(variants):
    # the Digital Omnibus puts quoted replacement text in divs inside list cells
    point = find(variants, "eu-test/art-7/1")
    assert point.text == "Article 3 is amended as follows: ‘3. The inserted text.’;"
    assert find(variants, "eu-test/art-7/1/a").text == "nested inside the quoted block;"
    assert find(variants, "eu-test/art-7/1~closing").text == "Closing words of the quoted block.’"


def test_text_in_a_one_cell_table_is_kept_as_text_of_the_article_not_dropped(variants):
    intro = find(variants, "eu-test/art-8")
    assert intro.text == "The following is inserted:"
    first = find(variants, "eu-test/art-8~closing")
    second = find(
        variants, "eu-test/art-8~closing2"
    )  # each paragraph of the quoted block is its own closing text
    assert (first.kind, first.text) == ("closing", "‘Article 99a")
    assert second.text == "The inserted article text.’"


def test_a_numbered_paragraph_container_inside_a_list_cell_is_quoted_text_not_a_paragraph_of_the_article(
    variants,
):
    # the Omnibus quotes "div#002.013" blocks inside list cells; they belong to the amendment point, not to Article 9
    point = find(variants, "eu-test/art-9/3")
    assert point.text == "in Article 2, the following paragraph is added: ‘13. The inserted paragraph:"
    assert find(variants, "eu-test/art-9/3/a").text == "first inserted point;"


def test_a_data_table_is_kept_row_by_row_as_text_not_mistaken_for_a_list(variants):
    # tables of codes in the Digital Omnibus: first column is data, not a "(a)" label
    assert find(variants, "eu-test/art-10").text == "The codes are the following:"
    assert find(variants, "eu-test/art-10~closing").text == "Code | Description"
    assert find(variants, "eu-test/art-10~closing2").text == "AIP 0102 | First description"
    assert not any(p.id.startswith("eu-test/art-10/") for p in variants)


def test_everything_is_in_reading_order_with_unique_ids_and_carries_the_document_labels(provisions):
    assert [p.order for p in provisions] == sorted(p.order for p in provisions)
    assert len({p.id for p in provisions}) == len(provisions)
    assert {(p.instrument, p.language, p.version, p.jurisdiction) for p in provisions} == {
        ("eu-test", "en", "oj", "EU")
    }
    ids = [p.id for p in provisions]
    assert ids.index("eu-test/rct-1") < ids.index("eu-test/art-1/1") < ids.index("eu-test/anx-I")


def test_annex_items_written_as_enumeration_divs_with_two_inline_paragraphs_are_read(variants):
    """The AI Act's Annex VI: each numbered item is a div holding a label paragraph and a text paragraph."""
    assert find(variants, "eu-test/anx-III").heading == "Procedure based on internal control"
    first = find(variants, "eu-test/anx-III/1")
    assert (first.kind, first.path) == ("point", ("III", "1"))
    assert first.text == "The procedure is the one based on points 2 and 3."
    assert find(variants, "eu-test/anx-III/2").text == "The provider verifies the quality management system."
