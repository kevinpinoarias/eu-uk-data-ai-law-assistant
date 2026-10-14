"""Project-wide settings: where files live, and the identifying User-Agent every fetcher must send."""

from __future__ import annotations

import os
from pathlib import Path

from law_assistant import __version__

PROJECT_NAME = "eu-uk-data-ai-law-assistant"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = PROJECT_ROOT / "data" / "raw"  # fetched source documents; git-ignored (see SOURCES.md)
PARSED_DIR = PROJECT_ROOT / "data" / "parsed"  # parsed provisions (JSON Lines); git-ignored
CONTACT_ENV_VAR = "FETCHER_CONTACT"


def load_env_file(path: Path | None = None) -> None:
    """Read KEY=VALUE lines from .env into the environment, never overriding a variable that is already set.

    Comments, blank lines and empty values are skipped and surrounding quotes are removed.
    A missing file is fine.
    """
    env_path = path or PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, _, value = line.partition("=")
        name, value = name.strip(), value.strip().strip("\"'")
        if name and value:
            os.environ.setdefault(name, value)


def user_agent(contact: str | None = None) -> str:
    """The User-Agent header for fetchers: project, version and a way to reach us.

    legislation.gov.uk does not accept anonymous agents and strongly recommends contact details, so a
    missing contact is an error, not a silent fallback. `contact` wins over the FETCHER_CONTACT variable.
    """
    value = (contact if contact is not None else os.environ.get(CONTACT_ENV_VAR, "")).strip()
    if not value:
        raise ValueError(
            f"Set {CONTACT_ENV_VAR} to an email address or URL: fetchers must identify themselves."
        )
    if any(ord(ch) < 32 or ord(ch) == 127 for ch in value):
        raise ValueError("The contact must not contain control characters.")
    return f"{PROJECT_NAME}/{__version__} (research project; contact: {value})"
