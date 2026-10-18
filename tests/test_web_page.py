"""
Checks on the web page (web/index.html) that need no browser: the English and Spanish texts match key for key,
the static English text is what the dictionary says, every control is labelled, and every pair of text and
background colours reaches the WCAG contrast of 4.5:1 in both the light and the dark theme.
"""

from __future__ import annotations

import json
import re
from html.parser import HTMLParser

import pytest

from law_assistant import settings

PAGE = (settings.PROJECT_ROOT / "web" / "index.html").read_text(encoding="utf-8")


def dictionary() -> dict:
    match = re.search(r'<script type="application/json" id="i18n">(.*?)</script>', PAGE, re.DOTALL)
    assert match, "the page has no i18n dictionary"
    return json.loads(match.group(1))


def test_english_and_spanish_have_exactly_the_same_keys_and_no_empty_text():
    d = dictionary()
    assert set(d) == {"en", "es"} and set(d["en"]) == set(d["es"])
    for lang in d:
        assert all(isinstance(v, (str, list, dict)) and v for v in d[lang].values()), lang


def test_every_data_i18n_key_used_in_the_markup_exists_in_both_languages():
    d = dictionary()
    keys = set(re.findall(r'data-i18n(?:-[a-z]+)?="([^"]+)"', PAGE))
    assert keys and keys <= set(d["en"]) and keys <= set(d["es"])


class Collector(HTMLParser):
    def __init__(self):
        super().__init__()
        self.elements, self.stack = [], []

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


def parse():
    c = Collector()
    c.feed(PAGE)
    return c.elements


def test_the_static_english_text_matches_the_english_dictionary():
    d = dictionary()["en"]
    for key in ("title", "subtitle", "qLabel", "ask", "noticeStrong"):
        assert d[key] in PAGE, key


def test_the_page_declares_its_language_and_has_a_skip_link_with_a_target():
    elements = parse()
    html = next(a for t, a in elements if t == "html")
    assert html.get("lang") == "en"
    skip = next(a for t, a in elements if t == "a" and "skip" in (a.get("class") or ""))
    assert skip["href"].startswith("#") and any(a.get("id") == skip["href"][1:] for _, a in elements)


def test_the_text_box_has_a_label_and_a_description_and_a_length_limit():
    elements = parse()
    box = next(a for t, a in elements if t == "textarea")
    assert box.get("id") and re.search(rf'<label[^>]+for="{box["id"]}"', PAGE)
    assert box.get("aria-describedby") and box.get("maxlength") == "1000" and "required" in box


def test_no_inline_event_handlers_and_no_external_resources():
    assert not re.search(r"\son[a-z]+=", PAGE)
    assert not re.search(r'(?:src|href)="https?://(?!github\.com/kevinpinoarias)', PAGE)


def test_the_result_area_is_announced_and_errors_are_alerts():
    assert 'aria-live="polite"' in PAGE
    assert 'setAttribute("role", "alert")' in PAGE  # the error paragraph is created by the script


def test_the_page_takes_an_access_code_from_the_link_fragment_and_sends_it_in_a_header():
    # An invited visitor's link is https://host/#code=...; a fragment is never sent to a server.
    d = dictionary()
    assert d["en"]["accessNeeded"] and d["es"]["accessNeeded"]
    assert "access code" in d["en"]["accessNeeded"].lower() and "código" in d["es"]["accessNeeded"]
    # A visitor who arrives without the invited link (the address is public) is told where to ask for one.
    assert (
        "ask the owner" in d["en"]["accessNeeded"].lower()
        and "privacy notice" in d["en"]["accessNeeded"].lower()
    )
    assert "aviso de privacidad" in d["es"]["accessNeeded"].lower()
    script = PAGE.split("<script>")[-1]
    assert "window.location.hash" in script and "sessionStorage" in script and "X-Access-Code" in script
    assert "replaceState" in script  # the code is taken out of the address bar and the history
    assert "status === 401" in script  # a refused visitor sees the plain message, in their language


def test_the_page_shows_the_servers_notice_above_an_answer_given_in_general_terms():
    # For a question about the user's own situation the server answers in general terms and sends a notice
    # (general information, not legal advice, see a professional); the page must show it, announced, above the answer.
    script = PAGE.split("<script>")[-1]
    assert "data.notice" in script
    assert (
        re.search(r'el\("p",\s*"notice"', script) or 'className = "notice"' in script or '"notice"' in script
    )
    assert ".notice" in PAGE.split("<style>")[1].split("</style>")[0]  # and it is styled


def test_the_footer_says_the_question_text_and_the_address_are_not_kept():
    for lang in ("en", "es"):
        text = dictionary()[lang]["privacy"]
        assert "30" in text and ("not kept" in text or "no se conserva" in text)
        assert "logged without your address" not in text


def test_the_footer_carries_each_publisher_s_required_credit_in_both_languages():
    # SOURCES.md lists the credit line each publisher requires; the page shows the texts, so it shows the credits.
    d = dictionary()
    for lang in ("en", "es"):
        credits = d[lang]["credits"]
        assert "Source: EUR-Lex, © European Union" in credits, lang
        assert "Open Government Licence v3.0" in credits, lang
        assert "Fuente de los datos: Agencia Estatal Boletín Oficial del Estado" in credits, lang
        assert "meramente informativo" in credits, lang
    assert 'data-i18n="credits"' in PAGE


def test_the_language_buttons_say_which_is_selected():
    assert PAGE.count("aria-pressed") >= 2


def test_a_slow_answer_shows_a_waking_message_in_the_announced_status_line_and_clears_it():
    # A host that scales to zero starts cold: the first visitor waits for the container and the model. The page
    # says so after a few seconds, in both languages, in the status element that screen readers announce.
    d = dictionary()
    assert "wak" in d["en"]["waking"].lower() and "desp" in d["es"]["waking"].lower()
    assert re.search(r'id="status"[^>]*role="status"|role="status"[^>]*id="status"', PAGE)
    script = PAGE.split("<script>")[-1]
    assert re.search(r"setTimeout\([^;]*waking", script, re.DOTALL)
    assert "clearTimeout" in script


# --- contrast ------------------------------------------------------------------------------------------------


def luminance(hex_colour: str) -> float:
    h = hex_colour.lstrip("#")
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def lin(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    return 0.2126 * lin(r) + 0.7152 * lin(g) + 0.0722 * lin(b)


def ratio(a: str, b: str) -> float:
    la, lb = sorted((luminance(a), luminance(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def tokens(block: str) -> dict[str, str]:
    return dict(re.findall(r"--([a-z-]+):\s*(#[0-9a-fA-F]{6})", block))


def theme_blocks():
    light = re.search(r":root \{(.*?)\}", PAGE, re.DOTALL).group(1)
    dark = re.search(r"prefers-color-scheme: dark\).*?\{(.*?)\}\s*\}", PAGE, re.DOTALL).group(1)
    return {"light": tokens(light), "dark": {**tokens(light), **tokens(dark)}}


PAIRS = [
    ("ink", "bg"), ("ink", "card"), ("muted", "bg"), ("muted", "card"), ("accent", "bg"), ("accent", "card"),
    ("accent-ink", "accent"), ("ok", "card"), ("no", "card"), ("ink", "warn-bg"),
]  # fmt: skip


@pytest.mark.parametrize("theme", ["light", "dark"])
@pytest.mark.parametrize(("fg", "bg"), PAIRS)
def test_text_and_background_colours_reach_wcag_aa_contrast(theme, fg, bg):
    t = theme_blocks()[theme]
    assert ratio(t[fg], t[bg]) >= 4.5, f"{theme}: {fg} on {bg} is {ratio(t[fg], t[bg]):.2f}"
