"""
A small web server for the demo page, using only the standard library: `python -m law_assistant.serve`.

- GET /          the one-page interface (web/index.html)
- GET /health    {"ok": true}, for a hosting platform's health check
- POST /ask      {"question": "..."} -> the answer JSON (see answer/service.py)

`--demo` serves canned answers without loading any model or key, to check the page. `--port N` and `--host H`
change the address (default 127.0.0.1:8000). Behind a proxy, set TRUST_PROXY=1 so the client address is read
from X-Forwarded-For for the rate limit. Questions are logged (without addresses) to data/traces/traces.jsonl.
"""

from __future__ import annotations

import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from law_assistant import settings
from law_assistant.answer.pipeline import Result, Source
from law_assistant.answer.service import AskService, RateLimiter
from law_assistant.answer.trace import TraceLog

PAGE = settings.PROJECT_ROOT / "web" / "index.html"
MAX_BODY = 10_000
HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Content-Security-Policy": (
        "default-src 'self'; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'"
    ),
    "Referrer-Policy": "no-referrer",
}


class DemoPipeline:
    """Canned answers for checking the page without a model or key."""

    def ask(self, question: str) -> Result:
        spanish = any(ch in question for ch in "¿¡ñáéíóú")
        if "fine" in question.lower() or "multa" in question.lower():
            text = "Up to EUR 20,000,000 or 4 % of worldwide annual turnover, whichever is higher (demo)."
            kind, route = "table", "table"
        elif "california" in question.lower():
            text = "I can only answer from the texts of EU, Spanish and UK data-protection and AI law (demo)."
            kind, route = "refused", "refuse"
        else:
            text = "Esto es una respuesta de demostración." if spanish else "This is a demo answer."
            kind, route = "answer", "retrieve"
        sources = [Source("GDPR, Article 83 (demo)", None, "up to 20 000 000 EUR")]
        return Result(kind, text, "es" if spanish else "en", route, sources=sources, timings={"demo": 0.01})


def make_handler(service: AskService, trust_proxy: bool):
    class Handler(BaseHTTPRequestHandler):
        def _send(self, status: int, body: bytes, content_type: str) -> None:
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            for name, value in HEADERS.items():
                self.send_header(name, value)
            self.end_headers()
            self.wfile.write(body)

        def _json(self, status: int, data: dict) -> None:
            self._send(status, json.dumps(data, ensure_ascii=False).encode("utf-8"), "application/json")

        def do_GET(self) -> None:  # noqa: N802 (the method name is fixed by BaseHTTPRequestHandler)
            if self.path == "/health":
                self._json(200, {"ok": True})
            elif self.path in ("/", "/index.html"):
                self._send(200, PAGE.read_bytes(), "text/html; charset=utf-8")
            else:
                self._json(404, {"error": "Not found."})

        def do_POST(self) -> None:  # noqa: N802
            if self.path != "/ask":
                self._json(404, {"error": "Not found."})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                length = -1
            if not 0 < length <= MAX_BODY:
                self._json(400, {"error": "Send a JSON body of up to 10 kilobytes."})
                return
            try:
                payload = json.loads(self.rfile.read(length))
            except ValueError:
                self._json(400, {"error": "The body is not valid JSON."})
                return
            client = self.client_address[0]
            if trust_proxy:
                client = self.headers.get("X-Forwarded-For", client).split(",")[0].strip()
            status, body = service.ask(payload, client=client)
            self._json(status, body)

        def log_message(self, format: str, *args) -> None:  # noqa: A002 (name fixed by the base class)
            sys.stderr.write(f"{self.log_date_time_string()} - {format % args}\n")

    return Handler


def main(argv: list[str]) -> int:
    def option(name: str, default: str) -> str:
        return argv[argv.index(name) + 1] if name in argv else default

    host, port = option("--host", "127.0.0.1"), int(option("--port", "8000"))
    if "--demo" in argv:
        pipeline = DemoPipeline()
    else:
        from law_assistant.answer.factory import build_pipeline

        pipeline, _ = build_pipeline(version_aware="--version-aware" in argv)
    trace = TraceLog(Path(settings.PROJECT_ROOT / "data" / "traces" / "traces.jsonl"))
    service = AskService(pipeline, trace=trace, limiter=RateLimiter())
    handler = make_handler(service, trust_proxy=os.environ.get("TRUST_PROXY") == "1")
    with ThreadingHTTPServer((host, port), handler) as server:
        print(f"serving on http://{host}:{port}  (demo mode: {'--demo' in argv})")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
