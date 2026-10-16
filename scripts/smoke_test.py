"""
Smoke test of the web service in demo mode: start the real server as a separate process, wait for `/health`, and
check the page, the answer endpoint and the error responses over HTTP. It needs no model, no key and no
network, and works on a minimal install (`pip install -e .`), so it also proves that the demo does not drag in
PyTorch. Used by CI and runnable by hand: `python scripts/smoke_test.py`.
"""

from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

ROOT_PYTHON = sys.executable


def free_port() -> int:
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def call(url: str, payload=None, raw: bytes | None = None):
    data = raw if raw is not None else (json.dumps(payload).encode() if payload is not None else None)
    request = urllib.request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"} if data else {},
        method="POST" if data else "GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as r:
            return r.status, r.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()


def run(port: int | None = None, startup_seconds: float = 40.0) -> list[str]:
    """Return the list of failed checks (empty means the smoke test passed)."""
    port = port or free_port()
    base = f"http://127.0.0.1:{port}"
    server = subprocess.Popen(
        [ROOT_PYTHON, "-m", "law_assistant.serve", "--demo", "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )  # fmt: skip
    failures: list[str] = []

    def check(name: str, ok: bool) -> None:
        if not ok:
            failures.append(name)

    try:
        deadline = time.time() + startup_seconds
        healthy = False
        while time.time() < deadline and server.poll() is None:
            try:
                healthy = call(f"{base}/health")[0] == 200
            except OSError:
                healthy = False
            if healthy:
                break
            time.sleep(0.3)
        check("the server starts and /health answers", healthy)
        if not healthy:
            return failures
        status, page = call(f"{base}/")
        check("the page is served", status == 200 and b"<html" in page)
        check(
            "the page carries the disclaimer in both languages",
            b"Not legal advice" in page and b"No es asesoramiento" in page,
        )
        status, privacy = call(f"{base}/privacy")
        check(
            "the privacy notice is served in both languages",
            status == 200 and b"Privacy notice" in privacy and b"Aviso de privacidad" in privacy,
        )
        check("the page links to the privacy notice", b'href="/privacy"' in page)
        status, body = call(f"{base}/ask", {"question": "What is the highest fine?"})
        answer = json.loads(body) if status == 200 else {}
        check(
            "a question gets a JSON answer with sources",
            status == 200 and answer.get("sources") and answer.get("answer"),
        )
        check("an empty question is a 400", call(f"{base}/ask", {"question": ""})[0] == 400)
        check("a body that is not JSON is a 400", call(f"{base}/ask", raw=b"not json")[0] == 400)
        check("an unknown path is a 404", call(f"{base}/nope")[0] == 404)
    finally:
        server.terminate()
        try:
            server.wait(timeout=10)
        except subprocess.TimeoutExpired:
            server.kill()
    return failures


if __name__ == "__main__":
    problems = run()
    for problem in problems:
        print("FAILED:", problem)
    print("smoke test:", "passed" if not problems else f"{len(problems)} check(s) failed")
    raise SystemExit(1 if problems else 0)
