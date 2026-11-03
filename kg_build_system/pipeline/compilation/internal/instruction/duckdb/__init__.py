"""DuckDB SQL instruction and emitter interface.

The implementation lives in ``_private.instructions.duckdb``; this package keeps
the internal import path stable and exposes the thin instruction wrapper.
"""
from __future__ import annotations

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
from .instruction import DuckDbSqlEmitter

__all__ = [
    "ARRAY_CANONICAL",
    "ArraySqlType",
    "CANONICAL_SQL_TYPES",
    "CanonicalDigest",
    "CanonicalTypeName",
    "DEFAULT_EMITTER",
    "DIGEST_TABLE",
    "DeclaredOnlyDigest",
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
