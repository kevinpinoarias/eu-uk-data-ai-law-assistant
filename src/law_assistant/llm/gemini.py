"""
A small client for Google's Gemini text models (generateContent), using only the standard library, and a disk
cache that makes repeated calls free and experiments repeatable.

- the key goes in the x-goog-api-key header, never in the URL, the logs, an error message or a repr;
- a rate limit (429) or a server error is retried with growing pauses, the same way as the embedding client;
- every call records its time and token counts, so latency and cost can be reported;
- `CachedGenerator` stores each answer in a JSON Lines file keyed by the model, the system text, the prompt
  and the settings; a change to any of them is a different entry. Run the same experiment twice and the second
  run makes no calls.
"""

from __future__ import annotations

import hashlib
import json
import os
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from law_assistant.retrieval.gemini import (
    BASE_URL,
    KEY_VARIABLE,
    Transport,
    _wait_after,
    quota_message,
    urllib_transport,
)

DEFAULT_MODEL = "gemini-3.1-flash-lite"


class LLMError(RuntimeError):
    pass


@dataclass(frozen=True)
class Call:
    seconds: float
    prompt_tokens: int
    output_tokens: int


class GeminiGenerator:
    def __init__(
        self,
        api_key: str,
        *,
        model: str = DEFAULT_MODEL,
        transport: Transport = urllib_transport,
        max_retries: int = 5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.model = model
        self._key, self._transport, self._sleep, self.max_retries = api_key, transport, sleep, max_retries
        self.calls: list[Call] = []

    def __repr__(self) -> str:
        return f"GeminiGenerator(model={self.model!r})"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None, **kwargs) -> GeminiGenerator:
        key = (os.environ if env is None else env).get(KEY_VARIABLE, "")
        if not key:
            raise LLMError(f"{KEY_VARIABLE} is not set (put it in .env; see .env.example)")
        return cls(key, **kwargs)

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
        json_output: bool = False,
    ) -> str:
        payload: dict = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": temperature, "maxOutputTokens": max_output_tokens},
        }
        if json_output:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        if system:
            payload["systemInstruction"] = {"parts": [{"text": system}]}
        url = f"{BASE_URL}/{self.model}:generateContent"
        headers = {"Content-Type": "application/json", "x-goog-api-key": self._key}
        body = json.dumps(payload).encode("utf-8")
        for attempt in range(self.max_retries + 1):
            started = time.perf_counter()
            status, reply = self._transport(url, headers, body)
            if status == 200:
                return self._read(json.loads(reply), time.perf_counter() - started)
            retryable = status == 429 or status >= 500
            if not retryable or attempt == self.max_retries:
                raise LLMError(
                    f"HTTP {status} from generateContent: {reply[:1500].decode('utf-8', 'replace')}"
                )
            wait = _wait_after(status, reply, attempt)
            quota = quota_message(status, reply, wait)
            if quota:
                raise LLMError(
                    f"HTTP {status} from generateContent: {quota}: {reply[:600].decode('utf-8', 'replace')}"
                )
            self._sleep(wait)
        raise LLMError("unreachable")

    def _read(self, data: dict, seconds: float) -> str:
        candidates = data.get("candidates") or []
        parts = (candidates[0].get("content") or {}).get("parts") or [] if candidates else []
        text = "".join(p.get("text", "") for p in parts)
        if not text:
            reason = candidates[0].get("finishReason", "no candidates") if candidates else "no candidates"
            raise LLMError(f"the model returned no text (finish reason: {reason})")
        usage = data.get("usageMetadata") or {}
        self.calls.append(
            Call(seconds, int(usage.get("promptTokenCount", 0)), int(usage.get("candidatesTokenCount", 0)))
        )
        return text


class CachedGenerator:
    """Wraps a generator; answers repeated requests from a JSON Lines file."""

    def __init__(self, inner: GeminiGenerator, path: Path) -> None:
        self._inner, self._path = inner, path
        self.model = inner.model
        self._store: dict[str, str] = {}
        if path.is_file():
            for line in path.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    row = json.loads(line)
                    self._store[row["key"]] = row["text"]

    def _key(
        self, prompt: str, system: str | None, temperature: float, max_output_tokens: int, json_output: bool
    ) -> str:
        parts = [self.model, system, prompt, temperature, max_output_tokens]
        if json_output:
            parts.append("json")  # added only when on, so earlier cache entries stay valid
        raw = json.dumps(parts, ensure_ascii=False)
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def generate(
        self,
        prompt: str,
        *,
        system: str | None = None,
        temperature: float = 0.0,
        max_output_tokens: int = 1024,
        json_output: bool = False,
    ) -> str:
        key = self._key(prompt, system, temperature, max_output_tokens, json_output)
        if key not in self._store:
            text = self._inner.generate(
                prompt,
                system=system,
                temperature=temperature,
                max_output_tokens=max_output_tokens,
                json_output=json_output,
            )
            self._store[key] = text
            self._path.parent.mkdir(parents=True, exist_ok=True)
            with self._path.open("a", encoding="utf-8") as f:
                f.write(
                    json.dumps({"key": key, "model": self.model, "text": text}, ensure_ascii=False) + "\n"
                )
        return self._store[key]

    @property
    def calls(self) -> list[Call]:
        return self._inner.calls
