"""The HTTP client only speaks http(s): a manifest URL must never be able to read a local file."""

from __future__ import annotations

import pytest

from law_assistant.fetch.http import UrllibClient


@pytest.mark.parametrize(
    "url", ["file:///etc/passwd", "ftp://example.org/x", "data:text/plain,hi", "/relative/path"]
)
def test_non_http_urls_are_refused_before_any_request(url):
    with pytest.raises(ValueError, match="http"):
        UrllibClient().get(url, {})
