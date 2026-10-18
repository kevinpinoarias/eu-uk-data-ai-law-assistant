"""
A small web server for the demo page, using only the standard library: `python -m law_assistant.serve`.

- GET /          the one-page interface (web/index.html)
- GET /privacy   the privacy notice (web/privacy.html, English and Spanish)
- GET /health    {"ok": true}, for a hosting platform's health check
- POST /ask      {"question": "..."} -> the answer JSON (see answer/service.py)

`--demo` serves canned answers without loading any model or key, to check the page. `--port N` and `--host H`
change the address (default 127.0.0.1:8000).

What this server knows about a visitor: nothing. It never reads the connecting address (the limits count
questions in total) and its request log has none; each question leaves a trace row with its route, timings and
outcome but not its text (data/traces/traces.jsonl, deleted after TRACE_RETENTION_DAYS days, default 30).

Asking a question can be restricted to people who hold an access code: set ACCESS_CODE, and the page sends it
(from the link's fragment, which a browser never sends to a server) in the X-Access-Code header. The pages and
the health check stay open. With no ACCESS_CODE the server answers anyone, which is right for a local run.
The total limits are QUESTIONS_PER_MINUTE (default 10) and QUESTIONS_PER_DAY (default 300).

A question about the user's own situation is answered in general terms from the texts, with a notice to see a
professional (decision 124); `--refuse-advice` restores the earlier behaviour of refusing it.
"""

from __future__ import annotations

import hmac
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from law_assistant import settings
from law_assistant.answer.pipeline import Result, Source
from law_assistant.answer.service import AskService, RateLimiter
from law_assistant.answer.trace import DEFAULT_RETENTION_DAYS, TraceLog

PAGE = settings.PROJECT_ROOT / "web" / "index.html"
PRIVACY_PAGE = settings.PROJECT_ROOT / "web" / "privacy.html"
# Details only the owner can supply; the notice must not go public while any of them is still a placeholder.
PRIVACY_PLACEHOLDERS = ("[OWNER NAME]", "[CITY, COUNTRY]", "[CONTACT EMAIL]", "[HOSTING PROVIDER]")
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


def launch_blockers(notice: str | None = None) -> list[str]:
    """Placeholders still present in the privacy notice (empty when it is ready to publish)."""
    text = PRIVACY_PAGE.read_text(encoding="utf-8") if notice is None else notice
    return [name for name in PRIVACY_PLACEHOLDERS if name in text]


def make_handler(service: AskService, access_code: str | None = None):
    def allowed(supplied: str | None) -> bool:
        if not access_code:
            return True
        return supplied is not None and hmac.compare_digest(supplied.encode(), access_code.encode())

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
            elif self.path == "/privacy":
                self._send(200, PRIVACY_PAGE.read_bytes(), "text/html; charset=utf-8")
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
            raw = self.rfile.read(
                length
            )  # read before any refusal: replying with unread data can reset the connection
            if not allowed(self.headers.get("X-Access-Code")):
                self._json(
                    401,
                    {
                        "error": "An access code is needed to ask questions. "
                        "Use the link you were given or ask the owner for one."
                    },
                )
                return
            try:
                payload = json.loads(raw)
            except ValueError:
                self._json(400, {"error": "The body is not valid JSON."})
                return
            status, body = service.ask(payload)
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

        pipeline, _ = build_pipeline(
            version_aware="--version-aware" in argv,
            include_dates="--with-dates" in argv,
            advice_mode="refuse" if "--refuse-advice" in argv else "general",
        )
    retention = int(os.environ.get("TRACE_RETENTION_DAYS", str(DEFAULT_RETENTION_DAYS)))
    trace = TraceLog(
        Path(settings.PROJECT_ROOT / "data" / "traces" / "traces.jsonl"), retention_days=retention
    )
    removed = trace.prune(days=retention)
    if removed:
        print(f"deleted {removed} traces older than the retention period")
    if blockers := launch_blockers():
        print(
            "WARNING: the privacy notice (web/privacy.html) still has placeholders to fill in before a "
            f"public launch: {', '.join(blockers)}",
            file=sys.stderr,
        )
    limiter = RateLimiter(
        per_minute=int(os.environ.get("QUESTIONS_PER_MINUTE", "10")),
        per_day=int(os.environ.get("QUESTIONS_PER_DAY", "300")),
    )
    service = AskService(pipeline, trace=trace, limiter=limiter)
    access_code = os.environ.get("ACCESS_CODE") or None
    if access_code is None:
        print(
            "NOTE: ACCESS_CODE is not set, so anyone who finds this server can ask questions.",
            file=sys.stderr,
        )
    handler = make_handler(service, access_code=access_code)
    with ThreadingHTTPServer((host, port), handler) as server:
        print(f"serving on http://{host}:{port}  (demo mode: {'--demo' in argv})")
        server.serve_forever()
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
