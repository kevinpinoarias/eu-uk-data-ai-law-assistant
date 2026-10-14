"""
Fetch a document once into data/raw/ and remember where it came from.

Each document is saved as `<source>/<key><suffix>` next to `<key>.meta.json` (URL, retrieval time, hash, size,
licence, credit, the User-Agent used). A cached document is never fetched again unless forced. Nothing is left
behind when a request fails: files are written to a temporary name and renamed into place.
"""

from __future__ import annotations

import hashlib
import json
import os
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from law_assistant.fetch.documents import SourceDocument
from law_assistant.fetch.http import Client, FetchError, header
from law_assistant.fetch.polite import RobotsPolicy, Throttle

__all__ = ["FetchError", "Retrieval", "fetch_document"]


@dataclass(frozen=True)
class Retrieval:
    path: Path
    meta_path: Path
    bytes: int
    sha256: str
    cached: bool  # True when the document was already in the cache and no request was made


def _write_atomic(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    partial = path.with_name(path.name + ".part")
    partial.write_bytes(data)
    os.replace(partial, path)


def fetch_document(
    doc: SourceDocument,
    raw_dir: Path,
    client: Client,
    throttle: Throttle,
    robots: RobotsPolicy,
    user_agent: str,
    *,
    now: Callable[[], datetime] = lambda: datetime.now(UTC),
    force: bool = False,
) -> Retrieval:
    path = raw_dir / doc.source / f"{doc.key}{doc.suffix}"
    meta_path = path.with_name(f"{doc.key}.meta.json")

    if path.exists() and meta_path.exists() and not force:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        return Retrieval(path, meta_path, meta["bytes"], meta["sha256"], cached=True)

    if not robots.can_fetch(doc.url):
        raise PermissionError(f"{doc.url} is disallowed by robots.txt; not fetching it.")

    throttle.wait()
    headers = {"User-Agent": user_agent}
    if doc.accept:
        headers["Accept"] = doc.accept
    response = client.get(doc.url, headers)
    if response.status != 200:
        raise FetchError(f"{doc.url} answered HTTP {response.status}")
    if not response.body:
        raise FetchError(f"{doc.url} returned an empty body")

    digest = hashlib.sha256(response.body).hexdigest()
    meta = {
        "key": doc.key,
        "title": doc.title,
        "url": doc.url,
        "retrieved_at": now().isoformat(),
        "http_status": response.status,
        "last_modified": header(response.headers, "Last-Modified"),
        "content_type": header(response.headers, "Content-Type"),
        "bytes": len(response.body),
        "sha256": digest,
        "user_agent": user_agent,
        "licence": doc.licence,
        "credit": doc.credit,
    }
    _write_atomic(path, response.body)
    _write_atomic(meta_path, json.dumps(meta, indent=2, ensure_ascii=False).encode("utf-8"))
    return Retrieval(path, meta_path, len(response.body), digest, cached=False)
