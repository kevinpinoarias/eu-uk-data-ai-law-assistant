"""
A small client for Google's embedding model (gemini-embedding-2), using only the standard library.

What the model expects (read from Google's documentation on 15 October 2026):
- a passage is sent as "title: {title} | text: {content}" ("title: none" when there is no title); here the
  chunk's context line (law, chapter, article) is the title and the law text is the content;
- a question is sent as "task: search result | query: {content}";
- there is no task-type field for this model; the prefix in the text does that job;
- the key goes in the x-goog-api-key header, never in the URL, the logs or an error message;
- by default each vector has 3,072 numbers; shorter ones can be made by truncating and renormalising.

Rate limits are not published per model, so requests are paced, and a 429 or a server error is retried with
growing pauses.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from collections.abc import Callable, Mapping, Sequence

from law_assistant.chunk.chunker import Chunk

MODEL = "gemini-embedding-2"
BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"
KEY_VARIABLE = "GEMINI_API_KEY"

Transport = Callable[[str, dict[str, str], bytes], tuple[int, bytes]]


class EmbeddingError(RuntimeError):
    pass


def document_prompt(chunk: Chunk, *, with_context: bool = True) -> str:
    title = chunk.context if with_context and chunk.context else "none"
    return f"title: {title} | text: {chunk.text}"


def query_prompt(text: str) -> str:
    return f"task: search result | query: {text}"


def urllib_transport(
    url: str, headers: dict[str, str], body: bytes, timeout: float = 120
) -> tuple[int, bytes]:
    request = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        return error.code, error.read()
    except (urllib.error.URLError, TimeoutError):
        return 599, b""  # a network failure: retried like a server error


def _wait_after(status: int, reply: bytes, attempt: int) -> float:
    """How long to wait before retrying. A rate limit (429) is usually per minute, so wait a good part of a
    minute, or the delay the reply asks for; other errors get short growing pauses."""
    if status != 429:
        return min(60.0, 2.0**attempt)
    try:
        for detail in json.loads(reply).get("error", {}).get("details", []):
            delay = detail.get("retryDelay") if isinstance(detail, dict) else None
            if delay:
                return float(str(delay).rstrip("s")) + 2.0
    except (ValueError, AttributeError):
        pass
    return min(120.0, 15.0 * 2.0**attempt)


class GeminiEmbedder:
    def __init__(
        self,
        api_key: str,
        *,
        model: str = MODEL,
        transport: Transport = urllib_transport,
        batch_size: int = 32,
        max_retries: int = 5,
        pause: float = 0.5,
        sleep: Callable[[float], None] = time.sleep,
    ) -> None:
        self.name = model
        self._key = api_key
        self._transport, self._sleep = transport, sleep
        self.batch_size, self.max_retries, self.pause = batch_size, max_retries, pause

    def __repr__(self) -> str:
        return f"GeminiEmbedder(model={self.name!r})"

    @classmethod
    def from_env(cls, env: Mapping[str, str] | None = None, **kwargs) -> GeminiEmbedder:
        key = (os.environ if env is None else env).get(KEY_VARIABLE, "")
        if not key:
            raise EmbeddingError(f"{KEY_VARIABLE} is not set (put it in .env; see .env.example)")
        return cls(key, **kwargs)

    def _post(self, method: str, payload: dict) -> dict:
        url = f"{BASE_URL}/{self.name}:{method}"
        headers = {"Content-Type": "application/json", "x-goog-api-key": self._key}
        body = json.dumps(payload).encode("utf-8")
        for attempt in range(self.max_retries + 1):
            status, reply = self._transport(url, headers, body)
            if status == 200:
                return json.loads(reply)
            retryable = status == 429 or status >= 500
            if not retryable or attempt == self.max_retries:
                raise EmbeddingError(
                    f"HTTP {status} from {method}: {reply[:1500].decode('utf-8', 'replace')}"
                )
            self._sleep(_wait_after(status, reply, attempt))
        raise EmbeddingError("unreachable")

    def embed_texts(self, texts: Sequence[str]) -> list[list[float]]:
        """One vector per text, in order, sent in batches."""
        out: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            payload = {
                "requests": [
                    {"model": f"models/{self.name}", "content": {"parts": [{"text": t}]}} for t in batch
                ]
            }
            reply = self._post("batchEmbedContents", payload)
            vectors = [e["values"] for e in reply.get("embeddings", [])]
            if len(vectors) != len(batch):
                raise EmbeddingError(f"expected {len(batch)} vectors, got {len(vectors)}")
            out.extend(vectors)
            if start + self.batch_size < len(texts):
                self._sleep(self.pause)
        return out

    def embed_one(self, text: str, dimensions: int | None = None) -> list[float]:
        payload: dict = {"model": f"models/{self.name}", "content": {"parts": [{"text": text}]}}
        if dimensions is not None:
            payload["output_dimensionality"] = dimensions
        return self._post("embedContent", payload)["embedding"]["values"]
