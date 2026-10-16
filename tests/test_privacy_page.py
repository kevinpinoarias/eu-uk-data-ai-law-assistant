"""
Checks that the privacy notice (web/privacy.html) says what the code does: the retention period equals the one the
log enforces, a real trace row holds only the fields the notice lists and never the client's address, both
languages are present, no owner placeholder is left in it, and the colours reach
WCAG AA contrast.
"""

from __future__ import annotations

import json
import re

import pytest
from tests.test_web_page import ratio, tokens

from law_assistant import settings
from law_assistant.answer.service import AskService, RateLimiter
from law_assistant.answer.trace import DEFAULT_RETENTION_DAYS, TraceLog
from law_assistant.serve import PRIVACY_PLACEHOLDERS, DemoPipeline, launch_blockers

NOTICE = (settings.PROJECT_ROOT / "web" / "privacy.html").read_text(encoding="utf-8")


def section(lang: str) -> str:
    match = re.search(rf'<section id="{lang}" lang="{lang}".*?</section>', NOTICE, re.DOTALL)
    assert match, f"no {lang} section"
    return match.group(0)


def test_both_languages_are_present_with_a_heading_each():
    for lang in ("en", "es"):
        assert section(lang).count("<h1") == 1
    assert 'lang="en"' in NOTICE and 'lang="es"' in NOTICE


def test_the_retention_period_in_the_notice_is_the_one_the_log_enforces():
    days = str(DEFAULT_RETENTION_DAYS)
    assert f"<strong>{days} days</strong>" in section("en")
    assert f"<strong>{days} días</strong>" in section("es")
    assert f"{days} days" in (settings.PROJECT_ROOT / "web" / "index.html").read_text(encoding="utf-8")


def test_no_owner_placeholder_is_left_and_the_check_would_notice_one():
    assert not re.search(r"\[[A-Z ,]+\]", NOTICE)
    assert launch_blockers() == []
    assert launch_blockers("Run by [OWNER NAME], hosted by [HOSTING PROVIDER].") == [
        "[OWNER NAME]",
        "[HOSTING PROVIDER]",
    ]
    assert set(PRIVACY_PLACEHOLDERS) == {
        "[OWNER NAME]",
        "[CITY, COUNTRY]",
        "[CONTACT EMAIL]",
        "[HOSTING PROVIDER]",
    }


def test_the_notice_names_the_owner_the_place_a_contact_address_and_the_uk_regulator():
    for text in (section("en"), section("es")):
        assert "Kevin Pino Arias" in text and "Glasgow" in text
        assert "mailto:" in text and "ico.org.uk" in text


# What the notice tells the reader is kept, in the code's field names. Anything else in a row is a change that
# the notice must be updated for first.
DECLARED_FIELDS = {
    "ts", "question", "language", "route", "passages", "timings", "seconds", "kind", "reason",
    "fact_key", "invalid_citations", "error",
}  # fmt: skip


def test_a_real_trace_row_holds_only_declared_fields_and_never_the_client_address(tmp_path):
    log = tmp_path / "traces.jsonl"
    service = AskService(DemoPipeline(), trace=TraceLog(log), limiter=RateLimiter())
    status, _ = service.ask({"question": "What is the highest fine?"}, client="203.0.113.77")
    assert status == 200
    text = log.read_text(encoding="utf-8")
    assert "203.0.113.77" not in text
    row = json.loads(text.splitlines()[0])
    assert set(row) <= DECLARED_FIELDS, set(row) - DECLARED_FIELDS


def test_the_notice_names_the_recipients_and_the_rights():
    en, es = section("en"), section("es")
    for text in (en, es):
        assert "Gemini" in text and "aepd.es" in text and "6" in text
    assert "not legal advice" in en and "No es asesoramiento jurídico" in es


def test_the_notice_loads_nothing_external_and_runs_no_script():
    assert "<script" not in NOTICE and "src=" not in NOTICE
    assert not re.search(r"""<link[^>]+href=["']https?://""", NOTICE)


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize(("fg", "bg"), [("ink", "bg"), ("muted", "bg"), ("accent", "bg"), ("todo-ink", "todo-bg"),
                                        ("ink", "card")])  # fmt: skip
def test_the_notice_colours_reach_wcag_aa_contrast(theme, fg, bg):
    light = re.search(r":root \{(.*?)\}", NOTICE, re.DOTALL).group(1)
    dark = re.search(r"prefers-color-scheme: dark\).*?\{(.*?)\}\s*\}", NOTICE, re.DOTALL).group(1)
    t = tokens(light) if theme == "light" else {**tokens(light), **tokens(dark)}
    assert ratio(t[fg], t[bg]) >= 4.5, f"{theme}: {fg} on {bg} is {ratio(t[fg], t[bg]):.2f}"
