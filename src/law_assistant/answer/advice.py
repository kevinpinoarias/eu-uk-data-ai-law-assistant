"""
Searching for a question about the user's own situation (decision 124).

A person asks "can I use data of restaurants to train a model for a future business"; the law says
nothing about restaurants and everything about lawful basis, purpose limitation, further processing
and training data for AI systems. Search matches words, so the question alone lands on the wrong
articles (on three examples none could then be answered from what was found). For these questions
only, the model restates the question as one general question in the law's own vocabulary, and the
pipeline searches with the question and the restatement together, as the earlier rewriting
experiment (R6) did. The answer is still written, and every quotation still checked, against the
original question and the passages found; if the model cannot be reached the restatement is empty
and the question is searched as it is.
"""

from __future__ import annotations

from law_assistant.llm.gemini import LLMError

REWRITE_INSTRUCTIONS = (
    "A user asked a question about their own plan or situation. Restate it as ONE general question about "
    "what EU, Spanish or UK data-protection and AI law says on the topic, in the law's own vocabulary (for "
    "example: personal data, controller, lawful basis, purpose limitation, further processing, data subject "
    "rights, special categories, AI system, training data, high-risk). Remove the personal framing (I, my, "
    "our) and any business detail that is not about the legal topic. Keep the language of the question. "
    "Reply with the restated question only, at most 40 words."
)


class AdviceRewriter:
    def __init__(self, generator) -> None:
        self._generator = generator

    def __call__(self, question: str) -> str:
        try:
            reply = self._generator.generate(
                question, system=REWRITE_INSTRUCTIONS, temperature=0.0, max_output_tokens=120
            )
        except LLMError:
            return ""
        return reply.strip()
