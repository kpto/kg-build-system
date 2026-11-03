"""The aggregate instruction: union a component's binding relations."""
from __future__ import annotations

from typing import Any

from .....kernel import StepOutcome
from ....internal.service.runtime import success
from ....internal.dto.instruction_dto import AggregateInstructionDTO


def handle_aggregate(
    context: Any,
    instruction: AggregateInstructionDTO,
    services: Any,
) -> StepOutcome:
    source_relations = tuple(
        services.relations.reference(item.artifact.value)
        for contributions in context.inputs.values()
        for item in contributions
        if item.artifact is not None
    )
    union_sql = " UNION ALL ".join(
        f"SELECT * FROM {source}" for source in source_relations
    )
    relation = services.relations.view(instruction.relation, union_sql)
    return success(context, relation)


__all__ = ["handle_aggregate"]
