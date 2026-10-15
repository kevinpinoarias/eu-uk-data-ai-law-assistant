"""
Turn text into the words a keyword search compares: lower-cased runs of letters and digits, so
"Article 6(1)(f)" becomes article, 6, 1, f. No stemming and no stop words (BM25 already gives very common
words almost no weight). Accent folding is optional: "protección" and "proteccion" are different words until
it is switched on.
"""

from __future__ import annotations

import re
import unicodedata

_WORD = re.compile(r"\w+")


def fold(text: str) -> str:
    """Remove accents: "protección" -> "proteccion", "año" -> "ano"."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def tokenize(text: str, *, fold_accents: bool = False) -> list[str]:
    text = text.lower()
    if fold_accents:
        text = fold(text)
    return _WORD.findall(text)
