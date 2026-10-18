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


def start(access_code=None):
    service = AskService(DemoPipeline(), limiter=RateLimiter(per_minute=100, per_day=1000))
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), make_handler(service, access_code=access_code))
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    return httpd, f"http://127.0.0.1:{httpd.server_address[1]}"


@pytest.fixture()
def server():
    httpd, url = start()
    yield url
    httpd.shutdown()
    httpd.server_close()


@pytest.fixture()
def closed_server():
    """A server that only answers questions from someone who holds the access code."""
    httpd, url = start(access_code="let-me-in")
    yield url
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


def ask_with_code(base, code):
    headers = {"Content-Type": "application/json"} | ({"X-Access-Code": code} if code is not None else {})
    return call(f"{base}/ask", json.dumps({"question": "What is the highest fine?"}).encode(), headers)


def test_a_closed_server_answers_only_with_the_right_access_code(closed_server):
    assert ask_with_code(closed_server, None)[0] == 401
    assert ask_with_code(closed_server, "")[0] == 401
    assert ask_with_code(closed_server, "wrong")[0] == 401
    status, _, body = ask_with_code(closed_server, "let-me-in")
    assert status == 200 and json.loads(body)["kind"] == "table"


def test_a_refusal_reads_the_body_first_so_the_client_always_receives_it(closed_server):
    # A server that answers and closes with unread request data can make the operating system reset the
    # connection, so the visitor sees a failed request instead of the 401. Send many near-maximum bodies.
    body = json.dumps({"question": "x" * 9000}).encode()
    for _ in range(40):
        status, _, reply = call(
            f"{closed_server}/ask", body, {"Content-Type": "application/json", "X-Access-Code": "wrong"}
        )
        assert status == 401 and b"access code" in reply.lower()


def test_a_refused_visitor_gets_a_plain_message_and_costs_nothing(closed_server):
    status, _, body = ask_with_code(closed_server, "wrong")
    assert status == 401 and "access code" in json.loads(body)["error"].lower()
    assert "ask the owner" in json.loads(body)["error"].lower()
    assert "wrong" not in json.loads(body)["error"] and "let-me-in" not in body.decode()


def test_the_pages_and_the_health_check_stay_open_on_a_closed_server(closed_server):
    # The notice and the page must be readable by anyone; only asking a question needs the code.
    assert call(f"{closed_server}/health")[0] == 200
    assert call(f"{closed_server}/")[0] == 200
    assert call(f"{closed_server}/privacy")[0] == 200


def test_an_open_server_needs_no_code(server):
    assert ask_with_code(server, None)[0] == 200


def test_the_server_never_reads_or_logs_a_visitors_address(server, capsys):
    import inspect

    from law_assistant import serve

    source = inspect.getsource(serve)
    assert "client_address" not in source and "X-Forwarded-For" not in source and "TRUST_PROXY" not in source
    ask_with_code(server, None)
    call(f"{server}/")
    assert "127.0.0.1" not in capsys.readouterr().err  # the request log has no address either


def test_the_real_pipeline_gets_the_advice_rewriter_only_in_general_mode():
    import inspect

    from law_assistant.answer import factory

    source = inspect.getsource(factory.build_pipeline)
    assert 'advice_rewriter=AdviceRewriter(generator) if advice_mode == "general" else None' in source


def test_the_live_server_answers_advice_questions_in_general_terms_and_can_be_switched_back():
    import inspect

    from law_assistant import serve
    from law_assistant.answer.factory import build_pipeline

    source = inspect.getsource(serve.main)
    assert 'advice_mode="refuse" if "--refuse-advice" in argv else "general"' in source
    # the factory itself keeps the measured behaviour, so experiments that build the pipeline reproduce earlier results
    assert inspect.signature(build_pipeline).parameters["advice_mode"].default == "refuse"
