"""DuckDB observations: relations, described columns and Parquet metadata.

Nothing here reads a data row for inference. ``DESCRIBE`` decides structure,
``parquet_schema()`` decides nested shape and repetition, and
``parquet_metadata()`` supplies footer statistics.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

import duckdb

from ...internal.generated import Nullability
from ...internal.models import GenerationError
from .formats import (
    DATABASE_SUFFIXES, PARQUET_SUFFIXES, remote_source, source_stem, source_suffix,
    tier_for_suffix,
)
from .nullability import describe_nullability

RowReader = Callable[[str, Sequence[object]], Sequence[Sequence[Any]]]
ParquetSchemaRow = tuple[str, str, str, str | None, int | None, str | None, int]


@dataclass(frozen=True, slots=True)
class DescribedColumn:
    name: str
    type_name: str
    nullability: Nullability


@dataclass(frozen=True, slots=True)
class NullStatistic:
    """One declared path's null count, summed over files and row groups."""

    schema_path: str
    values: int
    nulls: int


@dataclass(frozen=True, slots=True)
class NullStatisticReport:
    statistics: tuple[NullStatistic, ...] = ()
    unknown_paths: tuple[str, ...] = ()

    @property
    def violations(self) -> tuple[NullStatistic, ...]:
        return tuple(item for item in self.statistics if item.nulls > 0)


def connect() -> duckdb.DuckDBPyConnection:
    """One in-memory observation connection."""
    return duckdb.connect(":memory:")


def reader(connection: duckdb.DuckDBPyConnection) -> RowReader:
    """Adapt a DuckDB connection to the read-only query contract."""

    def read(query: str, parameters: Sequence[object]) -> Sequence[Sequence[Any]]:
        return connection.execute(query, list(parameters)).fetchall()

    return read


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def relations(connection: duckdb.DuckDBPyConnection, source: str) -> tuple[str, ...]:
    """The relations a database input exposes, or the file's own stem."""
    if source_suffix(source) not in DATABASE_SUFFIXES:
        return (source_stem(source),)
    rows = connection.execute(
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema NOT IN ('information_schema', 'pg_catalog') ORDER BY table_name"
    ).fetchall()
    return tuple(str(row[0]) for row in rows)


def describe(
    connection: duckdb.DuckDBPyConnection,
    sources: tuple[str, ...],
    relation: str,
    *,
    hive_partitioned: bool = False,
) -> tuple[DescribedColumn, ...]:
    """Structure and tier-decided nullability for one relation's columns.

    ``DESCRIBE`` is the structural boundary — it decides which columns exist
    and what scalar each holds. Its ``null`` column reports only *enforced*
    catalog constraints, so it is silent about what a file declares, and
    nullability is therefore decided by tier rather than read off it directly.
    Nullability is never derived from observed values.
    """
    source = sources[0]
    suffix = source_suffix(source)
    if suffix in DATABASE_SUFFIXES:
        query = f"SELECT * FROM {_quote_identifier(relation)}"
        parameters: list[Any] = []
    elif suffix in PARQUET_SUFFIXES:
        query = (
            "SELECT * FROM read_parquet(?, hive_partitioning = true)"
            if hive_partitioned else "SELECT * FROM read_parquet(?)"
        )
        parameters = [source if len(sources) == 1 else list(sources)]
    elif suffix in {".csv", ".tsv"}:
        query, parameters = "SELECT * FROM read_csv_auto(?)", [source if len(sources) == 1 else list(sources)]
    elif suffix in {".json", ".jsonl", ".ndjson"}:
        query, parameters = "SELECT * FROM read_json_auto(?)", [source if len(sources) == 1 else list(sources)]
    else:
        raise GenerationError(f"unsupported data-contract inference input format {suffix or '<none>'!r}")
    try:
        rows = connection.execute(f"DESCRIBE {query}", parameters).fetchall()
    except duckdb.Error as error:
        raise GenerationError(
            f"cannot infer schema for {source} relation {relation!r}: {error}"
        ) from error
    tier = tier_for_suffix(suffix)
    return tuple(
        DescribedColumn(
            str(row[0]), str(row[1]),
            describe_nullability(tier, str(row[2]).upper() != "NO"),
        )
        for row in rows
    )


def load_remote_access(connection: duckdb.DuckDBPyConnection, source: str) -> None:
    """Enable DuckDB's URL and S3 filesystem support when a remote input needs it."""
    if not remote_source(source):
        return
    try:
        connection.execute("LOAD httpfs")
    except duckdb.Error:
        try:
            connection.execute("INSTALL httpfs")
            connection.execute("LOAD httpfs")
        except duckdb.Error as error:
            raise GenerationError(
                f"cannot enable DuckDB httpfs support required for remote source {source!r}: {error}"
            ) from error


def parquet_schema_rows(
    connection: duckdb.DuckDBPyConnection, sources: Sequence[str],
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
        for row in reader(connection)(query, [list(sources)])
    )


def declared_null_statistics(
    connection: duckdb.DuckDBPyConnection,
    sources: Sequence[str],
    schema_paths: Sequence[str],
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
    for path, values, nulls, missing in reader(connection)(query, parameters):
        if values is None or nulls is None or missing:
            unknown.append(str(path))
            continue
        statistics.append(NullStatistic(str(path), int(values), int(nulls)))
    return NullStatisticReport(tuple(statistics), tuple(unknown))


__all__ = [
    "DescribedColumn", "NullStatistic", "NullStatisticReport", "ParquetSchemaRow",
    "RowReader", "connect", "declared_null_statistics", "describe", "load_remote_access",
    "parquet_schema_rows", "reader", "relations",
]
