"""
Answer-layer step 2b: for a question that asks for an exact figure, find the row of the facts table it is
about. Each fact is described by its subject and its one-line summary in the question's language; the closest
description by cosine similarity wins, but only if it is close enough. A named jurisdiction limits the choice
to that jurisdiction's facts. A question with no good match returns no fact, and the pipeline then
searches the text instead of guessing a figure.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass, replace

from law_assistant.facts.table import Fact

EmbedTexts = Callable[[list[str]], list[list[float]]]


@dataclass(frozen=True)
class FactMatch:
    fact: Fact | None
    score: float


class FactMatcher:
    def __init__(self, facts: Sequence[Fact], embed_texts: EmbedTexts, *, threshold: float) -> None:
        self._facts, self._embed, self.threshold = list(facts), embed_texts, threshold
        self._vectors = {
            lang: embed_texts([self._describe(f, lang) for f in self._facts]) for lang in ("en", "es")
        }

    @staticmethod
    def _describe(fact: Fact, language: str) -> str:
        subject = fact.subject_en if language == "en" else fact.subject_es
        return f"{subject}. {fact.summary(language)}"

    def match(self, question: str, language: str, jurisdictions: Sequence[str] = ()) -> FactMatch:
        (query,) = self._embed([question])
        best, best_score = None, 0.0
        for fact, vector in zip(self._facts, self._vectors[language], strict=True):
            if jurisdictions and not set(jurisdictions) & set(fact.jurisdictions):
                continue
            score = sum(a * b for a, b in zip(query, vector, strict=True))
            if score > best_score:
                best, best_score = fact, score
        if best is None or best_score < self.threshold:
            return FactMatch(None, best_score)
        return FactMatch(best, best_score)


PICK_INSTRUCTIONS = (
    "You pick the row of a table of exact legal figures that answers a user's question. Each row is a "
    "key and a subject. Choose the ONE row that gives the exact figure the question asks for, "
    "respecting the jurisdiction the question names (EU, UK and Spain have separate rows). If no row "
    "gives the figure the question asks for, or the question needs more than a single figure, answer "
    'null. Reply with JSON only: {"key": "<a key from the list>"} or {"key": null}.\n'
    "Rows:\n"
)


# Candidate (decision 116), written after the sealed test half showed the upper fine tier given for a
# breach-notification question (Article 33 falls in the lower tier). Used together with `apply_scope`,
# which puts the infringements each tier covers into the row's subject, because the model sees only
# the subjects. Not the default.
PICK_INSTRUCTIONS_V2 = (
    "You pick the row of a table of exact legal figures that answers a user's question. Each row is "
    "a key and a subject. Choose the ONE row that gives the exact figure the question asks for, "
    "respecting the jurisdiction the question names (EU, UK and Spain have separate rows). Some rows "
    "are fine tiers whose subject lists the obligations they cover: if the question names a breach, "
    "choose the tier whose list contains that obligation; if it names none and asks for the highest "
    "or maximum fine, choose the highest tier. If no row gives the figure the question asks for, or "
    "the question needs more than a single figure, answer null. Reply with JSON only: "
    '{"key": "<a key from the list>"} or {"key": null}.\n'
    "Rows:\n"
)


def apply_scope(facts: Sequence[Fact], overlay: dict[str, dict[str, str]]) -> list[Fact]:
    """The facts with the subjects named in `overlay` replaced (key -> subject_en, subject_es)."""
    unknown = set(overlay) - {f.key for f in facts}
    if unknown:
        raise KeyError(f"the overlay names facts that do not exist: {sorted(unknown)}")
    return [
        replace(f, subject_en=overlay[f.key]["subject_en"], subject_es=overlay[f.key]["subject_es"])
        if f.key in overlay
        else f
        for f in facts
    ]


class LLMFactPicker:
    """Let a language model choose the row, or none, from the whole table (19 short lines)."""

    def __init__(self, facts: Sequence[Fact], generator, instructions: str = PICK_INSTRUCTIONS) -> None:
        self._facts = {f.key: f for f in facts}
        self._generator = generator
        rows = [f"- {f.key} ({', '.join(f.jurisdictions)}): {f.subject_en}" for f in facts]
        self._system = instructions + "\n".join(rows)

    def pick(self, question: str, jurisdictions: Sequence[str] = ()) -> Fact | None:
        named = f"Jurisdictions named in the question: {', '.join(jurisdictions) or 'none'}.\n"
        reply = self._generator.generate(
            f"{named}Question: {question}",
            system=self._system,
            temperature=0.0,
            max_output_tokens=100,
            json_output=True,
        )
        try:
            key = json.loads(re.sub(r"^```(?:json)?|```$", "", reply.strip(), flags=re.MULTILINE))["key"]
        except (ValueError, KeyError, TypeError):
            return None
        return self._facts.get(key) if isinstance(key, str) else None
