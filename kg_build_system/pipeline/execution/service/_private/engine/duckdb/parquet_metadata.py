"""DuckDB Parquet-metadata reads: what a file declares, and what it counts.

These are DuckDB table functions, so they live with the engine that provides
them. Nothing here reads a data row — ``read_parquet`` stays the only reader of
rows — and nothing here knows who is calling. A caller supplies a read-only
query function, so an edit-time provider passing a DuckDB connection and a build
passing a workflow relation service are both just ways of running a statement.
"""

from __future__ import annotations

from collections.abc import Sequence

from .....model.internal.engine import (
    PARQUET_LIST_WRAPPER_PATH,
    PARQUET_LIST_WRAPPERS,
    NullStatistic,
    NullStatisticReport,
    ParquetSchemaRow,
    RowReader,
)

__all__ = [
    "PARQUET_LIST_WRAPPER_PATH",
    "PARQUET_LIST_WRAPPERS",
    "NullStatistic",
    "NullStatisticReport",
    "ParquetSchemaRow",
    "RowReader",
    "read_declared_null_statistics",
    "read_parquet_schema_rows",
]


def read_parquet_schema_rows(
    read: RowReader, sources: Sequence[str],
) -> tuple[ParquetSchemaRow, ...]:
    """Return every Parquet schema node of every source file.

    One row set per file, in pre-order depth-first order keyed on ``column_id``:
    ``file_name``, ``name``, ``repetition_type``, ``type``, ``num_children``,
    ``duckdb_type``, ``column_id``.
    """
    query = (
        "SELECT file_name, name, repetition_type, type, num_children, duckdb_type, column_id "
        "FROM parquet_schema(?) ORDER BY file_name, column_id"
    )
    return tuple(
        (
            str(row[0]), str(row[1]), str(row[2]),
            None if row[3] is None else str(row[3]),
            None if row[4] is None else int(row[4]),
            None if row[5] is None else str(row[5]),
            int(row[6]),
        )
        for row in read(query, [list(sources)])
    )


def read_declared_null_statistics(
    read: RowReader, sources: Sequence[str], schema_paths: Sequence[str],
) -> NullStatisticReport:
    """Read ``stats_null_count`` for the given paths from file footers only.

    A path the writer never reported statistics for is returned as unknown; an
    absent statistic tests nothing and must never be read as a zero count.
    """
    if not schema_paths:
        return NullStatisticReport()
    query = (
        "WITH reported AS ("
        "  SELECT path_in_schema AS schema_path,"
        "         sum(num_values) AS value_count,"
        "         sum(stats_null_count) FILTER (WHERE stats_null_count IS NOT NULL)"
        "             AS null_count,"
        "         count(*) FILTER (WHERE stats_null_count IS NULL) AS missing"
        "  FROM parquet_metadata(?)"
        "  WHERE path_in_schema IN (SELECT UNNEST(?::VARCHAR[]))"
        "  GROUP BY path_in_schema"
        ")"
        "SELECT p.path, r.value_count, r.null_count, r.missing "
        "FROM (SELECT UNNEST(?::VARCHAR[]) AS path) AS p "
        "LEFT JOIN reported r ON r.schema_path = p.path"
    )
    parameters: list[object] = [list(sources), list(schema_paths), list(schema_paths)]
    statistics: list[NullStatistic] = []
    unknown: list[str] = []
    for path, values, nulls, missing in read(query, parameters):
        if values is None or nulls is None or missing:
            unknown.append(str(path))
            continue
        statistics.append(NullStatistic(str(path), int(values), int(nulls)))
    return NullStatisticReport(tuple(statistics), tuple(unknown))
