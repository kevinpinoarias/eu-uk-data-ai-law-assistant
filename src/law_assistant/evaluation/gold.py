"""
The gold question set: what a question is, how the set is stored, and the hash that freezes a version of it.

A question names the provisions that answer it by instrument and unit (article 17 of the GDPR), never by
chunk, so the same gold works whatever chunking is being tested. Rules between fields (a refusal has no gold
provision, a numeric question needs a table key) are in checks.py; here only the fixed lists are enforced.
"""

from __future__ import annotations

import hashlib
import json
from collections import Counter
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from law_assistant.model import JURISDICTIONS, UNITS

LANGUAGES = ("en", "es")
TYPES = (
    "lookup",  # which provision says X
    "definition",  # what a defined term means
    "cross_reference",  # the answer needs two or more provisions
    "comparison",  # EU against UK
    "spanish_law",  # the LOPDGDD
    "as_of",  # the answer depends on the date
    "numeric",  # an exact figure or date: the structured table, not retrieval
    "refuse",  # out of the corpus, or a request for legal advice
)
ROUTES = ("retrieve", "table", "refuse")
ROUTE_OF = {t: "retrieve" for t in TYPES} | {"numeric": "table", "refuse": "refuse"}
PHRASINGS = ("lay", "lawyer")
AUTHORS = ("kevin", "claude")
SPLITS = ("dev", "test")
REASONS = ("out_of_corpus", "legal_advice")
ROLES = ("primary", "acceptable")  # primary: must be found; acceptable: also counts as relevant

# The plan for the 80 questions (docs: the Phase 2 plan, 15 October 2026)
MIX_TARGETS = {
    "lookup": 16,
    "definition": 8,
    "cross_reference": 10,
    "comparison": 10,
    "spanish_law": 8,
    "as_of": 10,
    "numeric": 8,
    "refuse": 10,
}
LANGUAGE_TARGETS = {"en": 40, "es": 40}
REASON_TARGETS = {"out_of_corpus": 6, "legal_advice": 4}


def _one_of(name: str, value: Any, allowed: tuple[str, ...], optional: bool = False) -> None:
    if optional and value is None:
        return
    if value not in allowed:
        raise ValueError(f"unknown {name} {value!r}; expected one of {allowed}")


@dataclass(frozen=True)
class GoldProvision:
    instrument: str  # eu-gdpr, eu-ai-act, uk-gdpr, es-lopdgdd ...
    unit: str  # article | section | annex | schedule | disposition | recital
    unit_path: tuple[str, ...]  # ("17",) is article 17; ("final", "tercera") a disposition
    pinpoints: tuple[str, ...] = ()  # provision ids that carry the answer, e.g. "eu-gdpr/art-6/1/f"
    quotes: tuple[str, ...] = ()  # short passages that must appear in the unit's text
    version: str | None = None  # only this text counts ("oj", "consolidated-20260727"); None means any
    language: str | None = None  # only this language of the text; None means any
    role: str = "primary"

    def __post_init__(self) -> None:
        _one_of("role", self.role, ROLES)
        _one_of("unit", self.unit, UNITS)
        _one_of("language", self.language, LANGUAGES, optional=True)
        if not self.unit_path:
            raise ValueError("unit_path must not be empty")


@dataclass(frozen=True)
class GoldQuestion:
    id: str  # q001 ...
    language: str  # the language the question is asked in
    text: str
    type: str
    route: str  # retrieve | table | refuse
    phrasing: str  # lay (how a non-lawyer asks) | lawyer
    jurisdictions: tuple[str, ...]  # which laws the question is about
    gold: tuple[GoldProvision, ...]
    expected_answer: str  # short, in the question's language
    author: str
    as_of: str | None = None  # ISO date the question is asked as of; None means the corpus snapshot date
    split: str | None = None  # dev | test, set when the set is frozen
    reviewed: str | None = None  # ISO date Kevin reviewed it
    table_key: str | None = None  # the row of the structured table that answers a numeric question
    refusal_reason: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        _one_of("language", self.language, LANGUAGES)
        _one_of("type", self.type, TYPES)
        _one_of("route", self.route, ROUTES)
        _one_of("phrasing", self.phrasing, PHRASINGS)
        _one_of("author", self.author, AUTHORS)
        _one_of("split", self.split, SPLITS, optional=True)
        _one_of("refusal_reason", self.refusal_reason, REASONS, optional=True)
        for jurisdiction in self.jurisdictions:
            _one_of("jurisdictions", jurisdiction, JURISDICTIONS)

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["jurisdictions"] = list(self.jurisdictions)
        data["gold"] = [
            {
                **g,
                "unit_path": list(g["unit_path"]),
                "pinpoints": list(g["pinpoints"]),
                "quotes": list(g["quotes"]),
            }
            for g in data["gold"]
        ]
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GoldQuestion:
        gold = tuple(
            GoldProvision(
                **{
                    **g,
                    "unit_path": tuple(g["unit_path"]),
                    "pinpoints": tuple(g.get("pinpoints", ())),
                    "quotes": tuple(g.get("quotes", ())),
                }
            )
            for g in data["gold"]
        )
        return cls(**{**data, "gold": gold, "jurisdictions": tuple(data["jurisdictions"])})


def _lines(questions: Iterable[GoldQuestion], sort_keys: bool) -> list[str]:
    ordered = sorted(questions, key=lambda q: q.id)
    return [json.dumps(q.to_dict(), ensure_ascii=False, sort_keys=sort_keys) for q in ordered]


def write_gold(path: Path, questions: Iterable[GoldQuestion]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(_lines(questions, sort_keys=False)) + "\n", encoding="utf-8", newline="\n")


def read_gold(path: Path) -> list[GoldQuestion]:
    with path.open(encoding="utf-8") as f:
        return [GoldQuestion.from_dict(json.loads(line)) for line in f if line.strip()]


def freeze_hash(questions: Iterable[GoldQuestion]) -> str:
    """SHA-256 of the set in canonical form (sorted by id and keys): any edit changes it, order does not."""
    canonical = "\n".join(_lines(questions, sort_keys=True))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def mix_counts(questions: Iterable[GoldQuestion]) -> dict[str, dict[str, int]]:
    qs = list(questions)
    return {
        "type": dict(Counter(q.type for q in qs)),
        "language": dict(Counter(q.language for q in qs)),
        "reason": dict(Counter(q.refusal_reason for q in qs if q.refusal_reason)),
    }
