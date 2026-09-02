"""DuckDB lowering and engine-specific SQL facilities."""

from .lowering import lower_relation_sql
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

__all__ = [
    "NULL_GUARD_MACRO",
    "NULL_GUARD_MACRO_SQL",
    "PARQUET_LIST_WRAPPER_PATH",
    "PARQUET_LIST_WRAPPERS",
    "NullStatistic",
    "NullStatisticReport",
    "ParquetSchemaRow",
    "RowReader",
    "lower_relation_sql",
    "read_declared_null_statistics",
    "read_parquet_schema_rows",
]
