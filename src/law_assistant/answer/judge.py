"""
A model-based judge for two questions the code cannot answer by itself:

- correctness: does an answer state the key content of the expert's reference answer, without
  contradicting it?
- support: is every claim in the answer backed by the quotations that were cited for it?

The judge is a language model, so its verdicts are evidence, not proof: it is the same model family as
the answer writer (a known bias), so a sample of its verdicts is read by a person and the agreement is
reported next to the results. It never sees the gold provisions, only the question, the reference answer
and the answer.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence

from law_assistant.llm.gemini import LLMError

VERDICTS = ("yes", "partly", "no")
_SCORES = {"yes": 1.0, "partly": 0.5, "no": 0.0}

CORRECTNESS_INSTRUCTIONS = (
    "You grade an answer to a question about data-protection or AI law against a reference answer written "
    "by an expert. Judge content only, not style, wording, length or language (the answer may be in a "
    "different language from the reference).\n"
    '- "yes": the answer states the key content of the reference answer and nothing in it contradicts the '
    "reference.\n"
    '- "partly": it states some of the key content but misses a main point, or adds a main claim that '
    "goes beyond or conflicts with the reference.\n"
    '- "no": it is wrong, contradicts the reference, or does not answer the question (for example it '
    "declines to answer).\n"
    'Reply with JSON only: {"verdict": "yes"|"partly"|"no", "reason": "one sentence"}.'
)

SUPPORT_INSTRUCTIONS = (
    "You check whether an answer is backed by the quotations cited for it. You see the answer and the "
    "quotations (copied from the law). Judge only whether the claims in the answer follow from the "
    "quotations; ignore what you know yourself.\n"
    '- "yes": every claim in the answer follows from the quotations.\n'
    '- "partly": most do, but at least one claim goes beyond the quotations.\n'
    '- "no": the main claims are not supported by the quotations.\n'
    'Reply with JSON only: {"verdict": "yes"|"partly"|"no", "reason": "one sentence"}.'
)


def score_of(verdict: str) -> float:
    return _SCORES[verdict]


def parse_verdict(reply: str) -> tuple[str, str]:
    cleaned = re.sub(r"^```(?:json)?|```$", "", reply.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(cleaned)
        verdict, reason = data["verdict"], str(data.get("reason", ""))
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        raise LLMError(f"the judge's reply is not the expected JSON: {reply[:200]!r}") from error
    if verdict not in VERDICTS:
        raise LLMError(f"unknown verdict {verdict!r}")
    return verdict, reason


class Judge:
    def __init__(self, generator) -> None:
        self._generator = generator

    def _ask(self, system: str, prompt: str) -> tuple[str, str]:
        reply = self._generator.generate(
            prompt, system=system, temperature=0.0, max_output_tokens=300, json_output=True
        )
        return parse_verdict(reply)

    def correctness(self, question: str, reference: str, answer: str) -> tuple[str, str]:
        prompt = f"Question: {question}\n\nReference answer: {reference}\n\nAnswer to grade: {answer}"
        return self._ask(CORRECTNESS_INSTRUCTIONS, prompt)

    def support(self, answer: str, quotes: Sequence[str]) -> tuple[str, str]:
        listed = "\n".join(f"- {q}" for q in quotes)
        return self._ask(SUPPORT_INSTRUCTIONS, f"Answer: {answer}\n\nQuotations:\n{listed}")
