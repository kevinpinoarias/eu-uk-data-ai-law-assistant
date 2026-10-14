"""
Tests for the UK parser (legislation.gov.uk XML), on a fixture built from the real markup: recitals as
`Division`s, chapters, articles and sections whose ids are already citations (`article-6-1-a`), amendment markup
that must be read as the current wording, repealed and not-yet-in-force provisions that must be left out, quoted
block amendments, and schedules.
The checks against the full downloaded files live in test_parse_uk_real.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from law_assistant.parse.uk import parse_uk, skipped_provisions

FIXTURE = Path(__file__).parent / "fixtures" / "uk_sample.xml"


@pytest.fixture(scope="module")
def provisions():
    return parse_uk(FIXTURE.read_bytes(), instrument="uk-test", version="revised-20261014")


def find(provisions, id_):
    matches = [p for p in provisions if p.id == id_]
    assert len(matches) == 1, f"{id_}: {[p.id for p in provisions]}"
    return matches[0]


def test_recitals_are_read_from_their_divisions_without_footnote_or_commentary_markers(provisions):
    r1 = find(provisions, "uk-test/rct-1")
    assert (r1.unit, r1.kind, r1.path, r1.jurisdiction) == ("recital", "recital", ("1",), "UK")
    assert r1.text == "The protection of natural persons is a fundamental right."
    assert find(provisions, "uk-test/rct-2").text == "The principles should respect rights."


def test_the_preamble_text_that_is_not_a_recital_is_not_a_provision(provisions):
    assert not any("EUROPEAN PARLIAMENT" in p.text for p in provisions)


def test_an_article_paragraph_gets_its_place_heading_and_chapter_from_the_xml(provisions):
    p = find(provisions, "uk-test/art-1/1")
    assert (p.unit, p.kind, p.path) == ("article", "paragraph", ("1", "1"))
    assert p.text == "This Regulation lays down rules relating to:"
    assert p.heading == "Subject-matter"
    assert p.chapter == "CHAPTER I — General provisions"
    assert p.version == "revised-20261014"


def test_points_and_text_after_them_follow_the_same_conventions_as_the_eu_parsers(provisions):
    assert find(provisions, "uk-test/art-1/1/a").text == "the protection of natural persons; and"
    assert find(provisions, "uk-test/art-1/1/b").path == ("1", "1", "b")
    closing = find(provisions, "uk-test/art-1/1~closing")
    assert (closing.kind, closing.path) == ("closing", ("1", "1"))
    assert closing.text == "The first subparagraph is without prejudice to national law."


def test_amendment_markup_is_read_as_the_current_wording(provisions):
    assert find(provisions, "uk-test/art-1/2").text == "This Regulation protects fundamental rights."


def test_provisions_not_yet_in_force_and_repealed_provisions_are_left_out(provisions):
    ids = {p.id for p in provisions}
    assert "uk-test/art-1/3" not in ids and "uk-test/art-2" not in ids
    assert not any("not yet in force" in p.text or "Repealed" in p.text for p in provisions)


def test_the_skipped_provisions_are_counted_so_the_report_can_say_so():
    skipped = skipped_provisions(FIXTURE.read_bytes())
    assert (skipped["repealed"], skipped["prospective"]) == (1, 1)
    assert skipped["numbers"] == [2]  # the repealed article, so its number is a known gap


def test_an_inserted_article_keeps_its_letter_and_the_date_it_came_into_force(provisions):
    p = find(provisions, "uk-test/art-1A")
    assert (p.kind, p.path, p.text) == ("article", ("1A",), "An inserted article.")
    assert (p.heading, p.in_force_from) == ("Recognised legitimate interests", "2026-02-05")
    assert find(provisions, "uk-test/art-1/1").in_force_from is None


def test_an_annex_and_its_paragraphs_inherit_the_date_from_their_group(provisions):
    annex = find(provisions, "uk-test/anx-1")
    assert (annex.unit, annex.kind, annex.heading) == ("annex", "annex", "LAWFULNESS OF PROCESSING")
    paragraph = find(provisions, "uk-test/anx-1/1")
    assert (paragraph.kind, paragraph.text) == (
        "paragraph",
        "This condition is met where the disclosure is necessary.",
    )
    assert (paragraph.heading, paragraph.in_force_from) == ("Disclosure for purposes", "2026-02-05")


def test_a_one_paragraph_section_is_an_article_kind_provision_with_its_part_chapter_and_cross_heading(
    provisions,
):
    p = find(provisions, "uk-test/sec-6")
    assert (p.unit, p.kind, p.path) == ("section", "article", ("6",))
    assert p.text == "Processing is lawful if a basis applies."
    assert p.heading == "Lawfulness of processing"
    assert p.chapter == "PART 2 — General processing > CHAPTER 1 — Scope > Lawfulness"


def test_a_quoted_block_amendment_is_kept_as_closing_text_of_its_paragraph(provisions):
    assert find(provisions, "uk-test/sec-7/1").text == "The Secretary of State may by regulations"
    quoted = find(provisions, "uk-test/sec-7/1~closing")
    assert quoted.kind == "closing"
    assert quoted.text == "8 An order may in particular— a specify a document;"
    assert not any(p.id.startswith("uk-test/sec-7/1/") for p in provisions)  # quoted text is not a provision


def test_a_schedule_keeps_its_title_intro_and_numbered_paragraphs_with_their_part(provisions):
    schedule = find(provisions, "uk-test/sch-1")
    assert (schedule.unit, schedule.kind, schedule.heading) == (
        "schedule",
        "annex",
        "Special categories conditions",
    )
    assert schedule.text == "This Schedule sets out conditions."
    sub = find(provisions, "uk-test/sch-1/1/1")
    assert (sub.kind, sub.path) == ("paragraph", ("1", "1", "1"))
    assert sub.text == "This condition is met if the processing is necessary:"
    assert (sub.heading, sub.chapter) == ("Employment, social security", "Part 1 — Employment")
    assert find(provisions, "uk-test/sch-1/1/1/a").text == "for the purposes of employment law;"


def test_everything_is_in_reading_order_with_unique_ids(provisions):
    assert [p.order for p in provisions] == sorted(p.order for p in provisions)
    assert len({p.id for p in provisions}) == len(provisions)
    assert {p.jurisdiction for p in provisions} == {"UK"}


def test_the_source_size_for_coverage_leaves_out_repealed_text_and_markers():
    from law_assistant.parse.uk import source_characters

    size = source_characters(FIXTURE.read_bytes())
    assert size > 0
    # coverage with the unit words the UK files use is complete on the fixture
    from law_assistant.parse.checks import coverage_ratio

    provisions = parse_uk(FIXTURE.read_bytes(), instrument="uk-test", version="r")
    words = {"article": "Article", "section": "", "schedule": "Schedule", "annex": "ANNEX"}
    assert 0.98 <= coverage_ratio(provisions, source_characters=size, unit_words=words) <= 1.02


def test_a_recital_split_across_a_title_and_a_paragraph_is_read_whole(provisions):
    assert find(provisions, "uk-test/rct-3").text == (
        "The first sentence sits in a title element. The second sentence is in the paragraph."
    )


def test_a_table_beside_the_paragraph_is_kept_row_by_row_as_closing_text(provisions):
    assert find(provisions, "uk-test/sec-8").text == "The Table below lists provisions."
    assert find(provisions, "uk-test/sec-8~closing").text == "the affirmative procedure | section 182"
    assert find(provisions, "uk-test/sec-8~closing2").text == "the negative procedure | section 183"


def test_provisions_the_law_has_omitted_are_left_out_not_kept_as_dots(provisions):
    """legislation.gov.uk shows omitted provisions as a Text of dots with no status: an omitted article, an
    omitted paragraph, and an article whose only paragraph is omitted."""
    ids = {p.id for p in provisions}
    assert not any(i.startswith(("uk-test/art-3", "uk-test/art-4")) for i in ids)
    assert "uk-test/art-1/4" not in ids and "uk-test/art-1/2" in ids
    assert not any(p.text.strip() and set(p.text) <= {" ", "."} for p in provisions)


def test_the_omitted_provisions_are_counted_with_the_numbers_of_the_omitted_articles():
    skipped = skipped_provisions(FIXTURE.read_bytes())
    assert (
        skipped["omitted"] == 3
    )  # article 3, paragraph 4 of article 1, article 4 (counted once, at the top)
    assert skipped["omitted_numbers"] == [3, 4]


def test_a_closing_line_of_dots_after_a_list_is_omitted_words_not_text(provisions):
    ids = {p.id for p in provisions}
    assert {"uk-test/art-1/5", "uk-test/art-1/5/a"} <= ids
    assert "uk-test/art-1/5~closing" not in ids
