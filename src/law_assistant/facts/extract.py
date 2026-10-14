"""
Find the numbers and dates in legal text, so that a fact's figures can be proved to come from the provision
it cites. Digits (with a space, comma or point between thousands) and dates are always read; a number written
as a word counts only when it counts a period or an age ("one month", "catorce años"), because "one of the
following" is not a number.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from typing import Any

_DIGITS = re.compile(r"(?<![\w.,])(\d{1,3}(?:[ ,.  ]\d{3})+|\d+)(?![\w])")

_EN_WORDS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9,
    "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16,
    "seventeen": 17, "eighteen": 18, "nineteen": 19, "twenty": 20,
}  # fmt: skip
_ES_WORDS = {
    "un": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8,
    "nueve": 9, "diez": 10, "once": 11, "doce": 12, "trece": 13, "catorce": 14, "quince": 15,
    "dieciséis": 16, "diecisiete": 17, "dieciocho": 18, "diecinueve": 19, "veinte": 20,
}  # fmt: skip
_EN_UNITS = r"(?:months?|years?|days?|hours?|weeks?)"
_ES_UNITS = r"(?:mes(?:es)?|años?|días?|horas?|semanas?)"
_EN_PERIOD = re.compile(
    rf"\b({'|'.join(_EN_WORDS)})\s+(?:(?:further|additional|more|calendar|working)\s+)*{_EN_UNITS}\b",
    re.IGNORECASE,
)
_ES_PERIOD = re.compile(rf"\b({'|'.join(_ES_WORDS)})\s+{_ES_UNITS}\b", re.IGNORECASE)

_EN_MONTHS = [
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
]  # fmt: skip
_ES_MONTHS = [
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
]  # fmt: skip
_EN_DATE = re.compile(
    rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({'|'.join(_EN_MONTHS)})\s+(\d{{4}})\b", re.IGNORECASE
)
_ES_DATE = re.compile(rf"\b(\d{{1,2}})\s+de\s+({'|'.join(_ES_MONTHS)})\s+de\s+(\d{{4}})\b", re.IGNORECASE)
_ISO = re.compile(r"^\d{4}-\d{2}-\d{2}$")


def numbers_in(text: str) -> set[int]:
    """Whole numbers in the text: digits, and number words that count a period or an age."""
    found = {int(re.sub(r"\D", "", m.group(1))) for m in _DIGITS.finditer(text)}
    found |= {_EN_WORDS[m.group(1).lower()] for m in _EN_PERIOD.finditer(text)}
    found |= {_ES_WORDS[m.group(1).lower()] for m in _ES_PERIOD.finditer(text)}
    return found


def dates_in(text: str) -> set[str]:
    """Dates written "2 August 2026" or "2 de agosto de 2026", as ISO strings."""
    found = set()
    for pattern, months in ((_EN_DATE, _EN_MONTHS), (_ES_DATE, _ES_MONTHS)):
        for m in pattern.finditer(text):
            found.add(f"{m.group(3)}-{months.index(m.group(2).lower()) + 1:02d}-{int(m.group(1)):02d}")
    return found


def value_leaves(value: Any) -> tuple[set[float], set[str]]:
    """The numbers and the ISO dates found anywhere inside a fact's value (text and booleans are ignored)."""
    numbers: set[float] = set()
    dates: set[str] = set()

    def walk(item: Any) -> None:
        if isinstance(item, bool):
            return
        if isinstance(item, (int, float)):
            numbers.add(item)
        elif isinstance(item, str) and _ISO.match(item):
            dates.add(item)
        elif isinstance(item, dict):
            for v in item.values():
                walk(v)
        elif isinstance(item, Iterable) and not isinstance(item, str):
            for v in item:
                walk(v)

    walk(value)
    return numbers, dates
