"""The relation instruction: define one named relation from lowered SQL."""
from __future__ import annotations

from typing import Any

from .....kernel import StepOutcome
from ..._runtime import success
from ..ir import RelationInstructionIR


def handle_relation(
    context: Any,
    instruction: RelationInstructionIR,
    services: Any,
) -> StepOutcome:
    relation = services.relations.view(instruction.relation, instruction.sql)
    return success(context, relation)


__all__ = ["handle_relation"]
