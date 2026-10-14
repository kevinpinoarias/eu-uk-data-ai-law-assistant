"""Shared by the parsers: build Provisions in reading order with unique, citation-shaped ids."""

from __future__ import annotations

from law_assistant.model import Provision

_PREFIX = {"recital": "rct", "article": "art", "annex": "anx"}


class ProvisionBuilder:
    """Collects provisions for one document. Ids are built from the path ("eu-gdpr/art-6/1/f"); closing text
    gets "~closing", and a repeated id gets a counter so ids stay unique."""

    def __init__(
        self,
        instrument: str,
        language: str,
        version: str,
        source_key: str | None,
        jurisdiction: str = "EU",
    ) -> None:
        self.instrument, self.language, self.version = instrument, language, version
        self.source_key, self.jurisdiction = source_key, jurisdiction
        self.provisions: list[Provision] = []
        self._ids: dict[str, int] = {}

    def emit(
        self,
        unit: str,
        kind: str,
        path: tuple[str, ...],
        text: str,
        heading: str | None,
        chapter: str | None,
    ) -> None:
        base = f"{self.instrument}/{_PREFIX[unit]}-" + "/".join(path)
        if kind == "closing":
            base += "~closing"
        count = self._ids.get(base, 0) + 1
        self._ids[base] = count
        self.provisions.append(
            Provision(
                id=base if count == 1 else f"{base}{count}",
                instrument=self.instrument,
                jurisdiction=self.jurisdiction,
                language=self.language,
                version=self.version,
                unit=unit,
                kind=kind,
                path=path,
                text=text,
                order=len(self.provisions),
                heading=heading,
                chapter=chapter,
                source_key=self.source_key,
            )
        )
