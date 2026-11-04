"""Public DuckDB executor surface.

The emitter and executor implementations live in the package's private zone;
each function here is a thin delegation kept on the public service path.
"""
from __future__ import annotations

from kg_build_system.distribution.service.internal.relations import (
    RelationService,
)

from ...model.public import (
    RelationQueryResult,
    RelationRef,
    canonical_sql_type,
)
from ..internal import (
    ArraySqlType,
    DuckDbExecutor,
    DuckDbInstructionEmitter,
    DuckDbResourceProvider,
    DuckDbService,
    DuckDbSqlEmitter,
    EmissionContext,
    ExpressionEmitter,
    Operand,
    RelationPlan,
    SqlType,
)
from .functions import expression_sql, relation_sql, row_source_sql

__all__ = [
    "ArraySqlType",
    "DuckDbExecutor",
    "DuckDbInstructionEmitter",
    "DuckDbResourceProvider",
    "DuckDbService",
    "DuckDbSqlEmitter",
    "EmissionContext",
    "ExpressionEmitter",
    "Operand",
    "RelationQueryResult",
    "RelationRef",
    "RelationService",
    "SqlType",
    "canonical_sql_type",
    "expression_sql",
    "relation_sql",
    "row_source_sql",
]
