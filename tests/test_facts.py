"""
Tests for the structured table of exact facts (step 2.3): finding numbers and dates in legal text, the shape of a
fact, and the checks that every number in a fact appears in the provision it cites. The table itself and the
checks against the real corpus are in test_facts_set.py and test_facts_real.py.
"""

from __future__ import annotations

import pytest

from law_assistant.evaluation.checks import Corpus
from law_assistant.evaluation.gold import GoldProvision, GoldQuestion
from law_assistant.facts.checks import check_facts, check_gold_keys
from law_assistant.facts.extract import dates_in, numbers_in, value_leaves
from law_assistant.facts.table import Fact, FactSource, lookup, read_facts, write_facts
from law_assistant.model import Provision

# --- finding numbers and dates ---------------------------------------------------------------------------


def test_digit_numbers_with_spaces_or_commas_between_thousands_are_read_as_one_number():
    found = numbers_in("fines up to 20 000 000 EUR, or up to 4 % of the total worldwide annual turnover")
    assert {20_000_000, 4} <= found
    assert 17_500_000 in numbers_in("administrative fines up to £17,500,000, or 4 %")
    assert 72 in numbers_in("not later than 72 hours after having become aware of it")


def test_a_number_word_counts_only_when_it_counts_a_period():
    assert {1, 2} <= numbers_in("within one month of receipt; extended by two further months")
    assert numbers_in("one of the following conditions applies") == set()
    assert 14 in numbers_in("cuando sea mayor de catorce años")
    assert 2 in numbers_in("podrá prorrogarse otros dos meses") and 1 in numbers_in("en el plazo de un mes")
    assert numbers_in("uno de los siguientes supuestos") == set()


def test_dates_are_read_in_english_and_spanish_and_returned_as_iso():
    assert dates_in("It shall apply from 2 August 2026. However, chapters apply from 2 February 2025") == {
        "2026-08-02",
        "2025-02-02",
    }
    assert dates_in("a partir del 2 de diciembre de 2027") == {"2027-12-02"}
    assert dates_in("no date here, only 2016/679 and Article 6") == set()


def test_the_numbers_and_dates_of_a_value_are_collected_ignoring_text_and_booleans():
    value = {
        "amount": 20_000_000,
        "currency": "EUR",
        "turnover_percent": 4,
        "higher_of": True,
        "dates": {"annex_iii": "2027-12-02"},
        "ratio": 0.5,
    }
    numbers, dates = value_leaves(value)
    assert numbers == {20_000_000, 4, 0.5} and dates == {"2027-12-02"}


# --- the shape of a fact ---------------------------------------------------------------------------------


def source(**kw):
    base = dict(
        instrument="eu-gdpr",
        unit="article",
        unit_path=("83",),
        pinpoints=("eu-gdpr/art-83/5",),
        quotes=("up to 20 000 000 EUR",),
    )
    return FactSource(**{**base, **kw})


def fact(**kw):
    base = dict(
        key="gdpr-fine-upper-tier",
        kind="fine_ceiling",
        jurisdictions=("EU",),
        subject_en="Highest GDPR fine tier",
        subject_es="Nivel máximo de multas del RGPD",
        value={"amount": 20_000_000, "currency": "EUR", "turnover_percent": 4},
        summary_en="Up to EUR 20,000,000 or 4 % of worldwide annual turnover, whichever is higher.",
        summary_es="Hasta 20 000 000 EUR o el 4 % del volumen de negocio mundial, si esta cuantía fuese superior.",
        sources=(source(),),
    )
    return Fact(**{**base, **kw})


def test_a_fact_has_a_summary_in_each_language_and_empty_caveats_by_default():
    f = fact()
    assert f.summary("en").startswith("Up to EUR") and f.summary("es").startswith("Hasta")
    assert (f.caveat_en, f.caveat_es) == ("", "")
    with pytest.raises(ValueError, match="language"):
        f.summary("fr")


@pytest.mark.parametrize(("field", "value"), [("kind", "opinion"), ("jurisdictions", ("FR",))])
def test_an_unknown_kind_or_jurisdiction_is_refused(field, value):
    with pytest.raises(ValueError, match=field):
        fact(**{field: value})


def test_a_fact_needs_a_source_and_a_value():
    with pytest.raises(ValueError, match="source"):
        fact(sources=())
    with pytest.raises(ValueError, match="value"):
        fact(value={})


def test_a_fact_survives_a_round_trip_and_the_table_is_written_in_key_order(tmp_path):
    f = fact()
    assert Fact.from_dict(f.to_dict()) == f
    path = tmp_path / "facts" / "legal_facts.jsonl"
    write_facts(path, [fact(key="b-fact"), fact(key="a-fact")])
    assert [x.key for x in read_facts(path)] == ["a-fact", "b-fact"]
    assert lookup(read_facts(path), "a-fact").key == "a-fact"
    with pytest.raises(KeyError):
        lookup(read_facts(path), "missing")


# --- the checks ------------------------------------------------------------------------------------------


def corpus():
    def prov(id_, path, text, **kw):
        return Provision(
            id=id_,
            instrument="eu-gdpr",
            jurisdiction="EU",
            language="en",
            version="oj",
            unit="article",
            kind="paragraph",
            path=tuple(path),
            text=text,
            order=0,
            **kw,
        )

    return Corpus(
        [
            prov(
                "eu-gdpr/art-83/5",
                ("83", "5"),
                "Infringements shall be subject to administrative fines up to 20 000 000 EUR, or in the "
                "case of an undertaking, up to 4 % of the total worldwide annual turnover, whichever is higher.",
            )
        ]
    )


def test_a_fact_whose_numbers_are_in_its_cited_text_passes():
    assert check_facts([fact()], corpus()) == []


def test_a_number_that_is_not_in_the_cited_text_is_reported():
    problems = check_facts(
        [fact(value={"amount": 30_000_000, "currency": "EUR", "turnover_percent": 4})], corpus()
    )
    assert any("30000000" in p and "gdpr-fine-upper-tier" in p for p in problems)


def test_a_date_that_is_not_in_the_cited_text_is_reported():
    problems = check_facts([fact(kind="application_date", value={"date": "2027-12-02"})], corpus())
    assert any("2027-12-02" in p for p in problems)


def test_a_missing_quote_unit_or_pinpoint_is_reported():
    assert any(
        "quote" in p for p in check_facts([fact(sources=(source(quotes=("not in the text",)),))], corpus())
    )
    assert any("unit" in p for p in check_facts([fact(sources=(source(unit_path=("999",)),))], corpus()))
    assert any(
        "pinpoint" in p
        for p in check_facts([fact(sources=(source(pinpoints=("eu-gdpr/art-83/9",)),))], corpus())
    )


def test_duplicate_keys_and_blank_summaries_are_reported():
    assert any("duplicate" in p for p in check_facts([fact(), fact()], corpus()))
    assert any("summary" in p for p in check_facts([fact(summary_es=" ")], corpus()))


def question(**kw):
    gold = GoldProvision("eu-gdpr", "article", ("83",))
    base = dict(
        id="q052",
        language="en",
        text="What is the highest fine?",
        type="numeric",
        route="table",
        phrasing="lay",
        jurisdictions=("EU",),
        gold=(gold,),
        expected_answer="Up to EUR 20,000,000 or 4 %.",
        author="claude",
        table_key="gdpr-fine-upper-tier",
    )
    return GoldQuestion(**{**base, **kw})


def test_every_numeric_question_must_name_a_key_that_exists_and_agree_with_it():
    assert check_gold_keys([question()], [fact()]) == []
    assert any("no-such-key" in p for p in check_gold_keys([question(table_key="no-such-key")], [fact()]))


def test_the_expected_answer_must_contain_the_numbers_of_its_fact():
    problems = check_gold_keys([question(expected_answer="Up to EUR 10,000,000 or 2 %.")], [fact()])
    assert any("20000000" in p for p in problems)
