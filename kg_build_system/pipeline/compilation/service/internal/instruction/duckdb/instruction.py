"""DuckDB SQL instruction emitter wrapper.

The SQL emission mechanism lives in ``service._private``; this wrapper keeps the
internal instruction path stable.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from ......contract.model.public import InstructionDTO
from .....model.internal.instruction import SQL_INSTRUCTION_KIND


@dataclass(frozen=True, slots=True)
class DuckDbSqlEmitter:
    """Emit a DuckDB SQL instruction from an engine-neutral relation plan."""

    kind: str = SQL_INSTRUCTION_KIND
    instruction_emitter: Any = None

    def emit(self, plan: Any, context: Any = None) -> InstructionDTO:
        """Render one relation plan as DuckDB SQL and wrap it as an instruction."""
        from ...._private.instructions import duckdb

        if self.instruction_emitter is None:
            emitter = duckdb.DuckDbSqlEmitter(kind=self.kind)
        else:
            emitter = duckdb.DuckDbSqlEmitter(
                kind=self.kind,
                instruction_emitter=self.instruction_emitter,
            )
        return emitter.emit(plan, context)


__all__ = ["DuckDbSqlEmitter"]
