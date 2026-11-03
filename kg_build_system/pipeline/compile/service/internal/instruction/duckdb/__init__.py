"""DuckDB SQL instruction and emitter interface.

The implementation lives in ``service._private.instructions.duckdb``; this
package keeps the internal import path stable and exposes the thin instruction
wrapper. Private emitter bodies are loaded lazily so this interface imports
``service._private`` only inside a function.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .instruction import DuckDbSqlEmitter

if TYPE_CHECKING:
    from ...._private.instructions.duckdb import (
        ARRAY_CANONICAL,
        CANONICAL_SQL_TYPES,
        DEFAULT_EMITTER,
        DIGEST_TABLE,
        EXTENSION_CONDITIONAL_TYPE_NAMES,
        STRUCT_CANONICAL,
        TYPE_NAME_ALIASES,
        ArraySqlType,
        CanonicalDigest,
        CanonicalTypeName,
        DeclaredOnlyDigest,
        DigestDisposition,
        DuckDbInstructionEmitter,
        EmissionContext,
        ExpressionEmitter,
        Operand,
        RefusedDigest,
        SqlType,
        StructSqlType,
        TypeDigest,
        canonical_sql_type,
        canonical_type_name,
        digest_for,
        emit_expression,
        emit_row_source,
        expression_sql,
        relation_sql,
        row_source_sql,
    )

_PRIVATE_NAMES = {
    "ARRAY_CANONICAL",
    "ArraySqlType",
    "CANONICAL_SQL_TYPES",
    "CanonicalDigest",
    "CanonicalTypeName",
    "DEFAULT_EMITTER",
    "DIGEST_TABLE",
    "DeclaredOnlyDigest",
    "EmissionContext",
    "ExpressionEmitter",
    "Operand",
    "DigestDisposition",
    "DuckDbInstructionEmitter",
    "EXTENSION_CONDITIONAL_TYPE_NAMES",
    "RefusedDigest",
    "STRUCT_CANONICAL",
    "SqlType",
    "StructSqlType",
    "TYPE_NAME_ALIASES",
    "TypeDigest",
    "canonical_sql_type",
    "canonical_type_name",
    "digest_for",
    "emit_expression",
    "emit_row_source",
    "expression_sql",
    "relation_sql",
    "row_source_sql",
}

__all__ = [
    "ARRAY_CANONICAL",
    "ArraySqlType",
    "CANONICAL_SQL_TYPES",
    "CanonicalDigest",
    "CanonicalTypeName",
    "DEFAULT_EMITTER",
    "DIGEST_TABLE",
    "DeclaredOnlyDigest",
    "EmissionContext",
    "ExpressionEmitter",
    "Operand",
    "DigestDisposition",
    "DuckDbInstructionEmitter",
    "DuckDbSqlEmitter",
    "EXTENSION_CONDITIONAL_TYPE_NAMES",
    "RefusedDigest",
    "STRUCT_CANONICAL",
    "SqlType",
    "StructSqlType",
    "TYPE_NAME_ALIASES",
    "TypeDigest",
    "canonical_sql_type",
    "canonical_type_name",
    "digest_for",
    "emit_expression",
    "emit_row_source",
    "expression_sql",
    "relation_sql",
    "row_source_sql",
]


def __getattr__(name: str):
    if name not in _PRIVATE_NAMES:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    from ...._private.instructions import duckdb

    return getattr(duckdb, name)
