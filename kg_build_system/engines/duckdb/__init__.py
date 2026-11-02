"""DuckDB lowering, type mapping, macros, metadata and relation service.

This package is the only place that imports SQL construction or a concrete
database. Its public-internal names are re-exported through
:mod:`kg_build_system.engines.interfaces`.
"""
from __future__ import annotations

from .engine import (
    DEFAULT_ENGINE,
    DEFAULT_LOWERING,
    DuckDBEngine,
    DuckDBLowering,
    lower_expression,
    lower_expression_sql,
    lower_plan,
    lower_relation_sql,
    lower_row_source,
    lower_row_source_sql,
)
from .macros import NULL_GUARD_MACRO, NULL_GUARD_MACRO_SQL
from .parquet_metadata import (
    PARQUET_LIST_WRAPPER_PATH,
    PARQUET_LIST_WRAPPERS,
    NullStatistic,
    NullStatisticReport,
    ParquetSchemaRow,
    RowReader,
    read_declared_null_statistics,
    read_parquet_schema_rows,
)
from .service import DuckDBRelationService, configure_framework_macros
from .sql import SqlNode
from .types import (
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
    "DEFAULT_ENGINE",
    "DEFAULT_LOWERING",
    "DIGEST_TABLE",
    "DeclaredOnlyDigest",
    "DigestDisposition",
    "DuckDBEngine",
    "DuckDBLowering",
    "DuckDBRelationService",
    "EXTENSION_CONDITIONAL_TYPE_NAMES",
    "NULL_GUARD_MACRO",
    "NULL_GUARD_MACRO_SQL",
    "NullStatistic",
    "NullStatisticReport",
    "PARQUET_LIST_WRAPPER_PATH",
    "PARQUET_LIST_WRAPPERS",
    "ParquetSchemaRow",
    "RefusedDigest",
    "RowReader",
    "STRUCT_CANONICAL",
    "SqlNode",
    "SqlType",
    "StructSqlType",
    "TYPE_NAME_ALIASES",
    "TypeDigest",
    "canonical_sql_type",
    "canonical_type_name",
    "configure_framework_macros",
    "digest_for",
    "lower_expression",
    "lower_expression_sql",
    "lower_plan",
    "lower_relation_sql",
    "lower_row_source",
    "lower_row_source_sql",
    "read_declared_null_statistics",
    "read_parquet_schema_rows",
]
