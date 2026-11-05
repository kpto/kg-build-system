"""Public DuckDB model: relation protocols and the type digest gate."""
from __future__ import annotations

from .relations import RelationQueryResult, RelationRef
from .sql_types import (
    ARRAY_CANONICAL,
    DIGEST_TABLE,
    EXTENSION_CONDITIONAL_TYPE_NAMES,
    STRUCT_CANONICAL,
    TYPE_NAME_ALIASES,
    CanonicalDigest,
    CanonicalTypeName,
    DeclaredOnlyDigest,
    DigestDisposition,
    RefusedDigest,
    TypeDigest,
    canonical_type_name,
    digest_for,
)

__all__ = [
    "ARRAY_CANONICAL",
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
    "TYPE_NAME_ALIASES",
    "TypeDigest",
    "canonical_type_name",
    "digest_for",
]
