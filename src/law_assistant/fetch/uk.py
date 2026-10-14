"""
Fetch the three Tier 1 UK documents from legislation.gov.uk into data/raw/legislation_gov_uk/.

    python -m law_assistant.fetch.uk            # fetch what is not cached yet
    python -m law_assistant.fetch.uk --force    # fetch again
    python -m law_assistant.fetch.uk --only uk-gdpr

Rules this follows (SOURCES.md): an identifying User-Agent (set FETCHER_CONTACT in .env or the environment),
robots.txt honoured, at least 5 seconds between requests (its robots.txt sets Crawl-delay: 5), well inside the
published cap of 1,500 requests per 5 minutes.
"""

from __future__ import annotations

from collections.abc import Sequence

from law_assistant.fetch.documents import SourceDocument
from law_assistant.fetch.runner import run_command

BASE_URL = "https://www.legislation.gov.uk"
SOURCE = "legislation_gov_uk"
LICENCE = "Open Government Licence v3.0"
CREDIT = "Contains public sector information licensed under the Open Government Licence v3.0."


def _doc(key: str, title: str, path: str) -> SourceDocument:
    return SourceDocument(
        key=key,
        title=title,
        source=SOURCE,
        url=f"{BASE_URL}/{path}/data.xml",
        suffix=".xml",
        licence=LICENCE,
        credit=CREDIT,
    )


UK_DOCUMENTS = (
    _doc("uk-gdpr", "UK GDPR (Regulation (EU) 2016/679 as it forms part of UK law)", "eur/2016/679"),
    _doc("uk-dpa-2018", "Data Protection Act 2018", "ukpga/2018/12"),
    _doc("uk-duaa-2025", "Data (Use and Access) Act 2025", "ukpga/2025/18"),
)


def main(argv: Sequence[str] | None = None) -> int:
    return run_command(UK_DOCUMENTS, BASE_URL, "Fetch the Tier 1 UK documents from legislation.gov.uk.", argv)


if __name__ == "__main__":
    raise SystemExit(main())
