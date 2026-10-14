"""
Tests for the chunker (step 1.5): provisions in, retrievable chunks out. The rules under test are the ones
decided from the length profile: a whole article, section, annex or recital is one chunk when it fits in the
cap; longer units split at the top-level paragraph boundaries, then at the points, then at sentences, then by
words, so the cap is a firm ceiling; nothing is lost or duplicated; every chunk carries its context and its
provision ids.
"""

from __future__ import annotations

import pytest

from law_assistant.chunk.checks import check_chunks
from law_assistant.chunk.chunker import DEFAULT_MAX_WORDS, Chunk, chunk_provisions
from law_assistant.model import Provision


def prov(
    id_,
    path,
    text,
    *,
    unit="article",
    kind="paragraph",
    order=0,
    heading="Lawfulness of processing",
    chapter="CHAPTER II — Principles",
    in_force_from=None,
    instrument="eu-gdpr",
    language="en",
    version="oj",
    jurisdiction="EU",
):
    return Provision(
        id=f"{instrument}/{id_}",
        instrument=instrument,
        jurisdiction=jurisdiction,
        language=language,
        version=version,
        unit=unit,
        kind=kind,
        path=tuple(path),
        text=text,
        order=order,
        heading=heading,
        chapter=chapter,
        in_force_from=in_force_from,
    )


def words(n, tag="w"):
    return " ".join(f"{tag}{i}" for i in range(n))


def article_6():
    return [
        prov(
            "art-6/1", ("6", "1"), "Processing shall be lawful only if one of the following applies:", order=1
        ),
        prov("art-6/1/a", ("6", "1", "a"), "the data subject has given consent;", kind="point", order=2),
        prov(
            "art-6/1/f",
            ("6", "1", "f"),
            "processing is necessary for legitimate interests.",
            kind="point",
            order=3,
        ),
        prov(
            "art-6/1~closing",
            ("6", "1"),
            "Point (f) does not apply to public authorities.",
            kind="closing",
            order=4,
        ),
        prov("art-6/2", ("6", "2"), "Member States may introduce more specific provisions.", order=5),
    ]


def test_a_short_article_is_one_chunk_with_its_numbering_restored():
    (c,) = chunk_provisions(article_6())
    assert c.text == (
        "1. Processing shall be lawful only if one of the following applies:\n"
        "(a) the data subject has given consent;\n"
        "(f) processing is necessary for legitimate interests.\n"
        "Point (f) does not apply to public authorities.\n"
        "2. Member States may introduce more specific provisions."
    )
    assert (c.unit, c.unit_path, c.citation, c.part, c.parts) == ("article", ("6",), "Article 6", 1, 1)
    assert c.provision_ids == tuple(p.id for p in article_6())
    assert c.words == len(c.text.split())


def test_the_context_names_the_law_the_chapter_and_the_article_with_its_heading():
    (c,) = chunk_provisions(article_6())
    assert c.context == (
        "GDPR (Regulation (EU) 2016/679) | CHAPTER II — Principles | Article 6: Lawfulness of processing"
    )
    assert c.embed_text == c.context + "\n" + c.text
    assert (c.heading, c.chapter) == ("Lawfulness of processing", "CHAPTER II — Principles")


def test_the_law_name_can_be_given_and_falls_back_to_the_instrument_id():
    named = chunk_provisions(article_6(), instrument_name="The GDPR")
    assert named[0].context.startswith("The GDPR | ")
    other = [prov("art-1", ("1",), "Text.", instrument="xx-unknown")]
    assert chunk_provisions(other)[0].context.startswith("xx-unknown | ")


def test_each_article_is_its_own_chunk_in_reading_order_with_a_running_order():
    ps = article_6() + [
        prov("art-7", ("7",), "Conditions for consent.", kind="article", order=6, heading="Consent")
    ]
    chunks = chunk_provisions(ps)
    assert [c.citation for c in chunks] == ["Article 6", "Article 7"]
    assert [c.order for c in chunks] == [0, 1]


def test_chunk_ids_are_unique_and_carry_version_and_language():
    chunks = chunk_provisions(article_6())
    assert chunks[0].id == "oj:en:eu-gdpr/art-6/1"
    assert len({c.id for c in chunks}) == len(chunks)


def test_a_recital_is_one_chunk_without_a_heading():
    r = prov(
        "rct-47",
        ("47",),
        "The legitimate interests of a controller may provide a legal basis.",
        unit="recital",
        kind="recital",
        heading=None,
        chapter=None,
    )
    (c,) = chunk_provisions([r])
    assert (c.citation, c.unit_path) == ("Recital 47", ("47",))
    assert c.context == "GDPR (Regulation (EU) 2016/679) | Recital 47"
    assert c.text == "The legitimate interests of a controller may provide a legal basis."


def test_the_spanish_preamble_is_cited_by_section_and_paragraph_and_each_paragraph_is_a_chunk():
    ps = [
        prov(
            "rct-I/1",
            ("I", "1"),
            "La protección es un derecho.",
            unit="recital",
            kind="recital",
            heading=None,
            chapter=None,
            instrument="es-lopdgdd",
            language="es",
            version="as-of-20261014",
            jurisdiction="ES",
        ),
        prov(
            "rct-I/2",
            ("I", "2"),
            "El Tribunal lo ha señalado.",
            unit="recital",
            kind="recital",
            order=1,
            heading=None,
            chapter=None,
            instrument="es-lopdgdd",
            language="es",
            version="as-of-20261014",
            jurisdiction="ES",
        ),
    ]
    chunks = chunk_provisions(ps)
    assert [c.citation for c in chunks] == [
        "Preámbulo, sección I, párrafo 1",
        "Preámbulo, sección I, párrafo 2",
    ]


@pytest.mark.parametrize(
    ("unit", "path", "language", "expected"),
    [
        ("article", ("7",), "es", "Artículo 7"),
        ("annex", ("III",), "en", "Annex III"),
        ("annex", ("III",), "es", "Anexo III"),
        ("section", ("6A",), "en", "section 6A"),
        ("schedule", ("1",), "en", "Schedule 1"),
        ("disposition", ("final", "tercera"), "es", "Disposición final tercera"),
        ("disposition", ("derogatoria", "única"), "es", "Disposición derogatoria única"),
    ],
)
def test_citations_use_the_words_of_each_language_and_jurisdiction(unit, path, language, expected):
    p = prov("x", path, "Texto del precepto.", unit=unit, kind="article", language=language)
    assert chunk_provisions([p])[0].citation == expected


def test_two_dispositions_are_two_chunks_whatever_their_depth():
    ps = [
        prov("disp-final/primera/1", ("final", "primera", "1"), "Uno.", unit="disposition"),
        prov("disp-final/segunda/1", ("final", "segunda", "1"), "Dos.", unit="disposition", order=1),
    ]
    assert [c.citation for c in chunk_provisions(ps)] == [
        "Disposición final primera",
        "Disposición final segunda",
    ]


def test_bullets_and_deep_levels_are_rendered_readably():
    ps = [
        prov("art-3", ("3",), "Applies in these cases:", kind="article"),
        prov("art-3/item1", ("3", "item1"), "the first case,", kind="point", order=1),
        prov("art-3/item2", ("3", "item2"), "the second case.", kind="point", order=2),
    ]
    assert chunk_provisions(ps)[0].text == "Applies in these cases:\n– the first case,\n– the second case."
    uk = [
        prov("schedule-1/3", ("1", "3"), "Employment.", unit="schedule", kind="paragraph"),
        prov(
            "schedule-1/3/2", ("1", "3", "2"), "This applies if:", unit="schedule", kind="paragraph", order=1
        ),
        prov(
            "schedule-1/3/2/a",
            ("1", "3", "2", "a"),
            "it is necessary;",
            unit="schedule",
            kind="point",
            order=2,
        ),
    ]
    assert chunk_provisions(uk)[0].text == "3. Employment.\n(2) This applies if:\n(a) it is necessary;"


def test_the_date_of_a_chunk_is_the_latest_date_among_its_provisions():
    ps = [
        prov("art-6/1", ("6", "1"), "A.", in_force_from="2025-08-20"),
        prov("art-6/2", ("6", "2"), "B.", order=1, in_force_from="2026-02-05"),
        prov("art-6/3", ("6", "3"), "C.", order=2, in_force_from=None),
    ]
    assert chunk_provisions(ps)[0].in_force_from == "2026-02-05"
    assert chunk_provisions([prov("art-1", ("1",), "A.")])[0].in_force_from is None


def test_a_long_article_splits_between_numbered_paragraphs_never_inside_one():
    ps = [prov(f"art-9/{i}", ("9", str(i)), words(150, f"p{i}x"), order=i) for i in (1, 2, 3)]
    chunks = chunk_provisions(ps, max_words=400)
    assert [(c.part, c.parts) for c in chunks] == [(1, 2), (2, 2)]
    assert [c.provision_ids for c in chunks] == [("eu-gdpr/art-9/1", "eu-gdpr/art-9/2"), ("eu-gdpr/art-9/3",)]
    assert [c.id for c in chunks] == ["oj:en:eu-gdpr/art-9/1", "oj:en:eu-gdpr/art-9/3"]
    assert {c.context for c in chunks} == {chunks[0].context}
    assert {c.citation for c in chunks} == {"Article 9"}


def test_a_paragraph_stays_with_its_points_when_the_pair_fits():
    ps = [
        prov("art-9/1", ("9", "1"), words(50, "lead"), order=1),
        prov("art-9/1/a", ("9", "1", "a"), words(50, "pa"), kind="point", order=2),
        prov("art-9/1/b", ("9", "1", "b"), words(50, "pb"), kind="point", order=3),
        prov("art-9/2", ("9", "2"), words(290, "second"), order=4),
    ]
    chunks = chunk_provisions(ps, max_words=300)
    assert [len(c.provision_ids) for c in chunks] == [3, 1]


def test_one_overlong_paragraph_splits_between_its_points():
    ps = [prov("art-9/1", ("9", "1"), "Intro line:", order=1)] + [
        prov(f"art-9/1/{ch}", ("9", "1", ch), words(150, f"pt{ch}"), kind="point", order=2 + i)
        for i, ch in enumerate("abc")
    ]
    chunks = chunk_provisions(ps, max_words=400)
    assert len(chunks) == 2
    assert [p for c in chunks for p in c.provision_ids] == [p.id for p in ps]
    assert all(c.words <= 400 for c in chunks)


def test_one_overlong_provision_splits_at_sentence_boundaries():
    sentence = lambda i: " ".join(f"s{i}w{j}" for j in range(19)) + "."  # noqa: E731  20 words with the full stop
    text = " ".join(sentence(i) for i in range(30))  # 570 words
    p = prov("art-9", ("9",), text, kind="article")
    chunks = chunk_provisions([p], max_words=200)
    assert len(chunks) == 3 and all(c.words <= 200 for c in chunks)
    assert all(c.text.endswith(".") for c in chunks)
    assert all(c.provision_ids == (p.id,) for c in chunks)


def test_a_single_sentence_longer_than_the_cap_is_cut_by_words_as_a_last_resort():
    p = prov("art-9", ("9",), words(1000), kind="article")
    chunks = chunk_provisions([p], max_words=400)
    assert [c.words for c in chunks] == [400, 400, 200]
    assert " ".join(c.text for c in chunks) == p.text


def test_an_empty_container_line_never_becomes_a_chunk_of_its_own():
    ps = [prov("anx-I", ("I",), "", unit="annex", kind="annex", heading="List")] + [
        prov(f"anx-I/{i}", ("I", str(i)), words(300, f"i{i}x"), unit="annex", order=i) for i in (1, 2)
    ]
    chunks = chunk_provisions(ps, max_words=400)
    assert len(chunks) == 2 and all(c.text.strip() for c in chunks)
    assert chunks[0].provision_ids == ("eu-gdpr/anx-I", "eu-gdpr/anx-I/1")
    assert check_chunks(ps, chunks, max_words=400) == []


def test_the_default_cap_is_four_hundred_words():
    assert DEFAULT_MAX_WORDS == 400


def test_chunking_is_deterministic():
    ps = article_6() + [
        prov(f"art-9/{i}", ("9", str(i)), words(150, f"p{i}"), order=10 + i) for i in (1, 2, 3)
    ]
    assert chunk_provisions(ps) == chunk_provisions(list(ps))


def test_a_mixed_document_is_refused():
    other = prov("art-1", ("1",), "Text.", language="es")
    with pytest.raises(ValueError, match="one document"):
        chunk_provisions([*article_6(), other])


def test_an_empty_document_gives_no_chunks():
    assert chunk_provisions([]) == []


def test_a_chunk_survives_a_round_trip_through_a_dict():
    (c,) = chunk_provisions(article_6())
    assert Chunk.from_dict(c.to_dict()) == c


# --- the checks ---------------------------------------------------------------------------------------------


def long_document():
    return article_6() + [
        prov(f"art-9/{i}", ("9", str(i)), words(150, f"p{i}x"), order=10 + i) for i in (1, 2, 3)
    ]


def test_the_checks_pass_for_a_good_chunking():
    ps = long_document()
    assert check_chunks(ps, chunk_provisions(ps), max_words=400) == []


def test_the_checks_notice_a_lost_provision():
    ps = long_document()
    chunks = chunk_provisions(ps)
    problems = check_chunks(ps, chunks[:-1], max_words=400)
    assert any("lost" in p for p in problems) and any("characters" in p for p in problems)


def test_the_checks_notice_a_chunk_over_the_cap():
    ps = long_document()
    assert any("over the cap" in p for p in check_chunks(ps, chunk_provisions(ps), max_words=100))


def test_the_checks_notice_altered_text():
    ps = long_document()
    chunks = chunk_provisions(ps)
    broken = [Chunk.from_dict({**chunks[0].to_dict(), "text": chunks[0].text + " extra"}), *chunks[1:]]
    assert any("characters" in p for p in check_chunks(ps, broken, max_words=400))


def test_the_checks_notice_duplicate_ids_and_empty_chunks():
    ps = long_document()
    chunks = chunk_provisions(ps)
    duplicated = [chunks[0], chunks[0], *chunks[1:]]
    assert any("duplicate" in p for p in check_chunks(ps, duplicated, max_words=400))
    empty = [Chunk.from_dict({**chunks[0].to_dict(), "text": "  "}), *chunks[1:]]
    assert any("empty" in p for p in check_chunks(ps, empty, max_words=400))


def test_a_numbered_paragraph_with_no_text_of_its_own_leaves_no_trailing_space():
    ps = [
        prov("sch-19/1", ("19", "1"), "", unit="schedule"),
        prov("sch-19/1/1", ("19", "1", "1"), "A first amendment.", unit="schedule", order=1),
    ]
    assert chunk_provisions(ps)[0].text == "1.\n(1) A first amendment."


def test_a_spelled_out_label_gets_back_its_capital_letter():
    ps = [
        prov(
            "disp-final/tercera",
            ("final", "tercera"),
            "Se modifica la ley:",
            unit="disposition",
            kind="article",
        ),
        prov(
            "disp-final/tercera/uno",
            ("final", "tercera", "uno"),
            "El apartado 3 queda así:",
            unit="disposition",
            order=1,
        ),
    ]
    assert chunk_provisions(ps)[0].text == "Se modifica la ley:\nUno. El apartado 3 queda así:"
