"""Private model data of the compilation package.

SQL types are render data: the engine-neutral plan names none of them, while the
DuckDB instruction emitter reads them.
"""
from __future__ import annotations

from .sql_types import (
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
    "DIGEST_TABLE",
    "DeclaredOnlyDigest",
    "DigestDisposition",
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
]
