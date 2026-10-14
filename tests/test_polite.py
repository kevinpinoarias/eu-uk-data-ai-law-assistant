"""
Tests for polite fetching: wait between requests, honour robots.txt (disallow rules and the crawl
delay), and never go faster than our own floor. Time is faked, so these tests never sleep and
never touch the network.
"""

from __future__ import annotations

from law_assistant.fetch.http import Response
from law_assistant.fetch.polite import RobotsPolicy, Throttle, load_robots


class FakeTime:
    """A clock that only moves when something sleeps."""

    def __init__(self) -> None:
        self.now = 1000.0
        self.slept: list[float] = []

    def clock(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.slept.append(seconds)
        self.now += seconds


def test_the_first_request_does_not_wait():
    t = FakeTime()
    Throttle(5.0, clock=t.clock, sleep=t.sleep).wait()
    assert t.slept == []


def test_a_second_request_waits_out_the_rest_of_the_interval():
    t = FakeTime()
    throttle = Throttle(5.0, clock=t.clock, sleep=t.sleep)
    throttle.wait()
    t.now += 2.0  # two seconds of our own work between requests
    throttle.wait()
    assert t.slept == [3.0]


def test_no_wait_when_the_interval_has_already_passed():
    t = FakeTime()
    throttle = Throttle(5.0, clock=t.clock, sleep=t.sleep)
    throttle.wait()
    t.now += 9.0
    throttle.wait()
    assert t.slept == []


ROBOTS = "User-agent: *\nCrawl-delay: 5\nSitemap: http://www.legislation.gov.uk/sitemap-static.xml\n"


def test_robots_with_no_disallow_allows_everything_and_reports_the_crawl_delay():
    policy = RobotsPolicy.from_text(ROBOTS)
    assert policy.can_fetch("https://www.legislation.gov.uk/ukpga/2018/12/data.xml")
    assert policy.crawl_delay == 5.0


def test_a_disallowed_path_is_not_fetchable():
    policy = RobotsPolicy.from_text("User-agent: *\nDisallow: /private/\n")
    assert not policy.can_fetch("https://example.org/private/x.xml")
    assert policy.can_fetch("https://example.org/public/x.xml")


def test_the_interval_is_never_below_our_floor_even_if_robots_allows_faster():
    fast = RobotsPolicy.from_text("User-agent: *\nCrawl-delay: 1\n")
    assert fast.min_interval(floor=5.0) == 5.0


def test_a_slower_crawl_delay_than_our_floor_wins():
    slow = RobotsPolicy.from_text("User-agent: *\nCrawl-delay: 12\n")
    assert slow.min_interval(floor=5.0) == 12.0


def test_no_crawl_delay_means_the_floor():
    assert RobotsPolicy.from_text("User-agent: *\n").min_interval(floor=5.0) == 5.0


class FakeClient:
    def __init__(self, response: Response) -> None:
        self.response = response
        self.calls: list[tuple[str, dict[str, str]]] = []

    def get(self, url: str, headers: dict[str, str]) -> Response:
        self.calls.append((url, headers))
        return self.response


def test_load_robots_fetches_robots_txt_with_our_user_agent_after_waiting():
    t = FakeTime()
    throttle = Throttle(5.0, clock=t.clock, sleep=t.sleep)
    client = FakeClient(Response(200, {}, ROBOTS.encode()))
    policy = load_robots(client, "https://www.legislation.gov.uk", "test-agent/1 (contact)", throttle)
    assert client.calls == [
        ("https://www.legislation.gov.uk/robots.txt", {"User-Agent": "test-agent/1 (contact)"})
    ]
    assert policy.crawl_delay == 5.0


def test_a_missing_robots_txt_means_no_restrictions():
    t = FakeTime()
    client = FakeClient(Response(404, {}, b""))
    policy = load_robots(client, "https://example.org", "ua", Throttle(5.0, clock=t.clock, sleep=t.sleep))
    assert policy.can_fetch("https://example.org/anything")
    assert policy.crawl_delay is None
