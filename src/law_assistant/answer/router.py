"""
Step 2 of the answer layer: decide what to do with a question before searching.

- retrieve: look the answer up in the law's text (most questions);
- table: the question asks for an exact figure (a fine ceiling, a deadline, an age); answer from the
  facts table;
- refuse: the question is outside the corpus (another country's law, a regulator's guide) or asks for legal
  advice about the user's own situation.

Two routers are provided so they can be compared. `RuleRouter` is a short list of readable patterns: free,
instant and easy to explain, but blunt. `LLMRouter` asks a language model to apply the same definitions. Both
return a `Route`; neither sees the gold labels. The routing accuracy of each is measured in
experiments/p4_router.py.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from law_assistant.answer.understand import understand
from law_assistant.llm.gemini import LLMError

ROUTES = ("retrieve", "table", "refuse")
REASONS = ("out_of_corpus", "legal_advice")


@dataclass(frozen=True)
class Route:
    route: str
    reason: str | None = None  # only for refuse: out_of_corpus | legal_advice
    why: str = ""


_FOREIGN = re.compile(
    r"\b(california|texas|virginia|colorado|ccpa|cpra|hipaa|coppa|lgpd|pipl|pipeda|popia|appi)\b",
    re.IGNORECASE,
)
_GUIDE = re.compile(
    r"\b(guidance|guide|guides|guidelines|guía|guías|directrices|recommend\w*|recomend\w*)\b", re.IGNORECASE
)
_REGULATOR = re.compile(r"\b(ico|aepd|edpb|cepd|cnil|garante|commission)\b", re.IGNORECASE)
_COMPLIANT = re.compile(
    r"\b(am i|are we|is my|is our|are my|are our)\b.{0,40}\b(compliant|compliance|legal|lawful)\b"
    r"|\b(mi|mis|nuestr[oa]s?)\b.{0,40}\b(cumple|cumplimos|cumplo|cumplen)\b|¿?\bcumplo\b|\bcumplimos con\b",
    re.IGNORECASE,
)
_DRAFTING = re.compile(
    r"\b(write|draft|prepare|generate|create)\b.{0,30}\b(a|an|the|my|our)\b.{0,30}"
    r"\b(policy|contract|clause|agreement|notice|dpia|template)\b"
    r"|\b(redacta|escribe|genera|prepara|elabora)\w*\b.{0,40}\b(política|cláusula|contrato|aviso|plantilla)\b",
    re.IGNORECASE,
)
_SHOULD = re.compile(
    r"\b(should (i|we)|ought (i|we)|debo|debemos|deberíamos|debería|deberia)\b", re.IGNORECASE
)
_RECENT = re.compile(
    r"\b(yesterday|last (week|month|night)|this morning|ayer|anoche|la semana pasada|esta mañana)\b",
    re.IGNORECASE,
)
_FIRST_PERSON = re.compile(
    r"\b(we|our|my|i|nuestr\w+|mi|mis|tenemos|sufrimos|tuvimos|hemos)\b|\b\w+(imos|amos)\b", re.IGNORECASE
)
_FIGURE = re.compile(
    r"\b(maximum|highest|biggest|largest|top|upper)\b.{0,15}\b(fine|penalty|sanction)s?\b"
    r"|\bhow (much|many|long|old)\b|\bwhat (age|is the (minimum )?age)\b|\bminimum age\b"
    r"|\b(deadline|time limit)\b|\bmulta (máxima|más alta)\b|\bsanción (máxima|más alta)\b"
    r"|\bcuánt[oa]s?\b|\bqué edad\b|\ba qué edad\b|\bedad mínima\b|\bplazo\b",
    re.IGNORECASE,
)
_COMPARISON = re.compile(r"\b(differ\w*|compar\w*|versus|vs|diferenc\w+)\b", re.IGNORECASE)


class RuleRouter:
    """Readable patterns, checked in this order: another country's law or a regulator's guide, advice
    about the user's own situation, an exact figure about one jurisdiction and no date, otherwise retrieve."""

    name = "rules"

    def route(self, text: str) -> Route:
        if _FOREIGN.search(text) or (_GUIDE.search(text) and _REGULATOR.search(text)):
            return Route("refuse", "out_of_corpus", "names another country's law or a regulator's guide")
        own_event = _RECENT.search(text) and _FIRST_PERSON.search(text)
        if _COMPLIANT.search(text) or _DRAFTING.search(text) or _SHOULD.search(text) or own_event:
            return Route("refuse", "legal_advice", "asks about the user's own situation or for a document")
        u = understand(text)
        if (
            _FIGURE.search(text)
            and len(u.jurisdictions) <= 1
            and not u.as_of
            and not _COMPARISON.search(text)
        ):
            return Route("table", None, "asks for an exact figure")
        return Route("retrieve", None, "a question about what the text says")


ROUTE_INSTRUCTIONS = (
    "You route questions for an assistant that answers from EU, Spanish and UK data-protection and AI law "
    "(the GDPR, the EU AI Act and its 2026 amendment, the UK GDPR, the UK Data Protection Act 2018, "
    "the UK Data (Use and Access) Act 2025 and Spain's data-protection law, the LOPDGDD). It holds the "
    "text of those laws and a small table of exact figures. Decide what to do with the user's question.\n"
    "Routes:\n"
    '- "retrieve": the question asks what the law says or means (a right, a duty, a definition, a comparison '
    "between jurisdictions, what applied on a given date). This is the usual case, including a general "
    "question that mentions the user's business ('do I need a data protection officer?').\n"
    '- "table": the question asks for ONE exact figure about one jurisdiction as it stands now: a maximum '
    "fine, a deadline in days or hours, a minimum age. Questions that compare jurisdictions or ask about a "
    "past date are 'retrieve'.\n"
    '- "refuse": the assistant must not answer. Give a reason: "out_of_corpus" (another '
    "country's law, such as California; or a regulator's guide or guidance rather than the law "
    'itself) or "legal_advice" (the user wants a judgment on their own concrete situation, a '
    "compliance check, or a document written for them).\n"
    'Reply with JSON only: {"route": "retrieve"|"table"|"refuse", '
    '"reason": null|"out_of_corpus"|"legal_advice"}.'
)


# Candidate (decision 116), written after the sealed test half showed three refusals sent to search
# (a court case, the largest fine, an adequacy list) and an application-date question sent to search.
# It states those categories as definitions, with a guard against refusing questions about what the
# law itself says. Not the default: it is measured on batch C (experiments/c1_routing_fixes.py)
# before any decision to adopt it.
ROUTE_INSTRUCTIONS_V2 = (
    "You route questions for an assistant that answers from EU, Spanish and UK data-protection and "
    "AI law (the GDPR, the EU AI Act and its 2026 amendment, the UK GDPR, the UK Data Protection Act "
    "2018, the UK Data (Use and Access) Act 2025 and Spain's data-protection law, the LOPDGDD). It "
    "holds the text of those laws and a small table of exact figures. It does not hold case law, "
    "regulators' decisions or guidance, or any other country's law. Decide what to do with the "
    "user's question.\n"
    "Routes:\n"
    '- "retrieve": the question asks what the law says or means (a right, a duty, a definition, a '
    "comparison between jurisdictions, what applied on a given date). This is the usual case, "
    "including a general question that mentions the user's business ('do I need a data protection "
    "officer?'). A question that mentions courts, regulators, fines, adequacy or transfers abroad is "
    "still 'retrieve' when it asks what the text of the law says (the right to go to court, an "
    "authority's powers, the rule on adequacy decisions, the factors that decide a fine, who can be "
    "fined).\n"
    '- "table": the question asks for ONE exact figure about one jurisdiction as it stands now: the '
    "maximum fine, a deadline in days or hours, a minimum age, or the date from which a rule starts "
    "to apply. Questions that compare jurisdictions or ask about a past date are 'retrieve'.\n"
    '- "refuse": the assistant must not answer. Give a reason: "out_of_corpus" (another '
    "country's law, such as California; a regulator's guide or guidance rather than the law itself; "
    "what a court decided in a case; a regulator's enforcement decision or the fines actually "
    "imposed on named companies; or which countries currently have an adequacy decision) or "
    '"legal_advice" (the user wants a judgment on their own concrete situation, a compliance check, '
    "or a document written for them).\n"
    'Reply with JSON only: {"route": "retrieve"|"table"|"refuse", '
    '"reason": null|"out_of_corpus"|"legal_advice"}.'
)


def parse_route(text: str) -> Route:
    cleaned = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        data = json.loads(cleaned)
        route, reason = data["route"], data.get("reason")
    except (ValueError, KeyError, TypeError, AttributeError) as error:
        raise LLMError(f"the router's reply is not the expected JSON: {text[:200]!r}") from error
    if route not in ROUTES:
        raise LLMError(f"unknown route {route!r}")
    if route == "refuse" and reason not in REASONS:
        raise LLMError(f"a refusal needs one of {REASONS}, not {reason!r}")
    if route != "refuse" and reason is not None:
        raise LLMError(f"only a refusal has a reason, not {route!r} with {reason!r}")
    return Route(route, reason, "model")


class LLMRouter:
    name = "llm"

    def __init__(self, generator, instructions: str = ROUTE_INSTRUCTIONS) -> None:
        self._generator = generator
        self._instructions = instructions

    def route(self, text: str) -> Route:
        reply = self._generator.generate(
            text, system=self._instructions, temperature=0.0, max_output_tokens=100, json_output=True
        )
        return parse_route(reply)
