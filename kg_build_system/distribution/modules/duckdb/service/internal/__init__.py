"""Internal emitter and engine interface shared with sibling packages."""
from __future__ import annotations

from .api import DuckDbExecutor, DuckDbResourceProvider, DuckDbService
from .emitters import (
    DEFAULT_EMITTER,
    DuckDbInstructionEmitter,
    DuckDbSqlEmitter,
    EmissionContext,
    ExpressionEmitter,
    NULL_GUARD_MACRO,
    Operand,
    PARQUET_LIST_WRAPPER_PATH,
    emit_expression,
    emit_row_source,
    expression_sql,
    read_declared_null_statistics,
    relation_sql,
    row_source_sql,
)

__all__ = [
    "DEFAULT_EMITTER",
    "DuckDbExecutor",
    "DuckDbInstructionEmitter",
    "DuckDbResourceProvider",
    "DuckDbService",
    "DuckDbSqlEmitter",
    "EmissionContext",
    "ExpressionEmitter",
    "NULL_GUARD_MACRO",
    "Operand",
    "PARQUET_LIST_WRAPPER_PATH",
    "emit_expression",
    "emit_row_source",
    "expression_sql",
    "read_declared_null_statistics",
    "relation_sql",
    "row_source_sql",
]
