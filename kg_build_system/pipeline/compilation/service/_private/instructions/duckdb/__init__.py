"""DuckDB SQL emission.

The package holds the only code that constructs DuckDB SQL from the
engine-neutral expression and relation plans. Its author-facing instruction
wrapper is :class:`DuckDbSqlEmitter`; the registry-backed implementation is
:class:`DuckDbInstructionEmitter`.
"""
from __future__ import annotations

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
from .....model._private.sql_types import (
    ARRAY_CANONICAL,
    CANONICAL_SQL_TYPES,
    DIGEST_TABLE,
    EXTENSION_CONDITIONAL_TYPE_NAMES,
    STRUCT_CANONICAL,
    TYPE_NAME_ALIASES,
    ArraySqlType,
    CanonicalDigest,
    CanonicalTypeName,
    DeclaredOnlyDigest,
    DigestDisposition,
    RefusedDigest,
    SqlType,
    StructSqlType,
    TypeDigest,
    canonical_sql_type,
    canonical_type_name,
    digest_for,
)

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
