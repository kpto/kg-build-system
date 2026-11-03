"""The relation instruction: define one named relation from emitted SQL."""
from __future__ import annotations

from typing import Any

from .....kernel import StepOutcome
from ....internal.service.runtime import success
from ....internal.dto.instruction_dto import RelationInstructionDTO


def handle_relation(
    context: Any,
    instruction: RelationInstructionDTO,
    services: Any,
) -> StepOutcome:
    relation = services.relations.view(instruction.relation, instruction.sql)
    return success(context, relation)


__all__ = ["handle_relation"]
