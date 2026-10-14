"""Being a good guest: wait between requests and follow robots.txt (disallow rules and the crawl delay)."""

from __future__ import annotations

import time
from collections.abc import Callable
from dataclasses import dataclass, field
from urllib.robotparser import RobotFileParser

from law_assistant.fetch.http import Client, FetchError


class Throttle:
    """Guarantees at least `min_interval` seconds between the starts of two requests."""

    def __init__(
        self,
        min_interval: float,
        clock: Callable[[], float] = time.monotonic,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.min_interval = min_interval
        self._clock = clock
        self._sleep = sleep
        self._last: float | None = None

    def wait(self) -> None:
        if self._last is not None:
            remaining = self.min_interval - (self._clock() - self._last)
            if remaining > 0:
                self._sleep(remaining)
        self._last = self._clock()


@dataclass(frozen=True)
class RobotsPolicy:
    """What a site's robots.txt asks of a crawler like us (the `*` rules)."""

    _parser: RobotFileParser = field(repr=False, compare=False)
    crawl_delay: float | None

    @classmethod
    def from_text(cls, text: str) -> RobotsPolicy:
        parser = RobotFileParser()
        parser.parse(text.splitlines())
        delay = parser.crawl_delay("*")
        return cls(parser, float(delay) if delay is not None else None)

    def can_fetch(self, url: str) -> bool:
        return self._parser.can_fetch("*", url)

    def min_interval(self, floor: float) -> float:
        """The slower of our own floor and the site's crawl delay."""
        return max(floor, self.crawl_delay or 0.0)


def load_robots(client: Client, base_url: str, user_agent: str, throttle: Throttle) -> RobotsPolicy:
    """Fetch and parse robots.txt. A 4xx means no restrictions (RFC 9309); other non-200 is an error."""
    throttle.wait()
    response = client.get(f"{base_url.rstrip('/')}/robots.txt", {"User-Agent": user_agent})
    if response.status == 200:
        return RobotsPolicy.from_text(response.body.decode("utf-8", errors="replace"))
    if 400 <= response.status < 500:
        return RobotsPolicy.from_text("")
    raise FetchError(
        f"robots.txt at {base_url} answered HTTP {response.status}; not fetching until it is readable"
    )
