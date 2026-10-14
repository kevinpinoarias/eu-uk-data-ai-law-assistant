"""
Checks of the chunker against the real parsed documents: the soundness checks on all fourteen files, the cap,
units that fit staying whole, stable ids, a reproducible build, and a few chunks whose text was read by eye.

These need data/parsed/ (run the parsers: `python -m law_assistant.parse.run_eu`, `run_uk`, `run_boe`). They are
skipped when it is absent, as in CI.
"""

from __future__ import annotations

import pytest

from law_assistant import settings
from law_assistant.chunk import run_chunk
from law_assistant.chunk.checks import check_chunks
from law_assistant.chunk.chunker import DEFAULT_MAX_WORDS, chunk_provisions, render_line, unit_key
from law_assistant.parse.store import read_jsonl

FILES = sorted(settings.PARSED_DIR.glob("*.jsonl"))

pytestmark = pytest.mark.skipif(
    len(FILES) < 14, reason="the parsed documents are not built (run the parsers in law_assistant.parse)"
)


@pytest.fixture(scope="module")
def corpus():
    """{file stem: (provisions, chunks)} for every parsed document."""
    out = {}
    for path in FILES:
        provisions = read_jsonl(path)
        out[path.stem] = (provisions, chunk_provisions(provisions))
    return out


def chunks_of(corpus, stem, citation):
    return [c for c in corpus[stem][1] if c.citation == citation]


def test_every_document_passes_the_soundness_checks(corpus):
    for stem, (provisions, chunks) in corpus.items():
        assert check_chunks(provisions, chunks, max_words=DEFAULT_MAX_WORDS) == [], stem


def test_the_cap_is_a_firm_ceiling_everywhere(corpus):
    assert max(c.words for _, chunks in corpus.values() for c in chunks) <= DEFAULT_MAX_WORDS


def test_a_unit_that_fits_in_the_cap_is_never_split(corpus):
    for stem, (provisions, chunks) in corpus.items():
        size = {}
        for p in provisions:
            key = (p.unit, unit_key(p))
            size[key] = size.get(key, 0) + len(render_line(p, len(key[1])).split())
        for c in chunks:
            if size[(c.unit, c.unit_path)] <= DEFAULT_MAX_WORDS:
                assert c.parts == 1, (stem, c.id)


def test_chunk_ids_are_unique_across_the_whole_corpus(corpus):
    ids = [c.id for _, chunks in corpus.values() for c in chunks]
    assert len(ids) == len(set(ids)) and len(ids) > 3000


def test_the_chunking_is_deterministic():
    provisions = read_jsonl(settings.PARSED_DIR / "eu-gdpr-oj-en.jsonl")
    assert chunk_provisions(provisions) == chunk_provisions(provisions)


def test_the_build_is_reproducible_and_writes_a_manifest(tmp_path, monkeypatch):
    monkeypatch.setattr(settings, "CHUNKS_DIR", tmp_path)
    first, problems = run_chunk.build()
    second, _ = run_chunk.build()
    assert problems == [] and first == second
    assert len(first["files"]) == 14 and first["max_words"] == DEFAULT_MAX_WORDS
    assert (tmp_path / "manifest.json").exists() and (tmp_path / "eu-gdpr-oj-en.jsonl").exists()


def test_gdpr_article_6_is_two_chunks_cut_between_paragraphs_2_and_3(corpus):
    first, second = chunks_of(corpus, "eu-gdpr-oj-en", "Article 6")
    assert (first.part, second.part, first.parts) == (1, 2, 2)
    assert first.text.startswith("1. Processing shall be lawful only if and to the extent that")
    assert "(f) processing is necessary for the purposes of the legitimate interests" in first.text
    assert second.text.startswith("3. The basis for the processing referred to in point (c) and (e)")
    assert (
        first.context
        == second.context
        == ("GDPR (Regulation (EU) 2016/679) | CHAPTER II — Principles | Article 6: Lawfulness of processing")
    )


def test_a_recital_is_one_chunk_with_its_number_in_the_context(corpus):
    (c,) = chunks_of(corpus, "eu-gdpr-oj-en", "Recital 47")
    assert c.context == "GDPR (Regulation (EU) 2016/679) | Recital 47"
    assert c.text.startswith("The legitimate interests of a controller")


def test_ai_act_annex_vi_is_one_chunk_with_its_four_items_in_both_languages(corpus):
    for stem, label in (("eu-ai-act-oj-en", "Annex VI"), ("eu-ai-act-oj-es", "Anexo VI")):
        (c,) = chunks_of(corpus, stem, label)
        assert c.text.count("\n") == 3 and c.text.startswith("1. ")
        assert len(c.provision_ids) == 5  # the annex heading and four items


def test_spanish_article_7_keeps_the_age_of_consent_and_its_date(corpus):
    (c,) = chunks_of(corpus, "es-lopdgdd-es", "Artículo 7")
    assert c.text.startswith(
        "1. El tratamiento de los datos personales de un menor de edad únicamente podrá fundarse en su "
        "consentimiento cuando sea mayor de catorce años."
    )
    assert (c.in_force_from, c.language, c.jurisdiction) == ("2018-12-07", "es", "ES")
    assert c.context.startswith(
        "LOPDGDD (Ley Orgánica 3/2018) | TÍTULO II — Principios de protección de datos | Artículo 7: "
    )


def test_a_spanish_disposition_restores_the_capital_of_its_spelled_out_markers(corpus):
    (c,) = chunks_of(corpus, "es-lopdgdd-es", "Disposición final tercera")
    assert "\nUno. El apartado 3 del artículo treinta y nueve" in c.text


def test_the_uk_schedule_that_is_thirty_thousand_words_becomes_many_chunks_cut_at_paragraphs(corpus):
    chunks = chunks_of(corpus, "uk-dpa-2018-en", "Schedule 19")
    assert len(chunks) > 80 and chunks[0].parts == len(chunks)
    assert all(c.text.strip() and not c.text.endswith(" ") for c in chunks)
    assert chunks[1].text.startswith("5. ")  # a new chunk starts at a numbered paragraph, not mid-text


def test_uk_dates_travel_with_the_chunks(corpus):
    dated = [c for c in corpus["uk-gdpr-en"][1] if c.in_force_from]
    assert dated and max(c.in_force_from for c in dated) >= "2026-02-05"
