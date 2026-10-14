"""
Tests for the gold-set checks (step 2.0): the rules every question must meet, the checks across the set, the
overlap warning that guards against leakage, and the checks of the gold against the parsed corpus (the unit
exists, the pinpoint ids exist, the supporting quotes are in the text).
"""

from __future__ import annotations

from law_assistant.evaluation.checks import (
    Corpus,
    check_against_corpus,
    check_mix,
    check_questions,
    overlap_ratio,
    overlap_warnings,
)
from law_assistant.evaluation.gold import GoldProvision, GoldQuestion
from law_assistant.model import Provision


def gp(**kw):
    base = dict(instrument="eu-gdpr", unit="article", unit_path=("17",), pinpoints=())
    return GoldProvision(**{**base, **kw})


def q(**kw):
    base = dict(
        id="q001",
        language="en",
        text="Can I make a company delete the data it holds about me?",
        type="lookup",
        route="retrieve",
        phrasing="lay",
        jurisdictions=("EU",),
        gold=(gp(),),
        expected_answer="Yes, in the cases listed in Article 17.",
        author="claude",
    )
    return GoldQuestion(**{**base, **kw})


def refuse(**kw):
    base = dict(
        id="q900",
        text="Is my company compliant with the law?",
        type="refuse",
        route="refuse",
        gold=(),
        refusal_reason="legal_advice",
        jurisdictions=(),
    )
    return q(**{**base, **kw})


def numeric(**kw):
    base = dict(
        id="q800",
        text="What is the biggest fine?",
        type="numeric",
        route="table",
        gold=(),
        table_key="gdpr-fine-upper",
    )
    return q(**{**base, **kw})


def problems(*questions):
    return check_questions(list(questions))


def test_a_good_question_of_each_route_has_no_problems():
    assert (
        problems(
            q(), refuse(), numeric(), q(id="q002", type="as_of", as_of="2026-10-14", text="Another one?")
        )
        == []
    )


def test_the_id_must_have_the_standard_form():
    assert any("id" in p for p in problems(q(id="question-1")))


def test_the_route_must_follow_from_the_type():
    assert any("route" in p for p in problems(q(route="refuse")))
    assert any("route" in p for p in problems(numeric(route="retrieve")))
    assert any("route" in p for p in problems(refuse(route="retrieve")))


def test_a_retrieval_question_needs_a_primary_gold_provision_and_a_jurisdiction():
    assert any("primary" in p for p in problems(q(gold=())))
    assert any("primary" in p for p in problems(q(gold=(gp(role="acceptable"),))))
    assert any("jurisdiction" in p for p in problems(q(jurisdictions=())))


def test_a_refusal_has_no_gold_and_a_reason_and_a_table_question_a_key():
    assert any("no gold" in p for p in problems(refuse(gold=(gp(),))))
    assert any("reason" in p for p in problems(refuse(refusal_reason=None)))
    assert any("table_key" in p for p in problems(numeric(table_key=None)))
    assert any("reason" in p for p in problems(q(refusal_reason="legal_advice")))


def test_an_as_of_question_needs_a_valid_date_and_any_date_must_be_valid():
    assert any("as_of" in p for p in problems(q(type="as_of", as_of=None)))
    assert any("as_of" in p for p in problems(q(as_of="14/10/2026")))
    assert any("as_of" in p for p in problems(q(as_of="2026-13-40")))
    assert problems(q(as_of="2026-10-14")) == []


def test_text_and_expected_answer_must_not_be_blank():
    assert any("text" in p for p in problems(q(text="  ")))
    assert any("expected_answer" in p for p in problems(q(expected_answer="")))


def test_ids_and_texts_must_be_unique_ignoring_case_and_spacing():
    assert any("duplicate id" in p for p in problems(q(), q(text="Different?")))
    assert any(
        "duplicate text" in p
        for p in problems(q(), q(id="q002", text="can i make a company   DELETE the data it holds about me?"))
    )


def test_the_mix_check_reports_each_type_language_and_reason_that_misses_its_target():
    qs = [q(), refuse(), refuse(id="q901", text="Another refusal?")]
    found = check_mix(qs, types={"lookup": 1, "refuse": 1}, languages={"en": 2}, reasons={"legal_advice": 1})
    assert any("refuse" in p and "2" in p for p in found)
    assert any("language" in p and "en" in p for p in found)
    assert not any("lookup" in p for p in found)
    assert any("legal_advice" in p for p in found)


def test_the_mix_check_passes_when_every_target_is_met():
    qs = [q(), refuse()]
    assert (
        check_mix(qs, types={"lookup": 1, "refuse": 1}, languages={"en": 2}, reasons={"legal_advice": 1})
        == []
    )


# --- leakage ---------------------------------------------------------------------------------------------


def test_overlap_is_the_share_of_the_questions_longer_words_found_in_the_gold_text():
    gold_text = (
        "The data subject shall have the right to obtain the erasure of personal data concerning him or her"
    )
    assert overlap_ratio("Can I make a company delete the data it holds about me?", [gold_text]) < 0.4
    assert (
        overlap_ratio("Does the data subject have the right to obtain erasure of personal data?", [gold_text])
        > 0.7
    )


def test_questions_that_copy_their_gold_text_are_warned_about():
    corpus = Corpus(
        [
            Provision(
                id="eu-gdpr/art-17/1",
                instrument="eu-gdpr",
                jurisdiction="EU",
                language="en",
                version="oj",
                unit="article",
                kind="paragraph",
                path=("17", "1"),
                order=0,
                text="The data subject shall have the right to obtain the erasure of personal data concerning him or her.",
            )
        ]
    )
    copied = q(
        text="Does the data subject have the right to obtain the erasure of personal data concerning him?"
    )
    assert any("q001" in w for w in overlap_warnings([copied], corpus, threshold=0.6))
    assert overlap_warnings([q()], corpus, threshold=0.6) == []


# --- against the corpus ----------------------------------------------------------------------------------


def prov(
    id_, path, text, *, unit="article", version="oj", language="en", instrument="eu-gdpr", kind="paragraph"
):
    return Provision(
        id=id_,
        instrument=instrument,
        jurisdiction="EU",
        language=language,
        version=version,
        unit=unit,
        kind=kind,
        path=tuple(path),
        text=text,
        order=0,
    )


def mini_corpus():
    return Corpus(
        [
            prov(
                "eu-gdpr/art-17/1",
                ("17", "1"),
                "The data subject shall have the right to obtain the erasure of personal data.",
            ),
            prov("eu-gdpr/art-17/1/a", ("17", "1", "a"), "the data are no longer necessary;", kind="point"),
            prov("eu-gdpr/art-37/1/c", ("37", "1", "c"), "old wording and more", version="oj"),
            prov(
                "eu-gdpr/art-37/1/c", ("37", "1", "c"), "new wording or less", version="consolidated-20160504"
            ),
            prov(
                "eu-gdpr/art-17/1",
                ("17", "1"),
                "El interesado tendrá derecho a obtener la supresión.",
                language="es",
            ),
        ]
    )


def test_a_gold_provision_that_exists_passes():
    good = q(gold=(gp(pinpoints=("eu-gdpr/art-17/1/a",), quotes=("no longer  necessary",)),))
    assert check_against_corpus([good], mini_corpus()) == []


def test_a_missing_unit_pinpoint_or_quote_is_reported():
    corpus = mini_corpus()
    assert any("unit" in p for p in check_against_corpus([q(gold=(gp(unit_path=("999",)),))], corpus))
    assert any(
        "pinpoint" in p
        for p in check_against_corpus([q(gold=(gp(pinpoints=("eu-gdpr/art-17/9",)),))], corpus)
    )
    assert any(
        "quote" in p for p in check_against_corpus([q(gold=(gp(quotes=("not in the text",)),))], corpus)
    )
    assert any(
        "instrument" in p for p in check_against_corpus([q(gold=(gp(instrument="xx-unknown"),))], corpus)
    )


def test_a_version_filter_means_the_quote_must_be_in_that_version():
    corpus = mini_corpus()
    in_new = q(gold=(gp(unit_path=("37",), quotes=("new wording",), version="consolidated-20160504"),))
    in_old_only = q(gold=(gp(unit_path=("37",), quotes=("old wording",), version="consolidated-20160504"),))
    assert check_against_corpus([in_new], corpus) == []
    assert any("quote" in p for p in check_against_corpus([in_old_only], corpus))


def test_a_language_filter_means_the_quote_must_be_in_that_language():
    corpus = mini_corpus()
    spanish = q(gold=(gp(quotes=("derecho a obtener la supresión",), language="es"),))
    wrong = q(gold=(gp(quotes=("derecho a obtener la supresión",), language="en"),))
    assert check_against_corpus([spanish], corpus) == []
    assert any("quote" in p for p in check_against_corpus([wrong], corpus))


def test_problems_name_the_question_they_belong_to():
    bad = q(id="q042", gold=(gp(unit_path=("999",)),))
    assert all(p.startswith("q042") for p in check_against_corpus([bad], mini_corpus()))


def test_common_words_count_for_less_when_the_overlap_is_weighted():
    idf = {"consent": 0.1, "minor": 0.1, "adult": 4.0}
    gold = ["consent minor"]
    assert overlap_ratio("adult consent minor?", gold) > 0.6
    assert overlap_ratio("adult consent minor?", gold, idf=idf) < 0.1
    # a word the corpus never saw is as telling as the rarest known word
    assert overlap_ratio("zebra consent?", ["zebra consent"], idf=idf) == 1.0
    assert overlap_ratio("zebra consent?", ["consent"], idf=idf) < 0.1


def test_the_corpus_gives_rarer_words_a_higher_weight_by_language():
    corpus = Corpus(
        [
            prov("eu-gdpr/art-1", ("1",), "data about erasure", kind="article"),
            prov("eu-gdpr/art-2", ("2",), "data about portability", kind="article"),
            prov("eu-gdpr/art-3", ("3",), "data about scope", kind="article"),
            prov("eu-gdpr/art-4", ("4",), "datos sobre alcance", kind="article", language="es"),
        ]
    )
    idf = corpus.idf("en")
    assert idf["data"] < idf["erasure"] and idf["about"] < idf["scope"]
    assert "datos" not in idf and "datos" in corpus.idf("es")


def test_a_copy_of_distinctive_wording_is_still_warned_about_in_a_larger_corpus():
    filler = [
        prov(f"eu-gdpr/art-{n}", (str(n),), "data protection rules apply here", kind="article")
        for n in range(5, 15)
    ]
    erasure = prov(
        "eu-gdpr/art-1",
        ("1",),
        "The data subject has the erasure right concerning personal data",
        kind="article",
    )
    corpus = Corpus([erasure, *filler])
    copied = q(
        text="Does the data subject have the erasure right concerning personal data?",
        gold=(gp(unit_path=("1",)),),
    )
    natural = q(
        id="q002", text="Can a company be told to delete my personal data?", gold=(gp(unit_path=("1",)),)
    )
    assert any("q001" in w for w in overlap_warnings([copied], corpus))
    assert overlap_warnings([natural], corpus) == []
