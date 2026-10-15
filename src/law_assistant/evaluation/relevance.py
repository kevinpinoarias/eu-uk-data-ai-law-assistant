"""
When a retrieved chunk counts as a hit for a gold provision (decisions 50 and 51): the same instrument,
unit kind and unit; the pinned version and language if the gold names them; and, when the gold lists pinpoint
ids, a chunk that contains at least one of them. Without pinpoints any chunk of the unit counts.
"""

from __future__ import annotations

from dataclasses import dataclass

from law_assistant.chunk.chunker import Chunk
from law_assistant.evaluation.gold import GoldProvision, GoldQuestion

GRADES = {"primary": 2, "acceptable": 1}


@dataclass(frozen=True)
class Target:
    """One thing a good ranking should contain: a gold provision of a question, with its grade."""

    question_id: str
    index: int  # position among the question's gold provisions
    gold: GoldProvision
    grade: int  # 2 for a primary provision, 1 for an acceptable one


def matches(chunk: Chunk, gold: GoldProvision) -> bool:
    if (chunk.instrument, chunk.unit, chunk.unit_path) != (gold.instrument, gold.unit, gold.unit_path):
        return False
    if gold.version is not None and chunk.version != gold.version:
        return False
    if gold.language is not None and chunk.language != gold.language:
        return False
    if gold.pinpoints:
        return bool(set(gold.pinpoints) & set(chunk.provision_ids))
    return True


def targets_of(question: GoldQuestion) -> list[Target]:
    return [Target(question.id, i, g, GRADES[g.role]) for i, g in enumerate(question.gold)]
