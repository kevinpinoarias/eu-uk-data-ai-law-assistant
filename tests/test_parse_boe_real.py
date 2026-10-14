"""
Checks of the BOE parser against the real downloaded LOPDGDD: known totals, the structural checks, near-complete
coverage, the dated versions (which blocks changed, and that every changed block carries the BOE's editorial
note), and golden provisions.

These need the files in data/raw/ (run `python -m law_assistant.fetch.boe`). They are skipped when the files are
absent, as in CI, and run on any machine that has fetched them.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET

import pytest

from law_assistant import settings
from law_assistant.parse.boe import parse_boe, source_characters
from law_assistant.parse.checks import check_structure, coverage_ratio
from law_assistant.parse.run_boe import EXPECTED, INSTRUMENT, KEY, UNIT_WORDS

RAW = settings.RAW_DIR / "boe_es" / f"{KEY}.xml"
AS_OF = "2026-10-14"

pytestmark = pytest.mark.skipif(
    not RAW.exists(), reason="the BOE file is not downloaded (run: python -m law_assistant.fetch.boe)"
)


@pytest.fixture(scope="module")
def data():
    return RAW.read_bytes()


@pytest.fixture(scope="module")
def now(data):
    return parse_boe(data, instrument=INSTRUMENT, version="as-of-test", as_of=AS_OF)


def provision(provisions, id_):
    return next(p for p in provisions if p.id == id_)


def test_known_totals_and_structure_hold(now):
    assert check_structure(now, **EXPECTED) == []
    articles = {p.path[0] for p in now if p.unit == "article"}
    assert len(articles) == 98 and "53 bis" in articles  # articles 1 to 97 and the inserted 53 bis
    dispositions = {p.path[:2] for p in now if p.unit == "disposition"}
    kinds = [kind for kind, _ in dispositions]
    assert (
        kinds.count("adicional"),
        kinds.count("transitoria"),
        kinds.count("derogatoria"),
        kinds.count("final"),
    ) == (
        23,
        6,
        1,
        16,
    )


def test_nothing_is_lost_or_duplicated(data, now):
    ratio = coverage_ratio(now, source_characters=source_characters(data, AS_OF), unit_words=UNIT_WORDS)
    assert 0.995 <= ratio <= 1.005


def test_nothing_is_in_force_before_the_first_version_date(data):
    assert parse_boe(data, instrument=INSTRUMENT, version="v", as_of="2018-12-06") == []


def test_the_units_that_changed_since_the_first_version_are_exactly_the_amended_and_the_added_ones(data, now):
    first = parse_boe(data, instrument=INSTRUMENT, version="v", as_of="2018-12-07")
    squash = lambda t: re.sub(r"\s+", "", t)  # noqa: E731
    old, new = {p.id: p for p in first}, {p.id: p for p in now}

    def unit_of(p):
        return (p.unit, p.path[:2] if p.unit == "disposition" else p.path[:1])

    changed = {unit_of(new[i]) for i in new if i not in old or squash(new[i].text) != squash(old[i].text)}
    changed |= {unit_of(old[i]) for i in old if i not in new}
    amended = {
        ("article", (n,))
        for n in ("2", "23", "24", "44", "48", "50", "64", "65", "66", "67", "75", "77", "83")
    }
    amended |= {("disposition", ("adicional", "decimoquinta")), ("disposition", ("final", "tercera"))}
    added = {("article", ("53 bis",)), ("disposition", ("adicional", "vigésima tercera"))}
    assert changed == amended | added


def test_every_block_with_more_than_one_version_carries_the_boes_editorial_note_in_its_latest(data):
    multi = [b for b in ET.fromstring(data).iter("bloque") if len([v for v in b if v.tag == "version"]) > 1]
    assert len(multi) == 15
    for block in multi:
        latest = [v for v in block if v.tag == "version"][-1]
        assert any(p.get("class") == "nota_pie" for p in latest.iter("p")), block.get("titulo")


def test_an_amended_article_carries_the_date_of_its_amendment(now):
    p = provision(now, f"{INSTRUMENT}/art-2/1")
    assert p.in_force_from == "2021-06-16"
    assert p.text.startswith("Lo dispuesto en los Títulos I a IX y en los artículos 89 a 94")
    assert provision(now, f"{INSTRUMENT}/art-6/1").in_force_from == "2018-12-07"


def test_article_7_sets_the_age_of_consent_for_minors_at_fourteen(now):
    p = provision(now, f"{INSTRUMENT}/art-7/1")
    assert p.text == (
        "El tratamiento de los datos personales de un menor de edad únicamente podrá fundarse en su "
        "consentimiento cuando sea mayor de catorce años."
    )
    assert (p.heading, p.chapter) == (
        "Consentimiento de los menores de edad",
        "TÍTULO II — Principios de protección de datos",
    )


def test_the_object_of_the_law_lists_its_aims_as_lettered_points(now):
    a = provision(now, f"{INSTRUMENT}/art-1/a")
    assert (a.kind, a.path) == ("point", ("1", "a"))
    assert a.text.startswith("Adaptar el ordenamiento jurídico español al Reglamento (UE) 2016/679")


def test_the_repealing_disposition_and_the_preamble_are_read(now):
    repeal = provision(now, f"{INSTRUMENT}/disp-derogatoria/única/2")
    assert repeal.text.startswith("Queda derogado el Real Decreto-ley 5/2018")
    assert (repeal.heading, repeal.chapter) == ("Derogación normativa", None)
    first = provision(now, f"{INSTRUMENT}/rct-I/1")
    assert first.unit == "recital" and first.text.startswith("La protección de las personas físicas")
    assert {p.path[0] for p in now if p.unit == "recital"} == {"I", "II", "III", "IV", "V"}
