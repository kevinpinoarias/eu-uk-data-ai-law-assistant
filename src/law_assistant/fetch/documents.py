"""What a source document is: where it comes from, where it is cached, and its licence and credit."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class SourceDocument:
    key: str  # short, stable id, used as the cached file name
    title: str
    source: str  # folder under data/raw/
    url: str
    suffix: str  # file extension of the cached document, e.g. ".xml"
    licence: str
    credit: str  # the credit line SOURCES.md requires wherever the text is shown
