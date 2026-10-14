"""
Fetch the Tier 1 EU acts from the Publications Office's Cellar API into data/raw/eur_lex_cellar/.

    python -m law_assistant.fetch.eu            # fetch what is not cached yet
    python -m law_assistant.fetch.eu --force    # fetch again
    python -m law_assistant.fetch.eu --only eu-gdpr-oj-es

EUR-Lex's own web pages answer scripts with a bot challenge, so we do not use them. Cellar is the
official route for programmatic access: a CELEX number URL, with the format and language chosen by the
Accept and Accept-Language headers, redirects to the document. Five acts in English and Spanish, as
XHTML (which keeps the article and recital structure we need in step 1.4): the GDPR (Official Journal
text and consolidated text), the AI Act (Official Journal text and the consolidated text of 27 July
2026) and the Digital Omnibus on AI.
"""

from __future__ import annotations

from collections.abc import Sequence

from law_assistant.fetch.documents import SourceDocument
from law_assistant.fetch.runner import run_command

BASE_URL = "https://publications.europa.eu"
SOURCE = "eur_lex_cellar"
LICENCE_OJ = "Commission Decision 2011/833/EU (reuse of Commission documents)"
LICENCE_CONSOLIDATED = "CC BY 4.0 (EUR-Lex consolidated texts); Commission Decision 2011/833/EU"
CREDIT_OJ = (
    "Source: EUR-Lex, © European Union, https://eur-lex.europa.eu. Only the version published in the "
    "Official Journal of the European Union is authentic. Indicate any summary or change."
)
CREDIT_CONSOLIDATED = CREDIT_OJ + " Consolidated text: a documentation tool with no legal effect."
LANGUAGES = {"en": "eng", "es": "spa"}  # our suffix -> the ISO 639-2 code Cellar expects

# act key -> (CELEX number, title, consolidated?)
ACTS = {
    "gdpr-oj": ("32016R0679", "GDPR, Regulation (EU) 2016/679, Official Journal text", False),
    "gdpr-consolidated": ("02016R0679-20160504", "GDPR, consolidated text (04/05/2016)", True),
    "ai-act-oj": ("32024R1689", "AI Act, Regulation (EU) 2024/1689, Official Journal text", False),
    "ai-act-consolidated-20260727": ("02024R1689-20260727", "AI Act, consolidated (27/07/2026)", True),
    "ai-omnibus-oj": (
        "32026R1744",
        "Digital Omnibus on AI, Regulation (EU) 2026/1744, Official Journal text",
        False,
    ),
}


def _docs() -> tuple[SourceDocument, ...]:
    docs = []
    for act, (celex, title, consolidated) in ACTS.items():
        for lang, code in LANGUAGES.items():
            docs.append(
                SourceDocument(
                    key=f"eu-{act}-{lang}",
                    title=f"{title} ({lang.upper()})",
                    source=SOURCE,
                    url=f"{BASE_URL}/resource/celex/{celex}",
                    suffix=".xhtml",
                    licence=LICENCE_CONSOLIDATED if consolidated else LICENCE_OJ,
                    credit=CREDIT_CONSOLIDATED if consolidated else CREDIT_OJ,
                    accept="application/xhtml+xml",
                    accept_language=code,
                )
            )
    return tuple(docs)


EU_DOCUMENTS = _docs()


def main(argv: Sequence[str] | None = None) -> int:
    return run_command(EU_DOCUMENTS, BASE_URL, "Fetch the Tier 1 EU acts from the Cellar API.", argv)


if __name__ == "__main__":
    raise SystemExit(main())
