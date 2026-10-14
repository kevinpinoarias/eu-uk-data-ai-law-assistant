"""
Tests for the BOE parser (consolidated Spanish legislation from the open-data API), on a fixture built from the
real markup: blocks with dated versions, headings that give the chapter context, articles and dispositions whose
paragraphs, lettered points and bullets are recognised by their text (the classes are used inconsistently),
quoted amendments in indented paragraphs, editorial notes that are not law text, and a preamble.
The checks against the full downloaded file live in test_parse_boe_real.py.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from law_assistant.parse.boe import parse_boe

FIXTURE = Path(__file__).parent / "fixtures" / "boe_sample.xml"
TODAY = "2026-10-15"


def parse(as_of=TODAY):
    return parse_boe(FIXTURE.read_bytes(), instrument="es-test", version=f"as-of-{as_of}", as_of=as_of)


@pytest.fixture(scope="module")
def provisions():
    return parse()


def find(provisions, id_):
    matches = [p for p in provisions if p.id == id_]
    assert len(matches) == 1, f"{id_}: {[p.id for p in provisions]}"
    return matches[0]


def test_the_latest_version_in_force_on_the_date_is_used_and_carries_its_date(provisions):
    p = find(provisions, "es-test/art-2/1")
    assert p.text == "Lo dispuesto se aplica a cualquier tratamiento, incluidos los policiales."
    assert (p.in_force_from, p.language, p.jurisdiction) == ("2021-06-16", "es", "ES")


def test_an_earlier_date_gives_the_earlier_wording():
    old = find(parse("2019-01-01"), "es-test/art-2/1")
    assert old.text == "Lo dispuesto se aplica a cualquier tratamiento."
    assert old.in_force_from == "2018-12-07"


def test_a_block_that_is_not_yet_in_force_is_left_out_until_its_date(provisions):
    assert not any(p.id.startswith("es-test/art-4") for p in provisions)
    later = parse("2027-06-01")
    assert find(later, "es-test/art-4").text == "Este texto entra en vigor el 1 de enero de 2027."


def test_an_article_gets_its_heading_chapter_and_lead_text(provisions):
    p = find(provisions, "es-test/art-1")
    assert (p.unit, p.kind, p.path) == ("article", "article", ("1",))
    assert p.text == "La presente ley orgánica tiene por objeto:"
    assert p.heading == "Objeto de la ley"
    assert p.chapter == "TÍTULO I — Disposiciones generales"


def test_lettered_points_are_found_by_their_text_whatever_the_paragraph_class(provisions):
    a = find(provisions, "es-test/art-1/a")
    assert (a.kind, a.path, a.text) == (
        "point",
        ("1", "a"),
        "Adaptar el ordenamiento jurídico al Reglamento.",
    )
    assert find(provisions, "es-test/art-1/b").text == "Garantizar los derechos digitales."


def test_an_unnumbered_paragraph_after_a_point_continues_that_point_as_closing_text(provisions):
    closing = find(provisions, "es-test/art-1/a~closing")
    assert (closing.kind, closing.path) == ("closing", ("1", "a"))
    assert closing.text == "El derecho fundamental de las personas físicas ampara este objeto."


def test_numbered_paragraphs_with_their_own_lettered_points_do_not_collide(provisions):
    assert find(provisions, "es-test/art-2/2").kind == "paragraph"
    assert find(provisions, "es-test/art-2/2/a").text == "A los tratamientos excluidos."
    assert find(provisions, "es-test/art-2/2/b").text == "A los tratamientos de personas fallecidas."
    assert find(provisions, "es-test/art-2/3/a").text == "Un primer supuesto del apartado 3."


def test_the_chapter_context_stacks_title_chapter_and_section(provisions):
    p = find(provisions, "es-test/art-3")
    assert (
        p.chapter
        == "TÍTULO I — Disposiciones generales > CAPÍTULO I — Principios > Sección 1.ª Disposiciones generales"
    )


def test_dash_bullets_become_numbered_items_and_the_last_paragraph_closes_the_list(provisions):
    assert find(provisions, "es-test/art-3").text == "Se aplica en los casos siguientes:"
    assert find(provisions, "es-test/art-3/item1").text == "El primer caso,"
    assert find(provisions, "es-test/art-3/item2").text == "el segundo caso,"
    assert find(provisions, "es-test/art-3/item3").text == "el tercer caso."
    assert find(provisions, "es-test/art-3/item3~closing").text == "Este último párrafo cierra la lista."


def test_an_inserted_article_keeps_its_suffix_as_written(provisions):
    p = find(provisions, "es-test/art-53 bis")
    assert (p.path, p.heading, p.text) == (
        ("53 bis",),
        "Un artículo insertado",
        "Texto del artículo insertado.",
    )


def test_editorial_notes_and_the_signature_are_not_law_text(provisions):
    texts = " ".join(p.text for p in provisions)
    assert "Se añade el apartado 5" not in texts and "Se modifica el apartado 1" not in texts
    assert "Madrid, 5 de diciembre" not in texts


def test_dispositions_are_a_unit_of_their_own_with_the_kind_and_ordinal_as_the_path(provisions):
    assert (
        find(provisions, "es-test/disp-adicional/primera/1").text
        == "El Esquema Nacional incluirá las medidas."
    )
    assert find(provisions, "es-test/disp-adicional/primera/2").path == ("adicional", "primera", "2")
    abrogation = find(provisions, "es-test/disp-derogatoria/única")
    assert (abrogation.unit, abrogation.kind, abrogation.heading) == (
        "disposition",
        "article",
        "Derogación normativa",
    )
    assert abrogation.text == "Queda derogada la normativa anterior."
    assert abrogation.chapter is None


def test_spelled_out_markers_and_quoted_amendments_in_a_final_disposition(provisions):
    base = "es-test/disp-final/vigésima segunda"
    assert (
        find(provisions, base).text == "Se modifica la Ley Orgánica 5/1985, que queda redactada como sigue:"
    )
    uno = find(provisions, f"{base}/uno")
    assert (uno.kind, uno.text) == (
        "paragraph",
        "El apartado 3 del artículo treinta y nueve queda redactado como sigue:",
    )
    assert (
        find(provisions, f"{base}/uno~closing").text
        == "«3. Dentro del plazo anterior, cualquier persona podrá formular reclamación.»"
    )
    # the quoted article's own numbered paragraphs are text, not markers of the disposition
    assert not any(p.id.startswith(f"{base}/1") or p.id.startswith(f"{base}/2") for p in provisions)
    quoted = [p.text for p in provisions if p.id.startswith(f"{base}/dos~closing")]
    assert quoted == [
        "«Artículo cincuenta y ocho bis. Utilización de medios tecnológicos.",
        "1. (Anulado)",
        "2. Los partidos políticos podrán utilizar datos personales.»",
    ]


def test_the_preamble_becomes_recitals_by_roman_section_without_the_royal_formula(provisions):
    r = find(provisions, "es-test/rct-I/1")
    assert (r.unit, r.kind, r.path) == ("recital", "recital", ("I", "1"))
    assert r.text == "La protección de las personas físicas es un derecho fundamental."
    assert find(provisions, "es-test/rct-I/2").text == "El Tribunal Constitucional lo ha señalado."
    assert find(provisions, "es-test/rct-II/1").path == ("II", "1")
    assert not any("FELIPE" in p.text or "vieren" in p.text for p in provisions)


def test_everything_is_in_reading_order_with_unique_ids(provisions):
    assert [p.order for p in provisions] == sorted(p.order for p in provisions)
    assert len({p.id for p in provisions}) == len(provisions)
