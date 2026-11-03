"""Stable internal path for DuckDB engine facts.

Distribution compilers import the framework macro name, the Parquet list
wrapper path and the footer readers from here. The implementation lives in the
build package's private zone; this module only delegates.
"""
from __future__ import annotations

from ...._private.engine.duckdb import (
    DuckDBRelationService,
    NULL_GUARD_MACRO,
    NULL_GUARD_MACRO_SQL,
    NullStatistic,
    NullStatisticReport,
    PARQUET_LIST_WRAPPER_PATH,
    PARQUET_LIST_WRAPPERS,
    ParquetSchemaRow,
    RowReader,
    configure_framework_macros,
    read_declared_null_statistics,
    read_parquet_schema_rows,
)
from ...._private.engine.duckdb.session import (
    EngineSession,
    PINNED_TIME_ZONE,
    engine_session,
)

__all__ = [
    "DuckDBRelationService",
    "EngineSession",
    "NULL_GUARD_MACRO",
    "NULL_GUARD_MACRO_SQL",
    "NullStatistic",
    "NullStatisticReport",
    "PARQUET_LIST_WRAPPER_PATH",
    "PARQUET_LIST_WRAPPERS",
    "PINNED_TIME_ZONE",
    "ParquetSchemaRow",
    "RowReader",
    "configure_framework_macros",
    "engine_session",
    "read_declared_null_statistics",
    "read_parquet_schema_rows",
]
