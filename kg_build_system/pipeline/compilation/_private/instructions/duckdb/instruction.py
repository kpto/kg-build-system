"""The DuckDB SQL instruction emitter.

This is the thin instruction-facing wrapper over the registry-backed SQL
emitter. It produces an ``InstructionDTO`` whose payload carries the rendered
statement and, when one is supplied, the relation name the step publishes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .....contract.public import InstructionDTO
from ....internal.instruction.model import SQL_INSTRUCTION_KIND
from .emitter import DuckDbInstructionEmitter


@dataclass(frozen=True, slots=True)
class DuckDbSqlEmitter:
    """Emit a DuckDB SQL instruction from an engine-neutral relation plan."""

    kind: str = SQL_INSTRUCTION_KIND
    instruction_emitter: DuckDbInstructionEmitter = field(
        default_factory=DuckDbInstructionEmitter,
    )

    def emit(self, plan: Any, context: Any = None) -> InstructionDTO:
        """Render one relation plan as DuckDB SQL and wrap it as an instruction."""
        sql = self.instruction_emitter.relation_sql(plan)
        payload: dict[str, Any] = {"sql": sql}
        if context is not None and context.relation:
            payload["relation"] = context.relation
        return InstructionDTO(kind=self.kind, payload=payload)


__all__ = ["DuckDbSqlEmitter"]
