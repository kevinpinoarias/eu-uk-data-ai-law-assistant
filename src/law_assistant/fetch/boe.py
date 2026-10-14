"""
Fetch the Spanish data-protection law (LOPDGDD, Ley Orgánica 3/2018) from the BOE open-data API into
data/raw/boe_es/.

    python -m law_assistant.fetch.boe            # fetch what is not cached yet
    python -m law_assistant.fetch.boe --force    # fetch again

Three records of the same law: the consolidated text with its versions (XML), its metadata (JSON) and
its European Legislation Identifier record (XML). The BOE's reuse conditions (SOURCES.md): cite the BOE
with its set wording, do not distort the meaning, mark consolidated texts as informative only, show the
last update date. The API needs no key and states no rate limit; we still send our identifying
User-Agent and wait between requests.
"""

from __future__ import annotations

from collections.abc import Sequence

from law_assistant.fetch.documents import SourceDocument
from law_assistant.fetch.runner import run_command

BASE_URL = "https://www.boe.es"
API = f"{BASE_URL}/datosabiertos/api/legislacion-consolidada/id/BOE-A-2018-16673"
SOURCE = "boe_es"
LICENCE = "BOE reuse conditions (Resolución de 27 de junio de 2024)"
CREDIT = (
    "Copias: «Fuente de los datos: Agencia Estatal Boletín Oficial del Estado». "
    "Obras derivadas: «Basado en datos de la Agencia Estatal Boletín Oficial del Estado». "
    "Texto consolidado, de carácter meramente informativo."
)


def _doc(key: str, title: str, endpoint: str, suffix: str, accept: str) -> SourceDocument:
    return SourceDocument(
        key=key,
        title=title,
        source=SOURCE,
        url=f"{API}/{endpoint}",
        suffix=suffix,
        licence=LICENCE,
        credit=CREDIT,
        accept=accept,
    )


BOE_DOCUMENTS = (
    _doc("es-lopdgdd-texto", "LOPDGDD, consolidated text with versions", "texto", ".xml", "application/xml"),
    _doc("es-lopdgdd-metadatos", "LOPDGDD, metadata", "metadatos", ".json", "application/json"),
    _doc("es-lopdgdd-eli", "LOPDGDD, ELI metadata", "metadata-eli", ".xml", "application/xml"),
)


def main(argv: Sequence[str] | None = None) -> int:
    return run_command(BOE_DOCUMENTS, BASE_URL, "Fetch the LOPDGDD from the BOE open-data API.", argv)


if __name__ == "__main__":
    raise SystemExit(main())
