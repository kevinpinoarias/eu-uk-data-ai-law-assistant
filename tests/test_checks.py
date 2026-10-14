"""
The structural checks every parsed document must pass: no duplicate ids, no empty leaves, article and recital
numbers that run 1..N without gaps, known totals, clean text, and the same skeleton in English and Spanish.
"""

from __future__ import annotations

from law_assistant.model import Provision
from law_assistant.parse.checks import check_structure, compare_skeletons, compare_texts, coverage_ratio


def prov(id_, path, text="some text", *, unit="article", kind="paragraph", heading="A title", language="en"):
    return Provision(
        id=id_,
        instrument="eu-test",
        jurisdiction="EU",
        language=language,
        version="oj",
        unit=unit,
        kind=kind,
        path=tuple(path),
        text=text,
        order=0,
        heading=heading if unit != "recital" else None,
    )


def good_document():
    return [
        prov("eu-test/rct-1", ["1"], unit="recital", kind="recital"),
        prov("eu-test/rct-2", ["2"], unit="recital", kind="recital"),
        prov("eu-test/art-1/1", ["1", "1"]),
        prov("eu-test/art-1/1/a", ["1", "1", "a"], kind="point"),
        prov("eu-test/art-2", ["2"], kind="article"),
    ]


def test_a_clean_document_has_no_problems():
    assert check_structure(good_document(), expected_articles=2, expected_recitals=2) == []


def test_duplicate_ids_are_reported():
    doc = [*good_document(), prov("eu-test/art-2", ["2"], kind="article")]
    assert any("duplicate id" in p and "eu-test/art-2" in p for p in check_structure(doc))


def test_an_empty_leaf_is_reported_but_an_empty_container_with_children_is_fine():
    container = prov("eu-test/art-3/1", ["3", "1"], text="")
    child = prov("eu-test/art-3/1/a", ["3", "1", "a"], kind="point")
    leaf = prov("eu-test/art-3/2", ["3", "2"], text="")
    problems = check_structure(
        [*good_document(), prov("eu-test/art-3", ["3"], kind="article"), container, child, leaf]
    )
    assert any("empty text" in p and "eu-test/art-3/2" in p for p in problems)
    assert not any("art-3/1:" in p or p.endswith("eu-test/art-3/1") for p in problems)


def test_gaps_in_article_or_recital_numbers_are_reported():
    doc = [p for p in good_document() if p.id != "eu-test/rct-2"] + [
        prov("eu-test/rct-4", ["4"], unit="recital", kind="recital")
    ]
    problems = check_structure(doc)
    assert any("recital numbering has gaps" in p and "[2, 3]" in p for p in problems)


def test_a_wrong_total_is_reported():
    problems = check_structure(good_document(), expected_articles=99, expected_recitals=173)
    assert any("expected 99 articles, found 2" in p for p in problems)
    assert any("expected 173 recitals, found 2" in p for p in problems)


def test_an_article_without_a_heading_is_reported():
    doc = [*good_document(), prov("eu-test/art-3", ["3"], kind="article", heading=None)]
    assert any("article 3 has no heading" in p for p in check_structure(doc))


def test_leftover_markup_and_odd_whitespace_are_reported():
    for bad in ("text with <span class='x'>markup</span>", "double  space", "non breaking"):
        doc = [*good_document(), prov("eu-test/art-3", ["3"], kind="article", text=bad)]
        assert any("art-3" in p and ("markup" in p or "whitespace" in p) for p in check_structure(doc)), bad


def test_skeletons_that_differ_between_languages_are_listed_on_both_sides():
    en = good_document()
    es = [p for p in good_document() if p.id != "eu-test/art-1/1/a"] + [
        prov("eu-test/art-9", ["9"], kind="article")
    ]
    problems = compare_skeletons(en, es)
    assert "only in the first: eu-test/art-1/1/a" in problems
    assert "only in the second: eu-test/art-9" in problems
    assert compare_skeletons(en, en) == []


def test_coverage_is_text_plus_what_moved_into_metadata_over_the_source_size():
    doc = [
        prov("eu-test/art-1/1", ["1", "1"], text="abcd"),
        prov("eu-test/art-1/1/a", ["1", "1", "a"], text="efgh", kind="point"),
    ]
    # text 8 + labels "1" and "a" 2 + the heading "A title" once (6 letters) + "Article1" 8 = 24 characters
    assert coverage_ratio(doc, source_characters=24, unit_words={"article": "Article"}) == 1.0
    assert coverage_ratio(doc, source_characters=48, unit_words={"article": "Article"}) == 0.5


def test_texts_are_compared_ignoring_spacing_so_only_real_wording_changes_are_reported():
    first = [
        prov("eu-test/art-1/1", ["1", "1"], text="«data» : any information ;"),
        prov("eu-test/art-2", ["2"], text="Processing shall be lawful.", kind="article"),
        prov("eu-test/art-3", ["3"], text="Only in the first.", kind="article"),
    ]
    second = [
        prov("eu-test/art-1/1", ["1", "1"], text="«data»: any information;"),  # spacing only
        prov("eu-test/art-2", ["2"], text="Processing shall be unlawful.", kind="article"),  # wording changed
        prov("eu-test/art-4", ["4"], text="Only in the second.", kind="article"),
    ]
    diff = compare_texts(first, second)
    assert diff["changed"] == ["eu-test/art-2"]
    assert diff["only_first"] == ["eu-test/art-3"]
    assert diff["only_second"] == ["eu-test/art-4"]


def test_inserted_labels_match_across_languages_when_compared_with_normalising_on():
    # English numbers inserted provisions 14a, ba; Spanish writes them "14 bis", "b bis"
    en = [prov("eu-test/art-3/14a", ["3", "14a"]), prov("eu-test/art-5/1/ba", ["5", "1", "ba"], kind="point")]
    es = [
        prov("eu-test/art-3/14 bis", ["3", "14 bis"]),
        prov("eu-test/art-5/1/b bis", ["5", "1", "b bis"], kind="point"),
    ]
    assert compare_skeletons(en, es) != []
    assert compare_skeletons(en, es, normalise_inserted_labels=True) == []
    ter = [prov("eu-test/art-3/14 ter", ["3", "14 ter"])]
    assert (
        compare_skeletons([prov("eu-test/art-3/14b", ["3", "14b"])], ter, normalise_inserted_labels=True)
        == []
    )


def test_section_numbering_is_checked_like_article_numbering_and_known_gaps_are_allowed():
    doc = [
        prov("uk-test/sec-1", ["1"], unit="section", kind="article"),
        prov("uk-test/sec-3", ["3"], unit="section", kind="article"),
        prov("uk-test/sec-3A", ["3A"], unit="section", kind="article"),
    ]
    assert any("section numbering has gaps" in p and "[2]" in p for p in check_structure(doc))
    assert check_structure(doc, allowed_gaps=[2]) == []
    assert any(
        "expected 4 sections, found 2" in p
        for p in check_structure(doc, expected_sections=4, allowed_gaps=[2])
    )


def test_schedules_can_be_counted_and_a_lettered_article_needs_its_base_article():
    doc = [
        prov("uk-test/art-1", ["1"], kind="article"),
        prov("uk-test/art-1A", ["1A"], kind="article"),
        prov("uk-test/art-5A", ["5A"], kind="article"),
        prov("uk-test/sch-1", ["1"], unit="schedule", kind="annex"),
    ]
    problems = check_structure(doc, expected_schedules=2)
    assert any("expected 2 schedules, found 1" in p for p in problems)
    assert any("article 5A has no article 5" in p for p in problems)
    assert not any("article 1A" in p for p in problems)


def test_headings_are_counted_once_per_distinct_title_so_schedule_paragraphs_each_count():
    doc = [
        prov("uk-test/sch-1/1", ["1", "1"], text="aaaa", unit="schedule", heading="Alpha"),
        prov("uk-test/sch-1/2", ["1", "2"], text="bbbb", unit="schedule", heading="Beta"),
    ]
    # text 8 + labels "1","2" 2 + headings "Alpha" 5 + "Beta" 4 + unit words "Schedule1" 9 (once per schedule)
    assert coverage_ratio(doc, source_characters=28, unit_words={"schedule": "Schedule"}) == 1.0
