"""
Step 1 of the answer layer: read a question before doing anything with it. Which language is it in, which
jurisdictions does it name, and does it ask about a particular date? Plain rules, no model, so the step is
free, instant and explainable; its accuracy against the gold labels is measured in
experiments/p4_understand.py.

The rules are deliberately small. A question that names no place or law gets no jurisdiction (the search then
uses everything), and a date is only read when it is written out or phrased as "the start of 2026".
"""

# ruff: noqa: SIM905  (word lists written as one string are easier to read and to extend than list literals)

from __future__ import annotations

import re
from dataclasses import dataclass

_SPANISH = frozenset(
    "el la los las del que qué en y un una por para con se mi mis su sus es al lo como cómo cuando cuándo "
    "quien quién quienes puedo puede pueden debe deben tiene tienen cual cuál cuáles hay está esta si sobre "
    "datos derecho derechos desde hasta entre ante tras mismo misma qué cuánto cuánta cuántos".split()
)
_ENGLISH = frozenset(
    "the of to in and is are do does can i my what how when who under if it for on with by from or that this "
    "which be as at have has there any an was were should would about between since".split()
)
_SPANISH_MARKS = re.compile(r"[¿¡ñ]")
_ACCENTS = re.compile(r"[áéíóú]")
_WORD = re.compile(r"\w+", re.UNICODE)


def detect_language(text: str) -> str:
    """'es' when Spanish markers outweigh English ones, otherwise 'en' (also the default for no evidence)."""
    words = [w.lower() for w in _WORD.findall(text)]
    spanish = sum(w in _SPANISH for w in words) + 3 * bool(_SPANISH_MARKS.search(text))
    spanish += bool(_ACCENTS.search(text.lower()))
    english = sum(w in _ENGLISH for w in words)
    return "es" if spanish > english else "en"


# Short acronyms are matched in capitals only ("UE" is the Spanish for EU; "ue" is not a word we want).
_UK_CASE = re.compile(r"\b(UK|ICO|DPA)\b")
_UK_ANY = re.compile(
    r"united kingdom|reino unido|great britain|britain|british|england|inglaterra|data protection act 2018|"
    r"data \(use and access\)|\bDUAA\b",
    re.IGNORECASE,
)
_UK_GDPR = re.compile(r"\bUK[ -]GDPR\b", re.IGNORECASE)
_ES_ANY = re.compile(
    r"\bspain\b|\bespaña\b|\bspanish\b|\bespañol(?:a|es|as)?\b|\blopdgdd\b|\blopd\b|\baepd\b", re.IGNORECASE
)
_EU_CASE = re.compile(r"\b(EU|UE|EDPB|CEPD)\b")
_EU_ANY = re.compile(
    r"european|\beurope\b|\beuropa\b|\bgdpr\b|\brgpd\b|\bai act\b|reglamento de ia|reglamento \(ue\)|"
    r"official journal|diario oficial",
    re.IGNORECASE,
)


def detect_jurisdictions(text: str) -> tuple[str, ...]:
    """Jurisdictions named by the question, in the order EU, UK, ES. 'UK GDPR' names the UK only."""
    without_uk_gdpr = _UK_GDPR.sub(" ", text)
    found = []
    if _EU_CASE.search(without_uk_gdpr) or _EU_ANY.search(without_uk_gdpr):
        found.append("EU")
    if _UK_GDPR.search(text) or _UK_CASE.search(text) or _UK_ANY.search(text):
        found.append("UK")
    if _ES_ANY.search(text):
        found.append("ES")
    return tuple(found)


_MONTHS = {
    **{
        m: i
        for i, m in enumerate(
            "january february march april may june july august september october november december".split(), 1
        )
    },
    **{
        m: i
        for i, m in enumerate(
            "enero febrero marzo abril mayo junio julio agosto septiembre octubre noviembre "
            "diciembre".split(),
            1,
        )
    },
}
_MONTH_NAMES = "|".join(sorted(_MONTHS, key=len, reverse=True))
_ISO = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})\b")
_DAY_MONTH_YEAR = re.compile(
    rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+(?:de\s+)?({_MONTH_NAMES})\s+(?:de\s+)?(\d{{4}})\b", re.IGNORECASE
)
_MONTH_DAY_YEAR = re.compile(
    rf"\b({_MONTH_NAMES})\s+(\d{{1,2}})(?:st|nd|rd|th)?,?\s+(\d{{4}})\b", re.IGNORECASE
)
_START_OF_YEAR = re.compile(
    r"(?:start|beginning) of (\d{4})|(?:principios|comienzos|inicios) de (\d{4})|\bearly (\d{4})\b",
    re.IGNORECASE,
)


def _iso(year: int, month: int, day: int) -> str | None:
    if 1 <= month <= 12 and 1 <= day <= 31:
        return f"{year:04d}-{month:02d}-{day:02d}"
    return None


def detect_as_of(text: str) -> str | None:
    """The date the question asks about as an ISO date, or None. 'The start of 2026' is 1 January 2026."""
    if m := _ISO.search(text):
        return _iso(int(m.group(1)), int(m.group(2)), int(m.group(3)))
    if m := _DAY_MONTH_YEAR.search(text):
        return _iso(int(m.group(3)), _MONTHS[m.group(2).lower()], int(m.group(1)))
    if m := _MONTH_DAY_YEAR.search(text):
        return _iso(int(m.group(3)), _MONTHS[m.group(1).lower()], int(m.group(2)))
    if m := _START_OF_YEAR.search(text):
        year = next(g for g in m.groups() if g)
        return f"{int(year):04d}-01-01"
    return None


_ORIGINAL = re.compile(
    r"as (?:first |originally )?published|originally published|original (?:text|wording|version)|"
    r"official journal|texto original|publicado (?:inicialmente|originalmente)|diario oficial|"
    r"redactado inicialmente|redacción original|versión original",
    re.IGNORECASE,
)


def wants_original_text(text: str) -> bool:
    """True when the question asks about the wording as first published (so the original text is needed,
    not only the current consolidated text)."""
    return bool(_ORIGINAL.search(text))


@dataclass(frozen=True)
class Understanding:
    language: str
    jurisdictions: tuple[str, ...]
    as_of: str | None
    wants_original: bool = False


def understand(text: str) -> Understanding:
    return Understanding(
        detect_language(text), detect_jurisdictions(text), detect_as_of(text), wants_original_text(text)
    )
