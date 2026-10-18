"""
Step 5 of the answer layer: ask the language model to write a short answer from numbered passages, and to
support it with quotations that step 6 (verify.py) then checks in code.

The model is told to use only the passages, to copy its quotations exactly, to say so when the passages
do not answer the question, and not to give legal advice. It replies in JSON so the reply can be read
without guessing. The labels that tell the reader which law, provision and text version an answer used
are built by this module from the chunk's own fields, never by the model, so they cannot be wrong or
missing.
"""

from __future__ import annotations

import json
import re
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date

from law_assistant.answer.verify import Citation
from law_assistant.chunk.chunker import Chunk
from law_assistant.llm.gemini import LLMError

LANGUAGE_NAMES = {"en": "English", "es": "Spanish"}

ANSWER_INSTRUCTIONS = (
    "You answer questions about EU, Spanish and UK data-protection and AI law for people who are not "
    "lawyers. You are given numbered passages of the law. Rules:\n"
    "1. Use only the passages. Do not add anything from memory, even if you know it.\n"
    "2. If the passages do not contain enough to answer the question, set enough_evidence to false and "
    "say briefly in the answer what is missing; do not guess.\n"
    "3. Write in the language you are told, in plain words, in at most 150 words: the direct answer "
    "first, then the conditions or exceptions that matter. Name the law and the provision in the text "
    "(for example: GDPR Article 6(1)(f)). Passages from different laws or from different versions of the "
    "same law (for example the EU GDPR and the UK GDPR, or the text as first published and the "
    "consolidated text) must not be mixed up: say which one each statement comes from.\n"
    "4. Support the answer with quotations. Each citation gives the passage number and a quotation "
    "copied exactly from that passage, word for word, in the passage's own language (at most 40 words; "
    "use ... to skip words). Every claim in the answer needs a citation behind it.\n"
    "5. This is an explanation of what the text says, not legal advice: do not tell the user what to do "
    "in their own situation.\n"
    'Reply with JSON only: {"enough_evidence": true|false, "answer": "...", '
    '"citations": [{"passage": 1, "quote": "..."}]}.'
)


def describe_version(version: str) -> str:
    if version == "oj":
        return "as first published in the Official Journal"
    if version == "consolidated":
        return "consolidated text"
    if m := re.fullmatch(r"(consolidated|as-of|revised)-(\d{4})(\d{2})(\d{2})", version):
        when = date(int(m.group(2)), int(m.group(3)), int(m.group(4)))
        day = f"{when.day} {when.strftime('%B')} {when.year}"
        return f"consolidated text of {day}" if m.group(1) == "consolidated" else f"text in force on {day}"
    return version


def source_label(chunk: Chunk) -> str:
    law = chunk.context.split(" | ")[0]
    return f"{law}, {chunk.citation} ({describe_version(chunk.version)})"


DATE_INSTRUCTIONS = (
    "6. A passage header may say 'in force from <date>': the date the current wording of that provision "
    "took effect, taken from the source's own dates. For a 'since when' question use it, and say that it is "
    "the date this wording took effect; if the header has no such date, do not guess one.\n"
)


ADVICE_INSTRUCTIONS = (
    "Special case: the user is asking about their own plan or situation. Do not decide it for them: do "
    "not say what they should do and do not answer yes or no to whether they may. Explain in general "
    "terms what the passages say that bears on the question, in conditional form (for example 'if the "
    "data are personal data, ...'), and say briefly what the answer depends on (the kind of data, the "
    "purpose, who the parties are, the country). Do not write the document, policy or text they ask "
    "for; explain what the passages require of it. Every statement still needs a citation.\n"
)


def answer_instructions(include_dates: bool = False, advice: bool = False) -> str:
    """The standing rules. With `include_dates` the in-force-date rule is added, and with `advice` the
    rule for a question about the user's own situation, both before the reply format. With neither it
    is the text that was measured."""
    if not include_dates and not advice:
        return ANSWER_INSTRUCTIONS
    head, tail = ANSWER_INSTRUCTIONS.split("Reply with JSON only", 1)
    extra = (DATE_INSTRUCTIONS if include_dates else "") + (ADVICE_INSTRUCTIONS if advice else "")
    return head + extra + "Reply with JSON only" + tail


def describe_date(iso: str) -> str:
    when = date.fromisoformat(iso)
    return f"{when.day} {when.strftime('%B')} {when.year}"


def format_passages(chunks: Sequence[Chunk], *, include_dates: bool = False) -> str:
    def header(c: Chunk) -> str:
        text = f"text version: {describe_version(c.version)}"
        if include_dates and c.in_force_from:
            text += f"; in force from {describe_date(c.in_force_from)}"
        return f"({text})"

    return "\n\n".join(f"[{i}] {header(c)}\n{c.embed_text}" for i, c in enumerate(chunks, start=1))


@dataclass(frozen=True)
class Draft:
    enough_evidence: bool
    text: str
    citations: list[Citation] = field(default_factory=list)


def parse_draft(reply: str) -> Draft:
    cleaned = re.sub(r"^```(?:json)?|```$", "", reply.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(cleaned)
        enough, text = data["enough_evidence"], data["answer"]
        citations = [Citation(int(c["passage"]), str(c["quote"])) for c in data.get("citations") or []]
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        raise LLMError(f"the answer is not the expected JSON: {reply[:200]!r}") from error
    if not isinstance(enough, bool) or not isinstance(text, str):
        raise LLMError("the answer's fields have the wrong types")
    return Draft(enough, text.strip(), citations)


class AnswerWriter:
    def __init__(self, generator, *, max_output_tokens: int = 1200, include_dates: bool = False) -> None:
        self._generator, self._max, self._include_dates = generator, max_output_tokens, include_dates

    def write(
        self,
        question: str,
        language: str,
        chunks: Sequence[Chunk],
        *,
        as_of: str | None = None,
        advice: bool = False,
    ) -> Draft:
        when = f"the law as it stood on {as_of}" if as_of else "the current law"
        prompt = (
            f"Answer in: {LANGUAGE_NAMES[language]}\n"
            f"The question is about: {when}\n"
            f"Question: {question}\n\n"
            f"Passages:\n{format_passages(chunks, include_dates=self._include_dates)}"
        )
        reply = self._generator.generate(
            prompt,
            system=answer_instructions(self._include_dates, advice),
            temperature=0.0,
            max_output_tokens=self._max,
            json_output=True,
        )
        return parse_draft(reply)
