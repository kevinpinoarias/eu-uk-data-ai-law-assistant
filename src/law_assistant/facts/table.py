"""
The structured table: one `Fact` per exact figure the assistant may state (a fine ceiling, a deadline, an age,
an application date), with its value in typed form, a one-line answer in each language, and the provisions it
comes from. The assistant looks these up by key instead of reading the figures out of prose.
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from law_assistant.model import JURISDICTIONS, UNITS

KINDS = ("fine_ceiling", "deadline", "age", "application_date")
LANGUAGES = ("en", "es")


@dataclass(frozen=True)
class FactSource:
    instrument: str
    unit: str
    unit_path: tuple[str, ...]
    pinpoints: tuple[str, ...] = ()
    quotes: tuple[str, ...] = ()  # passages that must appear in the unit's text
    version: str | None = None  # the wording the figure comes from; None means any version

    def __post_init__(self) -> None:
        if self.unit not in UNITS:
            raise ValueError(f"unknown unit {self.unit!r}")
        if not self.unit_path:
            raise ValueError("unit_path must not be empty")


@dataclass(frozen=True)
class Fact:
    key: str
    kind: str
    jurisdictions: tuple[str, ...]
    subject_en: str
    subject_es: str
    value: dict[str, Any]  # typed: {"amount": 20000000, "currency": "EUR", "turnover_percent": 4}
    summary_en: str  # a one-line answer with its citation
    summary_es: str
    sources: tuple[FactSource, ...]
    caveat_en: str = ""  # what the figure does not say (a ceiling, a default, a derived date)
    caveat_es: str = ""

    def __post_init__(self) -> None:
        if self.kind not in KINDS:
            raise ValueError(f"unknown kind {self.kind!r}; expected one of {KINDS}")
        for jurisdiction in self.jurisdictions:
            if jurisdiction not in JURISDICTIONS:
                raise ValueError(f"unknown jurisdictions entry {jurisdiction!r}")
        if not self.sources:
            raise ValueError("a fact needs at least one source")
        if not self.value:
            raise ValueError("a fact needs a value")

    def summary(self, language: str) -> str:
        if language not in LANGUAGES:
            raise ValueError(f"unknown language {language!r}")
        return self.summary_en if language == "en" else self.summary_es

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["jurisdictions"] = list(self.jurisdictions)
        data["sources"] = [
            {
                **s,
                "unit_path": list(s["unit_path"]),
                "pinpoints": list(s["pinpoints"]),
                "quotes": list(s["quotes"]),
            }
            for s in data["sources"]
        ]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Fact:
        sources = tuple(
            FactSource(
                **{
                    **s,
                    "unit_path": tuple(s["unit_path"]),
                    "pinpoints": tuple(s.get("pinpoints", ())),
                    "quotes": tuple(s.get("quotes", ())),
                }
            )
            for s in data["sources"]
        )
        return cls(**{**data, "sources": sources, "jurisdictions": tuple(data["jurisdictions"])})


def write_facts(path: Path, facts: Iterable[Fact]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = (json.dumps(f.to_dict(), ensure_ascii=False) for f in sorted(facts, key=lambda f: f.key))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")


def read_facts(path: Path) -> list[Fact]:
    with path.open(encoding="utf-8") as f:
        return [Fact.from_dict(json.loads(line)) for line in f if line.strip()]


def lookup(facts: Iterable[Fact], key: str) -> Fact:
    for fact in facts:
        if fact.key == key:
            return fact
    raise KeyError(key)
