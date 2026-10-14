"""A tiny HTTP layer: a Response value, a Client protocol (so tests can fake it) and a stdlib client."""

from __future__ import annotations

import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Protocol


class FetchError(RuntimeError):
    """A source did not give us a usable document."""


@dataclass(frozen=True)
class Response:
    status: int
    headers: dict[str, str]
    body: bytes


class Client(Protocol):
    def get(self, url: str, headers: dict[str, str]) -> Response: ...


def header(headers: dict[str, str], name: str) -> str | None:
    """Look a header up without caring about its capitalisation."""
    wanted = name.lower()
    return next((value for key, value in headers.items() if key.lower() == wanted), None)


class UrllibClient:
    """GET over http(s) with the standard library. Redirects are followed; HTTP errors become a Response."""

    def __init__(self, timeout: float = 60.0) -> None:
        self.timeout = timeout

    def get(self, url: str, headers: dict[str, str]) -> Response:
        if not url.startswith(("https://", "http://")):
            raise ValueError(f"Only http(s) URLs are fetched, got: {url!r}")
        request = urllib.request.Request(url, headers=headers)  # noqa: S310 (scheme checked above)
        try:
            with urllib.request.urlopen(request, timeout=self.timeout) as reply:  # noqa: S310
                return Response(reply.status, dict(reply.headers.items()), reply.read())
        except urllib.error.HTTPError as error:
            return Response(error.code, dict(error.headers.items()), error.read())
