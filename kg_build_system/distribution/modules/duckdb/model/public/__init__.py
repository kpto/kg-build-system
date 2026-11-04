"""Public DuckDB model: relation protocols and canonical SQL types."""
from __future__ import annotations

from .relations import RelationQueryResult, RelationRef
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
    "RelationQueryResult",
    "RelationRef",
    "STRUCT_CANONICAL",
    "SqlType",
    "StructSqlType",
    "TYPE_NAME_ALIASES",
    "TypeDigest",
    "canonical_sql_type",
    "canonical_type_name",
    "digest_for",
]
