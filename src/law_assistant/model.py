"""
The common shape every parser produces, whatever the source's markup: one Provision per recital, article,
paragraph, point, closing text or annex item, in reading order. Chunking (step 1.5) builds on this shape only.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

JURISDICTIONS = ("EU", "UK", "ES")
UNITS = ("recital", "article", "section", "annex", "schedule", "disposition")  # what `path[0]` refers to
KINDS = (
    "recital",  # a recital (explanatory, not binding)
    "article",  # an article's own text outside numbered paragraphs: a one-paragraph article, an intro line
    "paragraph",  # a numbered paragraph of an article
    "point",  # a lettered or numbered list item, at any depth
    "closing",  # text that follows a list and belongs to the paragraph or point above it
    "annex",  # an annex's own intro text
)


@dataclass(frozen=True)
class Provision:
    id: str  # unique within a document, built from the path: "eu-gdpr/art-6/1/f"
    instrument: str  # which law: "eu-gdpr", "eu-ai-act", "uk-gdpr", "es-lopdgdd" ...
    jurisdiction: str  # EU | UK | ES
    language: str  # en | es
    version: str  # which text: "oj", "consolidated-20260727", ...
    unit: str  # recital | article | annex
    kind: str  # see KINDS
    path: tuple[str, ...]  # labels from the unit down: ("6", "1", "f") is article 6, paragraph 1, point (f)
    text: str  # plain text of this provision only (children are separate provisions)
    order: int  # position in the document's reading order
    heading: str | None = None  # the article's or annex's title
    chapter: str | None = None  # chapter (and section) the provision sits in
    source_key: str | None = None  # the cache key of the raw file this came from
    in_force_from: str | None = None  # ISO date the wording took effect, where the source states it

    def __post_init__(self) -> None:
        if self.jurisdiction not in JURISDICTIONS:
            raise ValueError(f"unknown jurisdiction {self.jurisdiction!r}")
        if self.unit not in UNITS:
            raise ValueError(f"unknown unit {self.unit!r}")
        if self.kind not in KINDS:
            raise ValueError(f"unknown kind {self.kind!r}")
        if not self.path:
            raise ValueError("path must not be empty")
        if not isinstance(self.text, str):
            raise ValueError("text must be a string")

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["path"] = list(self.path)
        return data

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Provision:
        return cls(**{**data, "path": tuple(data["path"])})
