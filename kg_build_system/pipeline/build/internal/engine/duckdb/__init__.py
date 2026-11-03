"""The DuckDB implementation of the build's relation service and engine session.

The service, framework macros and Parquet metadata readers are import-safe on
their own. The session opens a live database and therefore imports the build
runtime lazily.
"""
from __future__ import annotations

from typing import Any

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

__all__ = [
    "DuckDBRelationService",
    "NULL_GUARD_MACRO",
    "NULL_GUARD_MACRO_SQL",
    "NullStatistic",
    "NullStatisticReport",
    "PARQUET_LIST_WRAPPER_PATH",
    "PARQUET_LIST_WRAPPERS",
    "ParquetSchemaRow",
    "RowReader",
    "configure_framework_macros",
    "read_declared_null_statistics",
    "read_parquet_schema_rows",
]


def __getattr__(name: str) -> Any:
    if name in {"EngineSession", "PINNED_TIME_ZONE", "engine_session"}:
        from . import session

        return getattr(session, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
