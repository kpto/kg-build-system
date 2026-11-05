"""Public DuckDB executor surface.

The emitter and executor implementations live in the package's private zone;
each function here is a thin delegation kept on the public service path.
"""
from __future__ import annotations

from kg_build_system.distribution.service.internal.relations import (
    RelationService,
)

from ...model.public import RelationQueryResult, RelationRef
from ..internal import (
    DuckDbExecutor,
    DuckDbInstructionEmitter,
    DuckDbResourceProvider,
    DuckDbService,
    DuckDbSqlEmitter,
    EmissionContext,
    ExpressionEmitter,
    Operand,
)
from .functions import expression_sql, relation_sql, row_source_sql
from .planner import DuckDbSourcePlanner

__all__ = [
    "DuckDbExecutor",
    "DuckDbInstructionEmitter",
    "DuckDbResourceProvider",
    "DuckDbService",
    "DuckDbSourcePlanner",
    "DuckDbSqlEmitter",
    "EmissionContext",
    "ExpressionEmitter",
    "Operand",
    "RelationQueryResult",
    "RelationRef",
    "RelationService",
    "expression_sql",
    "relation_sql",
    "row_source_sql",
]
