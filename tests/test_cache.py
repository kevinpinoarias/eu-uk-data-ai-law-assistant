"""
Tests for fetching a document into the local cache: the file and a sidecar record are written once (with hash,
sizes and dates), a cached document is not fetched again, and a failed request leaves nothing behind.
All HTTP is faked; the tests never touch the network.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from datetime import UTC, datetime

import pytest

from law_assistant.fetch.cache import FetchError, fetch_document
from law_assistant.fetch.documents import SourceDocument
from law_assistant.fetch.http import Response
from law_assistant.fetch.polite import RobotsPolicy, Throttle

DOC = SourceDocument(
    key="uk-test-act",
    title="Test Act 2025",
    source="legislation_gov_uk",
    url="https://www.legislation.gov.uk/ukpga/2025/1/data.xml",
    suffix=".xml",
    licence="Open Government Licence v3.0",
    credit="Contains public sector information licensed under the Open Government Licence v3.0.",
)
BODY = b"<Legislation>hello</Legislation>"
WHEN = datetime(2026, 10, 14, 9, 30, tzinfo=UTC)


class FakeClient:
    def __init__(self, response: Response) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, url: str, headers: dict[str, str]) -> Response:
        self.calls.append((url, headers))
        return self.response


def _throttle() -> Throttle:
    return Throttle(0.0, clock=lambda: 0.0, sleep=lambda s: None)


def _fetch(tmp_path, client, *, force=False, robots=None):
    return fetch_document(
        DOC,
        tmp_path,
        client,
        _throttle(),
        robots or RobotsPolicy.from_text("User-agent: *\n"),
        "test-agent/1 (contact)",
        now=lambda: WHEN,
        force=force,
    )


def test_the_document_and_its_record_are_written(tmp_path):
    ok = Response(
        200, {"Last-Modified": "Wed, 30 Sep 2026 16:18:53 GMT", "Content-Type": "application/xml"}, BODY
    )
    result = _fetch(tmp_path, FakeClient(ok))

    assert result.cached is False
    assert result.path == tmp_path / "legislation_gov_uk" / "uk-test-act.xml"
    assert result.path.read_bytes() == BODY
    meta = json.loads((tmp_path / "legislation_gov_uk" / "uk-test-act.meta.json").read_text(encoding="utf-8"))
    assert meta["url"] == DOC.url
    assert meta["retrieved_at"] == "2026-10-14T09:30:00+00:00"
    assert meta["sha256"] == hashlib.sha256(BODY).hexdigest()
    assert meta["bytes"] == len(BODY)
    assert meta["last_modified"] == "Wed, 30 Sep 2026 16:18:53 GMT"
    assert meta["licence"] == DOC.licence
    assert meta["credit"] == DOC.credit
    assert meta["user_agent"] == "test-agent/1 (contact)"


def test_the_request_carries_our_user_agent():
    # the header check lives with the request itself
    client = FakeClient(Response(200, {}, BODY))
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as d:
        _fetch(Path(d), client)
    assert client.calls[0][0] == DOC.url
    assert client.calls[0][1]["User-Agent"] == "test-agent/1 (contact)"


def test_a_document_that_names_a_format_asks_for_it_with_an_accept_header(tmp_path):
    client = FakeClient(Response(200, {}, BODY))
    doc = replace(DOC, accept="application/xml")
    fetch_document(
        doc,
        tmp_path,
        client,
        _throttle(),
        RobotsPolicy.from_text("User-agent: *\n"),
        "test-agent/1 (contact)",
        now=lambda: WHEN,
    )
    assert client.calls[0][1] == {"User-Agent": "test-agent/1 (contact)", "Accept": "application/xml"}


def test_a_document_with_no_format_sends_no_accept_header(tmp_path):
    client = FakeClient(Response(200, {}, BODY))
    _fetch(tmp_path, client)
    assert "Accept" not in client.calls[0][1]


def test_a_cached_document_is_not_fetched_again(tmp_path):
    client = FakeClient(Response(200, {}, BODY))
    _fetch(tmp_path, client)
    second = _fetch(tmp_path, client)
    assert len(client.calls) == 1
    assert second.cached is True
    assert second.sha256 == hashlib.sha256(BODY).hexdigest()


def test_force_fetches_again_and_replaces_the_file(tmp_path):
    _fetch(tmp_path, FakeClient(Response(200, {}, b"old")))
    result = _fetch(tmp_path, FakeClient(Response(200, {}, b"new")), force=True)
    assert result.cached is False
    assert result.path.read_bytes() == b"new"


@pytest.mark.parametrize("status", [403, 404, 429, 500])
def test_a_non_200_response_raises_and_leaves_nothing_behind(tmp_path, status):
    with pytest.raises(FetchError, match=str(status)):
        _fetch(tmp_path, FakeClient(Response(status, {}, b"nope")))
    assert list(tmp_path.rglob("*")) == [] or all(p.is_dir() for p in tmp_path.rglob("*"))


def test_an_empty_body_is_an_error_not_a_cached_document(tmp_path):
    with pytest.raises(FetchError, match="empty"):
        _fetch(tmp_path, FakeClient(Response(200, {}, b"")))
    assert not (tmp_path / "legislation_gov_uk" / "uk-test-act.xml").exists()


def test_robots_disallow_stops_the_request_before_it_is_made(tmp_path):
    client = FakeClient(Response(200, {}, BODY))
    blocked = RobotsPolicy.from_text("User-agent: *\nDisallow: /ukpga/\n")
    with pytest.raises(PermissionError, match="robots.txt"):
        _fetch(tmp_path, client, robots=blocked)
    assert client.calls == []
