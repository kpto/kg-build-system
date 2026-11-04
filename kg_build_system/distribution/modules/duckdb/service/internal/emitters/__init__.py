"""Internal emitter interface shared with sibling distribution packages."""
from __future__ import annotations

from ..._private.emitters import (
    DEFAULT_EMITTER,
    ArraySqlType,
    DuckDbInstructionEmitter,
    DuckDbSqlEmitter,
    EmissionContext,
    ExpressionEmitter,
    Operand,
    SqlType,
    canonical_sql_type,
    emit_expression,
    emit_row_source,
    expression_sql,
    relation_sql,
    row_source_sql,
)
from ..._private.emitters.plan import Expand, Filter, RelationPlan, Scan
from ..._private.engine.facts import NULL_GUARD_MACRO, PARQUET_LIST_WRAPPER_PATH
from ..._private.engine.parquet_metadata import read_declared_null_statistics

__all__ = [
    "DEFAULT_EMITTER",
    "ArraySqlType",
    "DuckDbInstructionEmitter",
    "DuckDbSqlEmitter",
    "EmissionContext",
    "Expand",
    "ExpressionEmitter",
    "Filter",
    "NULL_GUARD_MACRO",
    "Operand",
    "PARQUET_LIST_WRAPPER_PATH",
    "RelationPlan",
    "Scan",
    "SqlType",
    "canonical_sql_type",
    "emit_expression",
    "emit_row_source",
    "expression_sql",
    "read_declared_null_statistics",
    "relation_sql",
    "row_source_sql",
]
