"""
The answer pipeline: the steps of docs/PHASE4_PLAN.md wired in order.

    understand -> route -+-> refuse ------------------------------------------> answer
                         +-> lookup (a figure from the table) --found--------> answer
                         |            +-- no row ---+
                         +-> retrieve <--------------+
                              -> generate -> verify -> answer, or abstain

Every step is a function from the shared state to the keys it adds, so the same steps can be run by the plain
loop in `AnswerPipeline.ask` or wired into a LangGraph graph (graph.py) without change. The language model
is used in exactly one place that writes text (generate); everything that makes the answer trustworthy
(routing rules, the table, the check of every quotation, the source labels, the refusal and abstention
messages) is ordinary code that can be tested without a model.
"""

from __future__ import annotations

import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from typing import Any

from law_assistant.answer.generate import describe_version, source_label
from law_assistant.answer.router import Route
from law_assistant.answer.understand import understand
from law_assistant.answer.verify import verify_citations
from law_assistant.chunk.chunker import Chunk
from law_assistant.facts.table import Fact

AS_OF_CUTOFF = (
    "2026-07-27"  # the date of the consolidated AI Act; earlier dates need the first-published text
)

INSTRUMENT_NAMES = {
    "eu-gdpr": "GDPR",
    "eu-ai-act": "AI Act",
    "eu-ai-omnibus": "AI Omnibus Regulation",
    "uk-gdpr": "UK GDPR",
    "uk-dpa-2018": "Data Protection Act 2018",
    "uk-duaa-2025": "Data (Use and Access) Act 2025",
    "es-lopdgdd": "LOPDGDD",
}

MESSAGES = {
    "en": {
        "out_of_corpus": (
            "I can only answer from the texts of EU, Spanish and UK data-protection and AI law that I hold "
            "(the GDPR, the AI Act, the UK GDPR, the Data Protection Act 2018, the Data (Use and Access) Act "
            "2025 and the Spanish LOPDGDD). Your question is about something else, such as another "
            "country's law or a regulator's guidance, so I won't answer it."
        ),
        "legal_advice": (
            "I can explain what the law says, but I can't judge your own situation, check your compliance or "
            "draft documents for you. For that, please consult a qualified lawyer or your data-protection "
            "authority."
        ),
        "abstained": (
            "I couldn't find enough in the texts I hold to answer that reliably. Try rephrasing the "
            "question or naming the law you mean."
        ),
        "sources": "Sources:",
        "disclaimer": "This explains what the text says; it is not legal advice.",
        "caveat": "Note:",
    },
    "es": {
        "out_of_corpus": (
            "Solo puedo responder a partir de los textos de derecho de protección de datos e IA de la UE, "
            "España y el Reino Unido que tengo (el RGPD, el Reglamento de IA, el UK GDPR, la Data "
            "Protection Act 2018, la Data (Use and Access) Act 2025 y la LOPDGDD). Tu pregunta trata de otra "
            "cosa, como la ley de otro país o una guía de un regulador, así que no la respondo."
        ),
        "legal_advice": (
            "Puedo explicar lo que dice la ley, pero no puedo valorar tu situación concreta, comprobar tu "
            "cumplimiento ni redactar documentos por ti. Para eso, consulta con un abogado cualificado o con "
            "tu autoridad de protección de datos."
        ),
        "abstained": (
            "No he encontrado en los textos que tengo lo suficiente para responder con fiabilidad. Prueba a "
            "reformular la pregunta o a indicar de qué ley hablas."
        ),
        "sources": "Fuentes:",
        "disclaimer": "Esto explica lo que dice el texto; no es asesoramiento jurídico.",
        "caveat": "Nota:",
    },
}


@dataclass(frozen=True)
class Source:
    label: str
    chunk_id: str | None = None
    quote: str | None = None
    provision_ids: tuple[str, ...] = ()


@dataclass
class Result:
    kind: str  # answer | table | refused | abstained
    text: str
    language: str
    route: str
    reason: str | None = None
    sources: list[Source] = field(default_factory=list)
    timings: dict[str, float] = field(default_factory=dict)
    trace: dict[str, Any] = field(default_factory=dict)


def _fact_source_label(fact: Fact) -> list[Source]:
    out = []
    for s in fact.sources:
        name = INSTRUMENT_NAMES.get(s.instrument, s.instrument)
        out.append(
            Source(
                f"{name}, {s.unit} {'.'.join(s.unit_path)}",
                None,
                s.quotes[0] if s.quotes else None,
                s.pinpoints,
            )
        )
    return out


class AnswerPipeline:
    def __init__(
        self,
        *,
        router,
        picker,
        current,
        full,
        writer,
        original=None,
        chunks: Sequence[Chunk],
        k: int = 5,
        rewriter: Callable[[str], str] | None = None,
        version_aware: bool = True,
    ) -> None:
        self._router, self._picker, self._writer = router, picker, writer
        self._current, self._full, self._k, self._rewriter = current, full, k, rewriter
        self._original = original or full  # text before the 2026 amendment, for questions dated earlier
        self._version_aware = version_aware  # False reproduces the first design: early date -> `full`
        self._by_id = {c.id: c for c in chunks}

    # ----------------------------------------------------------------- steps (state in, new keys out)
    def understand(self, state: dict) -> dict:
        u = understand(state["question"])
        return {
            "language": u.language,
            "jurisdictions": u.jurisdictions,
            "as_of": u.as_of,
            "wants_original": u.wants_original,
        }

    def route(self, state: dict) -> dict:
        r: Route = self._router.route(state["question"])
        return {"route": r.route, "reason": r.reason}

    def lookup(self, state: dict) -> dict:
        fact = self._picker.pick(state["question"], state["jurisdictions"])
        if fact is None:
            return {"fact": None, "route": "retrieve", "fell_back": True}
        lang = state["language"]
        text = fact.summary(lang)
        caveat = fact.caveat_en if lang == "en" else fact.caveat_es
        if caveat:
            text += f"\n\n{MESSAGES[lang]['caveat']} {caveat}"
        sources = _fact_source_label(fact)
        return {"fact": fact, "result": self._render("table", text, state, sources)}

    def refuse(self, state: dict) -> dict:
        reason = state["reason"] or "legal_advice"
        lang = state["language"]
        return {"result": Result("refused", MESSAGES[lang][reason], lang, "refuse", reason)}

    def retrieve(self, state: dict) -> dict:
        query = state["question"]
        if self._rewriter:
            query = f"{query}\n{self._rewriter(state['question'])}"
        as_of = state["as_of"]
        if as_of and as_of < AS_OF_CUTOFF:
            retriever = self._original if self._version_aware else self._full
        elif state["wants_original"] and self._version_aware:
            retriever = self._full  # every version, so original and current wording can be compared
        else:
            retriever = self._current
        ids = retriever.search(query, self._k)
        return {"passages": [self._by_id[i] for i in ids[: self._k]], "query": query}

    def generate(self, state: dict) -> dict:
        if not state["passages"]:
            return {"draft": None}
        draft = self._writer.write(
            state["question"], state["language"], state["passages"], as_of=state["as_of"]
        )
        return {"draft": draft}

    def verify(self, state: dict) -> dict:
        draft = state["draft"]
        if draft is None or not draft.enough_evidence:
            return {"verification": None}
        return {"verification": verify_citations(draft.citations, state["passages"])}

    def finish(self, state: dict) -> dict:
        lang = state["language"]
        verification = state.get("verification")
        if verification is None or not verification.valid:
            return {"result": Result("abstained", MESSAGES[lang]["abstained"], lang, "retrieve")}
        sources = [
            Source(source_label(v.chunk), v.chunk.id, v.quote, v.chunk.provision_ids)
            for v in verification.valid
        ]
        return {"result": self._render("answer", state["draft"].text, state, sources)}

    # ----------------------------------------------------------------- wiring
    def _render(self, kind: str, body: str, state: dict, sources: list[Source]) -> Result:
        lang = state["language"]
        lines = [body, "", MESSAGES[lang]["sources"]]
        for s in sources:
            lines.append(f"- {s.label}" + (f": “{s.quote}”" if s.quote else ""))
        lines += ["", MESSAGES[lang]["disclaimer"]]
        return Result(kind, "\n".join(lines), lang, "table" if kind == "table" else "retrieve", None, sources)

    def nodes(self) -> dict[str, Callable[[dict], dict]]:
        return {
            "understand": self.understand,
            "route": self.route,
            "lookup": self.lookup,
            "refuse": self.refuse,
            "retrieve": self.retrieve,
            "generate": self.generate,
            "verify": self.verify,
            "finish": self.finish,
        }

    @staticmethod
    def next_step(name: str, state: dict) -> str | None:
        """The edges: which step follows `name` given the state; None means the pipeline is done."""
        if name == "understand":
            return "route"
        if name == "route":
            return {"table": "lookup", "refuse": "refuse"}.get(state["route"], "retrieve")
        if name == "lookup":
            return None if state.get("fact") else "retrieve"
        if name == "refuse":
            return None
        return {"retrieve": "generate", "generate": "verify", "verify": "finish", "finish": None}[name]

    def ask(self, question: str) -> Result:
        state: dict[str, Any] = {"question": question}
        timings: dict[str, float] = {}
        nodes = self.nodes()
        step: str | None = "understand"
        while step:
            started = time.perf_counter()
            state.update(nodes[step](state))
            timings[step] = time.perf_counter() - started
            step = self.next_step(step, state)
        result: Result = state["result"]
        result.timings = timings
        verification = state.get("verification")
        result.trace = {
            "route": state["route"],
            "reason": state.get("reason"),
            "language": state["language"],
            "jurisdictions": state["jurisdictions"],
            "as_of": state["as_of"],
            "fact_key": state["fact"].key if state.get("fact") else None,
            "fell_back_from_table": state.get("fell_back", False),
            "passages": [c.id for c in state.get("passages", [])],
            "enough_evidence": state["draft"].enough_evidence if state.get("draft") else None,
            "invalid_citations": verification.invalid if verification else [],
            "version_notes": sorted({describe_version(c.version) for c in state.get("passages", [])}),
        }
        return result
