"""The command-line part shared by every source: pick documents, load robots.txt, fetch politely, report."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from law_assistant import settings
from law_assistant.fetch.cache import fetch_document
from law_assistant.fetch.documents import SourceDocument
from law_assistant.fetch.http import UrllibClient
from law_assistant.fetch.polite import Throttle, load_robots

MIN_INTERVAL = 5.0  # seconds between requests: our floor, raised if the site's robots.txt asks for more


def select_documents(documents: Sequence[SourceDocument], only: Sequence[str] | None) -> list[SourceDocument]:
    """All documents, or only the requested keys (in manifest order). An unknown key is an error."""
    if not only:
        return list(documents)
    unknown = set(only) - {d.key for d in documents}
    if unknown:
        raise ValueError(f"unknown document key(s): {', '.join(sorted(unknown))}")
    return [d for d in documents if d.key in only]


def run_command(
    documents: Sequence[SourceDocument], base_url: str, description: str, argv: Sequence[str] | None = None
) -> int:
    parser = argparse.ArgumentParser(description=description)
    parser.add_argument("--force", action="store_true", help="fetch again even if cached")
    parser.add_argument(
        "--only", action="append", metavar="KEY", help="fetch only this document (repeatable)"
    )
    args = parser.parse_args(argv)
    try:
        chosen = select_documents(documents, args.only)
    except ValueError as error:
        parser.error(str(error))

    settings.load_env_file()
    user_agent = settings.user_agent()
    client = UrllibClient()
    throttle = Throttle(MIN_INTERVAL)
    robots = load_robots(client, base_url, user_agent, throttle)
    throttle.min_interval = robots.min_interval(MIN_INTERVAL)

    for doc in chosen:
        result = fetch_document(doc, settings.RAW_DIR, client, throttle, robots, user_agent, force=args.force)
        state = "cached" if result.cached else "fetched"
        print(f"{state:8} {doc.key:22} {result.bytes:>10,} bytes  sha256 {result.sha256[:12]}  {result.path}")
    return 0
