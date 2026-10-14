"""
Checks of the UK parser against the real downloaded legislation.gov.uk files: known totals, the structural checks
(missing section numbers must be exactly the repealed or not-yet-in-force ones), near-complete coverage, dates
that agree with the government's commencement table, and the UK GDPR against the EU text.

These need the files in data/raw/ (run `python -m law_assistant.fetch.uk`). They are skipped when the files are
absent, as in CI, and run on any machine that has fetched them.
"""

from __future__ import annotations

import re

import pytest

from law_assistant import settings
from law_assistant.parse.checks import check_structure, coverage_ratio
from law_assistant.parse.eu_consolidated import parse_eu_consolidated
from law_assistant.parse.run_uk import SPECS, UNIT_WORDS
from law_assistant.parse.uk import parse_uk, skipped_provisions, source_characters

RAW = settings.RAW_DIR / "legislation_gov_uk"

pytestmark = pytest.mark.skipif(
    not (RAW / "uk-gdpr.xml").exists(),
    reason="the UK files are not downloaded (run: python -m law_assistant.fetch.uk)",
)

KEYS = [spec.key for spec in SPECS]


@pytest.fixture(scope="module")
def parsed():
    out = {}
    for spec in SPECS:
        data = (RAW / f"{spec.key}.xml").read_bytes()
        out[spec.key] = (
            parse_uk(data, instrument=spec.key, version="revised-test"),
            skipped_provisions(data),
            source_characters(data),
        )
    return out


def provision(parsed, key, id_):
    return next(p for p in parsed[key][0] if p.id == id_)


@pytest.mark.parametrize("key", KEYS)
def test_known_totals_and_structure_hold_with_the_skipped_numbers_as_the_only_gaps(parsed, key):
    spec = next(s for s in SPECS if s.key == key)
    provisions, skipped, _ = parsed[key]
    assert check_structure(provisions, **spec.expected, allowed_gaps=skipped["numbers"]) == []


@pytest.mark.parametrize("key", KEYS)
def test_nothing_is_lost_or_duplicated(parsed, key):
    provisions, _, source_chars = parsed[key]
    ratio = coverage_ratio(provisions, source_characters=source_chars, unit_words=UNIT_WORDS)
    assert 0.995 <= ratio <= 1.005


def test_the_missing_section_numbers_of_the_new_act_are_exactly_the_not_yet_in_force_ones(parsed):
    provisions, skipped, _ = parsed["uk-duaa-2025"]
    present = {int(p.path[0]) for p in provisions if p.unit == "section" and p.path[0].isdigit()}
    missing = [n for n in range(1, max(present) + 1) if n not in present]
    assert missing == skipped["numbers"] and skipped["prospective"] > 0


def test_the_uk_gdpr_drops_the_cooperation_chapter_the_eu_text_has(parsed):
    provisions, skipped, _ = parsed["uk-gdpr"]
    assert skipped["numbers"] == [*range(60, 77), 92, 93]
    assert not any(p.unit == "article" and p.path[0] in {"60", "76"} for p in provisions)


def test_dates_agree_with_the_governments_commencement_table(parsed):
    # Article 17(1)(g), the new erasure ground: 31 March 2026; the complaints provisions (section 103): 19 June 2026;
    # the first provisions of the Act: 20 August 2025
    assert provision(parsed, "uk-gdpr", "uk-gdpr/art-17/1/g").in_force_from == "2026-03-31"
    assert provision(parsed, "uk-duaa-2025", "uk-duaa-2025/sec-103/1").in_force_from == "2026-06-19"
    assert provision(parsed, "uk-duaa-2025", "uk-duaa-2025/sec-1/1").in_force_from == "2025-08-20"


def test_the_uk_gdpr_has_the_recognised_legitimate_interests_basis_the_eu_text_lacks(parsed):
    ea = provision(parsed, "uk-gdpr", "uk-gdpr/art-6/1/ea")
    assert ea.text == "processing is necessary for the purposes of a recognised legitimate interest;"
    assert (ea.heading, ea.chapter) == ("Lawfulness of processing", "CHAPTER II — Principles")
    assert ea.in_force_from == "2026-02-05"


def test_article_5_1_a_is_word_for_word_the_same_in_the_uk_and_the_eu_text(parsed):
    eu = parse_eu_consolidated(
        (settings.RAW_DIR / "eur_lex_cellar" / "eu-gdpr-consolidated-en.xhtml").read_bytes(),
        instrument="uk-gdpr",
        language="en",
        version="consolidated",
    )
    eu_text = next(p.text for p in eu if p.id == "uk-gdpr/art-5/1/a")
    uk_text = provision(parsed, "uk-gdpr", "uk-gdpr/art-5/1/a").text
    assert re.sub(r"\s+", "", eu_text) == re.sub(r"\s+", "", uk_text)


def test_the_data_protection_act_keeps_its_first_sections_and_their_parts(parsed):
    p = provision(parsed, "uk-dpa-2018", "uk-dpa-2018/sec-1/1")
    assert p.text == "This Act makes provision about the processing of personal data."
    assert (p.heading, p.chapter) == ("Overview", "PART 1 — Preliminary")
    offence = provision(parsed, "uk-dpa-2018", "uk-dpa-2018/sec-170/1")
    assert offence.text == "It is an offence for a person knowingly or recklessly—"
    assert offence.chapter == "PART 6 — Enforcement > Offences relating to personal data"


def test_a_section_that_is_a_table_keeps_its_rows(parsed):
    p = provision(parsed, "uk-dpa-2018", "uk-dpa-2018/sec-206")
    assert p.text.startswith("The Table below lists provisions which define or otherwise explain terms")
    rows = [q for q in parsed["uk-dpa-2018"][0] if q.id.startswith("uk-dpa-2018/sec-206~closing")]
    assert len(rows) > 10 and all(" | " in r.text for r in rows)
