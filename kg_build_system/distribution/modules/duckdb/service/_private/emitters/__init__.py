"""DuckDB SQL emission.

The package holds the only code that constructs DuckDB SQL from the
engine-neutral expression and relation plans. Its author-facing instruction
wrapper is :class:`DuckDbSqlEmitter`; the registry-backed implementation is
:class:`DuckDbInstructionEmitter`.
"""
from __future__ import annotations

from .protocols import (
    EmissionContext,
    ExpressionEmitter,
    Operand,
    RowSourceEmissionContext,
    RowSourceEmitter,
)
from .emitter import (
    DEFAULT_EMITTER,
    DuckDbInstructionEmitter,
    emit_expression,
    emit_row_source,
    expression_sql,
    relation_sql,
    row_source_sql,
)
from .instruction import DuckDbSqlEmitter
from .sql import SqlNode

__all__ = [
    "DEFAULT_EMITTER",
    "DuckDbInstructionEmitter",
    "DuckDbSqlEmitter",
    "EmissionContext",
    "ExpressionEmitter",
    "Operand",
    "RowSourceEmissionContext",
    "RowSourceEmitter",
    "SqlNode",
    "emit_expression",
    "emit_row_source",
    "expression_sql",
    "relation_sql",
    "row_source_sql",
]
