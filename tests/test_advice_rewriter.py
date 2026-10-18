"""
The advice rewriter: for a question about the user's own situation, the pipeline also searches with a restatement of
it as a general question in the law's own vocabulary ("can I use restaurant data to train a model" becomes a question
about lawful basis, purpose limitation and training data for AI systems), because search could not bridge that
vocabulary gap alone (decision 124). The model is fake here; what is tested is the prompt, the plumbing and that a
failure never blocks the answer.
"""

from __future__ import annotations

from law_assistant import settings
from law_assistant.answer.advice import REWRITE_INSTRUCTIONS, AdviceRewriter
from law_assistant.evaluation.gold import read_gold
from law_assistant.llm.gemini import LLMError


class Generator:
    def __init__(self, reply="What does the GDPR say about further processing?", error=None):
        self.reply, self.error, self.calls = reply, error, []

    def generate(self, prompt, **kwargs):
        self.calls.append((prompt, kwargs))
        if self.error:
            raise self.error
        return self.reply


def test_the_rewriter_asks_for_one_general_question_in_the_laws_vocabulary_and_keeps_the_language():
    text = REWRITE_INSTRUCTIONS.lower()
    for phrase in (
        "own plan or situation",
        "general question",
        "purpose limitation",
        "remove the personal framing",
    ):
        assert phrase in text, phrase
    assert "language of the question" in text and "restated question only" in text


def test_it_sends_the_question_with_the_instructions_at_temperature_zero_and_returns_the_trimmed_reply():
    gen = Generator(reply="  What does the GDPR say about further processing?\n")
    reply = AdviceRewriter(gen)("Can I reuse my customers' data?")
    assert reply == "What does the GDPR say about further processing?"
    prompt, kwargs = gen.calls[0]
    assert prompt == "Can I reuse my customers' data?"
    assert kwargs["system"] == REWRITE_INSTRUCTIONS and kwargs["temperature"] == 0.0


def test_a_failure_of_the_model_gives_an_empty_restatement_instead_of_blocking_the_answer():
    assert AdviceRewriter(Generator(error=LLMError("HTTP 503")))("Can I?") == ""


def test_no_scored_question_is_quoted_in_the_prompt():
    test_half = [q for q in read_gold(settings.GOLD_DIR / "questions.jsonl") if q.split == "test"]
    batch_c = read_gold(settings.PROJECT_ROOT / "eval" / "batch_c" / "questions.jsonl")
    assert not [q.id for q in test_half + batch_c if q.text.casefold() in REWRITE_INSTRUCTIONS.casefold()]
