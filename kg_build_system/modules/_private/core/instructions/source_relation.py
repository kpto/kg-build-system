"""The source-relation instruction: open a physical source as a typed view."""
from __future__ import annotations

from typing import Any

from .....kernel import StepOutcome, StepStatus
from ..._runtime import success
from ..ir import SourceRelationInstructionIR
from ..reading import open_source


def handle_source_relation(
    context: Any,
    instruction: SourceRelationInstructionIR,
    services: Any,
) -> StepOutcome:
    relation, warned = open_source(instruction, services)
    return success(
        context,
        relation,
        status=StepStatus.WARNING if warned else StepStatus.SUCCEEDED,
    )


__all__ = ["handle_source_relation"]
