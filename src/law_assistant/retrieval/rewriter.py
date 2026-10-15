"""
The question rewriter used by the pipeline (R6): a language model restates an everyday question in the
law's own vocabulary. The rules are the ones the blind agent of R6.1/R6.2 was given (see
eval/rewrites/README.md), reworded as a system instruction and fixed here so that every rewrite in an
experiment comes from one prompt.
"""

from __future__ import annotations

import re
from collections.abc import Sequence

from law_assistant.llm.gemini import LLMError

INSTRUCTIONS = (
    "You help a search system over EU, Spanish and UK data-protection and AI law (the GDPR, the EU AI Act, "
    "the UK GDPR, the UK Data Protection Act 2018, the UK Data (Use and Access) Act 2025, and Spain's "
    "data-protection law, the LOPDGDD). Ordinary people ask questions in everyday words, but the law is "
    "written in legal terms, so the words often do not match.\n"
    "Rewrite the user's question as ONE search query written the way the legal text itself would put it.\n"
    "Rules:\n"
    "- Keep the same language as the question (English stays English, Spanish stays Spanish).\n"
    "- Use the legal terms of art the relevant law would use (for example data protection officer, "
    "controller, processor, data subject, data protection impact assessment, right of access, high-risk AI "
    "system, deployer, provider, supervisory authority; delegado de protección de datos, responsable del "
    "tratamiento, encargado del tratamiento, evaluación de impacto), and name the instrument when the "
    "question points to one (GDPR / RGPD, AI Act / Reglamento de IA, UK GDPR, Data Protection Act 2018, "
    "LOPDGDD).\n"
    "- Do NOT cite article, section or paragraph numbers.\n"
    "- Keep every part of the question: if it asks two things, the rewrite covers both.\n"
    "- At most 40 words. A phrase or a sentence. Do not answer the question.\n"
    "Reply with the search query only, with no quotation marks and no explanation."
)


_LENGTH_RULE = "- At most 40 words. A phrase or a sentence. Do not answer the question.\n"
assert _LENGTH_RULE in INSTRUCTIONS
EXPANDING_INSTRUCTIONS = INSTRUCTIONS.replace(
    _LENGTH_RULE,
    "- Then add the specific legal terms and concepts the relevant provision itself would contain (the key "
    "words of a definition, the names of the rights, duties, parties or authorities involved), as a list of "
    "phrases after the first part.\n"
    "- At most 60 words in all. Do not answer the question.\n",
)


class LLMRewriter:
    def __init__(self, generator, *, instructions: str = INSTRUCTIONS, max_output_tokens: int = 200) -> None:
        self._generator, self._instructions, self._max = generator, instructions, max_output_tokens

    def rewrite(self, question: str) -> str:
        text = self._generator.generate(
            question, system=self._instructions, temperature=0.0, max_output_tokens=self._max
        )
        cleaned = re.sub(r"\s+", " ", text).strip().strip("\"'«»“”").strip()
        if not cleaned:
            raise LLMError("the model's rewrite was empty")
        return cleaned

    def rewrite_all(self, questions: Sequence[str]) -> dict[str, str]:
        return {q: self.rewrite(q) for q in questions}
