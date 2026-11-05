"""The DuckDB SQL instruction emitter.

This is the thin instruction-facing wrapper over the registry-backed SQL
emitter. It produces a kernel ``Instruction`` whose payload carries the rendered
statement and, when one is supplied, the relation name the step publishes.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from kg_build_system.distribution.service.internal.emission import RelationPlan
from kg_build_system.kernel import Instruction, InstructionKind

from .emitter import DuckDbInstructionEmitter

DEFAULT_SQL_KIND = InstructionKind("sql", "duckdb")


@dataclass(frozen=True, slots=True)
class DuckDbSqlEmitter:
    """Emit a DuckDB SQL instruction from an engine-neutral relation plan."""

    kind: InstructionKind = DEFAULT_SQL_KIND
    instruction_emitter: DuckDbInstructionEmitter = field(
        default_factory=DuckDbInstructionEmitter,
    )

    def emit(self, plan: RelationPlan, context: Any = None) -> Instruction:
        """Render one relation plan as DuckDB SQL and wrap it as an instruction."""
        sql = self.instruction_emitter.relation_sql(plan)
        payload: dict[str, Any] = {"sql": sql}
        if context is not None and context.relation:
            payload["relation"] = context.relation
        return Instruction(kind=self.kind, payload=payload)


__all__ = ["DEFAULT_SQL_KIND", "DuckDbSqlEmitter"]
