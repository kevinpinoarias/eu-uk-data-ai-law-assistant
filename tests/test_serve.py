"""
Tests for the web server: a real server on a free local port with the demo pipeline, called over HTTP with the
standard library. No model, key or internet involved.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer

import pytest

from law_assistant.answer.service import AskService, RateLimiter
from law_assistant.serve import DemoPipeline, make_handler


@pytest.fixture()
def server():
    service = AskService(DemoPipeline(), limiter=RateLimiter(per_minute=100, per_day=1000))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(service, trust_proxy=False))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()
    httpd.server_close()


def call(url, data=None, headers=None):
    request = urllib.request.Request(url, data=data, headers=headers or {}, method="POST" if data else "GET")
    try:
        with urllib.request.urlopen(request, timeout=5) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as error:
        return error.code, dict(error.headers), error.read()


def ask(base, payload):
    return call(f"{base}/ask", json.dumps(payload).encode(), {"Content-Type": "application/json"})


def test_health_check(server):
    status, _, body = call(f"{server}/health")
    assert status == 200 and json.loads(body) == {"ok": True}


def test_the_page_is_served_with_security_headers_and_the_disclaimer(server):
    status, headers, body = call(f"{server}/")
    assert status == 200 and headers["Content-Type"].startswith("text/html")
    assert (
        headers["X-Content-Type-Options"] == "nosniff"
        and "default-src 'self'" in headers["Content-Security-Policy"]
    )
    assert b"not legal advice" in body.lower()


def test_a_question_gets_a_json_answer(server):
    status, headers, body = ask(server, {"question": "What is the highest fine?"})
    data = json.loads(body)
    assert status == 200 and headers["Content-Type"] == "application/json"
    assert data["kind"] == "table" and data["sources"][0]["label"].startswith("GDPR")


def test_a_bad_body_is_a_400_and_an_unknown_path_a_404(server):
    assert call(f"{server}/ask", b"not json", {"Content-Type": "application/json"})[0] == 400
    assert ask(server, {"question": ""})[0] == 400
    assert call(f"{server}/nope")[0] == 404
    assert call(f"{server}/nope", b"{}")[0] == 404


def test_an_oversized_body_is_refused_without_reading_it(server):
    big = json.dumps({"question": "x" * 20000}).encode()
    assert call(f"{server}/ask", big, {"Content-Type": "application/json"})[0] == 400
