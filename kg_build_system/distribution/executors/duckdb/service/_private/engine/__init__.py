"""The DuckDB implementation of the relation service and engine session."""
from __future__ import annotations

from .facts import (
    NULL_GUARD_MACRO,
    NULL_GUARD_MACRO_SQL,
    PARQUET_LIST_WRAPPER_PATH,
    PARQUET_LIST_WRAPPERS,
    NullStatistic,
    NullStatisticReport,
    ParquetSchemaRow,
    RowReader,
)
from .parquet_metadata import (
    read_declared_null_statistics,
    read_parquet_schema_rows,
)
from .service import DuckDBRelationService, configure_framework_macros
from .session import (
    PINNED_TIME_ZONE,
    DuckDbSettings,
    EngineSession,
    engine_session,
    open_engine,
)

__all__ = [
    "DuckDBRelationService",
    "DuckDbSettings",
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
    "open_engine",
    "read_declared_null_statistics",
    "read_parquet_schema_rows",
]
