"""Framework-internal DuckDB facts used by distribution compilers.

The macro name, its SQL text and the Parquet list convention are data; the
footer readers are thin wrappers over the private engine implementation.
"""
from __future__ import annotations

from collections.abc import Sequence

from .....model.internal.engine import (
    NULL_GUARD_MACRO,
    NULL_GUARD_MACRO_SQL,
    PARQUET_LIST_WRAPPER_PATH,
    PARQUET_LIST_WRAPPERS,
    NullStatistic,
    NullStatisticReport,
    ParquetSchemaRow,
    RowReader,
)


def read_parquet_schema_rows(
    read: RowReader, sources: Sequence[str],
) -> tuple[ParquetSchemaRow, ...]:
    """Return every Parquet schema node of every source file."""
    from ...._private.engine.duckdb.parquet_metadata import (
        read_parquet_schema_rows as implementation,
    )

    return implementation(read, sources)


def read_declared_null_statistics(
    read: RowReader, sources: Sequence[str], schema_paths: Sequence[str],
) -> NullStatisticReport:
    """Read ``stats_null_count`` for the given paths from file footers only."""
    from ...._private.engine.duckdb.parquet_metadata import (
        read_declared_null_statistics as implementation,
    )

    return implementation(read, sources, schema_paths)


__all__ = [
    "NULL_GUARD_MACRO",
    "NULL_GUARD_MACRO_SQL",
    "NullStatistic",
    "NullStatisticReport",
    "PARQUET_LIST_WRAPPER_PATH",
    "PARQUET_LIST_WRAPPERS",
    "ParquetSchemaRow",
    "RowReader",
    "read_declared_null_statistics",
    "read_parquet_schema_rows",
]
