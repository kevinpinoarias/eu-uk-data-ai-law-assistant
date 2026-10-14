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

import argparse
from collections.abc import Sequence

from law_assistant import settings
from law_assistant.fetch.cache import fetch_document
from law_assistant.fetch.documents import SourceDocument
from law_assistant.fetch.http import UrllibClient
from law_assistant.fetch.polite import Throttle, load_robots

BASE_URL = "https://www.legislation.gov.uk"
SOURCE = "legislation_gov_uk"
LICENCE = "Open Government Licence v3.0"
CREDIT = "Contains public sector information licensed under the Open Government Licence v3.0."
MIN_INTERVAL = 5.0  # seconds between requests: our floor, raised if robots.txt asks for more


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
    parser = argparse.ArgumentParser(description="Fetch the Tier 1 UK documents from legislation.gov.uk.")
    parser.add_argument("--force", action="store_true", help="fetch again even if cached")
    parser.add_argument(
        "--only", action="append", metavar="KEY", help="fetch only this document (repeatable)"
    )
    args = parser.parse_args(argv)

    chosen = [d for d in UK_DOCUMENTS if not args.only or d.key in args.only]
    unknown = set(args.only or ()) - {d.key for d in UK_DOCUMENTS}
    if unknown:
        parser.error(f"unknown document key(s): {', '.join(sorted(unknown))}")

    settings.load_env_file()
    user_agent = settings.user_agent()
    client = UrllibClient()
    throttle = Throttle(MIN_INTERVAL)
    robots = load_robots(client, BASE_URL, user_agent, throttle)
    throttle.min_interval = robots.min_interval(MIN_INTERVAL)

    for doc in chosen:
        result = fetch_document(doc, settings.RAW_DIR, client, throttle, robots, user_agent, force=args.force)
        state = "cached" if result.cached else "fetched"
        print(f"{state:8} {doc.key:14} {result.bytes:>10,} bytes  sha256 {result.sha256[:12]}  {result.path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
