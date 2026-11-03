"""Execute a ``sql`` step instruction through the DuckDB relation service."""
from __future__ import annotations

from ......kernel import (
    DisruptedExecutionContext,
    ExecutionContext,
    StepOutcome,
)
from ..instructions import Instruction, instruction_payload
from ..runtime.outcome import skipped, succeeded


class SqlInstructionExecutor:
    """Define a named relation from SQL carried only by the instruction."""

    def execute(
        self,
        context: ExecutionContext | DisruptedExecutionContext,
        instruction: Instruction,
    ) -> StepOutcome:
        """Materialize the instruction's SQL as the step's relation output."""
        if isinstance(context, DisruptedExecutionContext):
            return skipped(context)
        payload = instruction_payload(instruction)
        sql = payload.get("sql")
        if not isinstance(sql, str) or not sql.strip():
            raise ValueError("a sql instruction requires a non-empty 'sql' payload")
        relation = payload.get("relation", context.step.name)
        if not isinstance(relation, str) or not relation:
            raise ValueError(
                "a sql instruction requires a non-empty 'relation' payload"
            )
        reference = context.services.relations.materialize(relation, sql)
        return succeeded(context, reference)


__all__ = ["SqlInstructionExecutor"]
