"""
Checks that keep the gold set honest, as the parsers' and the chunker's checks keep their output honest:
the rules between a question's fields, the mix against the plan, the overlap warning that guards against a
question copying its answer's wording (which would reward keyword matching), and a check of every gold
provision against the parsed corpus: the unit exists, the pinpoint ids exist, the quotes are in the text.
"""

from __future__ import annotations

import math
import re
from collections import Counter
from collections.abc import Iterable, Sequence
from datetime import date
from pathlib import Path

from law_assistant import settings
from law_assistant.chunk.chunker import unit_key
from law_assistant.evaluation.gold import (
    LANGUAGE_TARGETS,
    MIX_TARGETS,
    REASON_TARGETS,
    ROUTE_OF,
    GoldProvision,
    GoldQuestion,
)
from law_assistant.model import Provision
from law_assistant.parse.store import read_jsonl

_ID = re.compile(r"^q\d{3}$")
_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_WORDS = re.compile(r"\w+")


def _norm(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _valid_date(value: str) -> bool:
    if not _ISO_DATE.match(value):
        return False
    try:
        date.fromisoformat(value)
    except ValueError:
        return False
    return True


def _question_problems(q: GoldQuestion) -> list[str]:
    found: list[str] = []
    if not _ID.match(q.id):
        found.append("id must look like q001")
    if not q.text.strip():
        found.append("text is blank")
    if not q.expected_answer.strip():
        found.append("expected_answer is blank")
    if ROUTE_OF[q.type] != q.route:
        found.append(f"route {q.route} does not follow from type {q.type} (expected {ROUTE_OF[q.type]})")
    primaries = [g for g in q.gold if g.role == "primary"]
    if q.route == "retrieve":
        if not primaries:
            found.append("a retrieval question needs at least one primary gold provision")
        if not q.jurisdictions:
            found.append("a retrieval question needs its jurisdictions")
    if q.route == "table" and not q.table_key:
        found.append("a numeric question needs its table_key")
    if q.route == "refuse":
        if q.gold:
            found.append(f"a refusal has no gold provisions, found {len(q.gold)}")
        if not q.refusal_reason:
            found.append("a refusal needs a reason")
    elif q.refusal_reason:
        found.append("a reason is only for refusals")
    if q.type == "as_of" and not q.as_of:
        found.append("an as_of question needs its as_of date")
    if q.as_of and not _valid_date(q.as_of):
        found.append(f"as_of {q.as_of!r} is not a valid YYYY-MM-DD date")
    return found


def check_questions(questions: Sequence[GoldQuestion]) -> list[str]:
    """Problems with each question and across the set (an empty list means the questions are well formed)."""
    problems = [f"{q.id}: {p}" for q in questions for p in _question_problems(q)]
    for id_, n in Counter(q.id for q in questions).items():
        if n > 1:
            problems.append(f"duplicate id {id_} ({n} times)")
    seen: dict[str, str] = {}
    for q in questions:
        key = _norm(q.text).casefold()
        if key in seen and seen[key] != q.id:
            problems.append(f"{q.id}: duplicate text of {seen[key]}")
        seen.setdefault(key, q.id)
    return problems


def check_mix(
    questions: Sequence[GoldQuestion],
    types: dict[str, int] = MIX_TARGETS,
    languages: dict[str, int] = LANGUAGE_TARGETS,
    reasons: dict[str, int] = REASON_TARGETS,
) -> list[str]:
    """Where the counts differ from the plan: by type, language and refusal reason."""
    actual = {
        "type": Counter(q.type for q in questions),
        "language": Counter(q.language for q in questions),
        "reason": Counter(q.refusal_reason for q in questions if q.refusal_reason),
    }
    problems = []
    for name, targets in (("type", types), ("language", languages), ("reason", reasons)):
        for key in sorted(set(targets) | set(actual[name])):
            have, want = actual[name].get(key, 0), targets.get(key, 0)
            if have != want:
                problems.append(f"{name} {key}: {have} questions, target {want}")
    return problems


# --- leakage ---------------------------------------------------------------------------------------------


def _content_words(text: str) -> set[str]:
    return {w for w in _WORDS.findall(text.casefold()) if len(w) > 3}


def overlap_ratio(question: str, texts: Iterable[str], idf: dict[str, float] | None = None) -> float:
    """Share of the question's longer words found in the best-matching text; high means a copied answer.

    With `idf` (word -> rarity weight, see Corpus.idf) the words are weighted, so the vocabulary every text
    on the topic shares ("consent", "child") counts for little and distinctive wording for a lot. A word the
    corpus never saw gets the largest weight. If every weight is zero the plain share is used."""
    words = _content_words(question)
    if not words:
        return 0.0
    weight = {w: 1.0 for w in words}
    if idf:
        top = max(idf.values())
        weight = {w: idf.get(w, top) for w in words}
        if sum(weight.values()) == 0:
            weight = {w: 1.0 for w in words}
    total = sum(weight.values())
    return max((sum(weight[w] for w in words & _content_words(t)) / total for t in texts), default=0.0)


# --- the corpus ------------------------------------------------------------------------------------------


class Corpus:
    """The parsed provisions, grouped by document (instrument, version, language)."""

    def __init__(self, provisions: Iterable[Provision]) -> None:
        self._docs: dict[tuple[str, str, str], list[Provision]] = {}
        self._idf: dict[str, dict[str, float]] = {}
        for p in provisions:
            self._docs.setdefault((p.instrument, p.version, p.language), []).append(p)

    @classmethod
    def from_dir(cls, directory: Path | None = None) -> Corpus:
        paths = sorted((directory or settings.PARSED_DIR).glob("*.jsonl"))
        return cls(p for path in paths for p in read_jsonl(path))

    def instruments(self) -> set[str]:
        return {instrument for instrument, _, _ in self._docs}

    def documents(self, g: GoldProvision, prefer_language: str | None = None) -> list[list[Provision]]:
        """The documents a gold provision may be found in: its instrument, narrowed by version, language."""
        wanted = g.language or prefer_language
        docs = {k: v for k, v in self._docs.items() if k[0] == g.instrument and (g.version in (None, k[1]))}
        narrowed = {k: v for k, v in docs.items() if wanted is None or k[2] == wanted}
        return list((narrowed if (g.language or narrowed) else docs).values())

    @staticmethod
    def unit_members(doc: list[Provision], g: GoldProvision) -> list[Provision]:
        return [p for p in doc if p.unit == g.unit and unit_key(p) == g.unit_path]

    def idf(self, language: str) -> dict[str, float]:
        """Rarity weight of each longer word in one language: log(units / units that contain the word)."""
        if language not in self._idf:
            units: dict[tuple, list[str]] = {}
            for (instrument, version, lang), doc in self._docs.items():
                if lang == language:
                    for p in doc:
                        units.setdefault((instrument, version, p.unit, unit_key(p)), []).append(p.text)
            frequency: Counter[str] = Counter()
            for texts in units.values():
                frequency.update(_content_words(" ".join(texts)))
            total = max(len(units), 1)
            self._idf[language] = {w: math.log(total / n) for w, n in frequency.items()}
        return self._idf[language]

    def unit_texts(self, g: GoldProvision, prefer_language: str | None = None) -> list[str]:
        texts = []
        for doc in self.documents(g, prefer_language):
            members = self.unit_members(doc, g)
            if members:
                texts.append(_norm(" ".join(p.text for p in members)))
        return texts


def check_against_corpus(questions: Sequence[GoldQuestion], corpus: Corpus) -> list[str]:
    """Every gold provision must exist: its unit, its pinpoint ids and its quotes (whitespace ignored)."""
    problems: list[str] = []
    for q in questions:
        for g in q.gold:
            where = f"{g.instrument} {g.unit} {'/'.join(g.unit_path)}"
            if g.instrument not in corpus.instruments():
                problems.append(f"{q.id}: instrument {g.instrument} is not in the corpus")
                continue
            docs = corpus.documents(g)
            if not docs:
                problems.append(
                    f"{q.id}: no document of {g.instrument} for version {g.version} language {g.language}"
                )
                continue
            members = [m for doc in docs for m in corpus.unit_members(doc, g)]
            if not members:
                problems.append(f"{q.id}: unit {where} not found")
                continue
            ids = {m.id for m in members}
            problems += [
                f"{q.id}: pinpoint {pid} not found in {where}" for pid in g.pinpoints if pid not in ids
            ]
            texts = corpus.unit_texts(g)
            problems += [
                f"{q.id}: quote {quote!r} not found in {where}"
                for quote in g.quotes
                if not any(_norm(quote) in text for text in texts)
            ]
    return problems


def overlap_warnings(questions: Sequence[GoldQuestion], corpus: Corpus, threshold: float = 0.6) -> list[str]:
    """Warnings for retrieval questions that share most of their longer words with their own gold text."""
    warnings = []
    for q in questions:
        if q.route != "retrieve":
            continue
        texts = [t for g in q.gold if g.role == "primary" for t in corpus.unit_texts(g, q.language)]
        ratio = overlap_ratio(q.text, texts, corpus.idf(q.language))
        if ratio >= threshold:
            warnings.append(
                f"{q.id}: shares {ratio:.0%} of its words with its gold text, a keyword search would find it"
            )
    return warnings
