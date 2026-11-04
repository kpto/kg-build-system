"""Engine facts shared by the build interface and the DuckDB implementation.

The macro names, their SQL text and the Parquet list convention are data: a
distribution compiler and the build engine must name the same fact. The
metadata value types are the shape the footer readers return.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any

__all__ = [
    "NULL_GUARD_MACRO",
    "NULL_GUARD_MACRO_SQL",
    "PARQUET_LIST_WRAPPER_PATH",
    "PARQUET_LIST_WRAPPERS",
    "NullStatistic",
    "NullStatisticReport",
    "ParquetSchemaRow",
    "RowReader",
]

#: Aborts with ``msg`` when a value is null. Emitted bindings wrap every non-null
#: output in it, so a violated contract claim stops a build instead of emitting a
#: value the contract forbids.
NULL_GUARD_MACRO = "_kg_nn"

#: Idempotent and namespaced: macro names are database-scoped, and a disk build
#: opens a fresh database per run.
NULL_GUARD_MACRO_SQL = (
    f"CREATE OR REPLACE MACRO {NULL_GUARD_MACRO}(v, msg := 'unexpected NULL') AS "
    "CASE WHEN v IS NULL THEN error(msg) ELSE v END"
)

#: Runs one read-only statement and returns its rows.
RowReader = Callable[[str, Sequence[object]], Sequence[Sequence[Any]]]

ParquetSchemaRow = tuple[str, str, str, str | None, int | None, str | None, int]

#: The Parquet three-level list convention wraps an array in a repeated ``list``
#: group holding one ``element``, and ``path_in_schema`` reports both names. A
#: logical path drops them, a schema path carries one pair per array level, so
#: both readings of a path are written from this one fact.
PARQUET_LIST_WRAPPERS = frozenset({"list", "element"})
PARQUET_LIST_WRAPPER_PATH: tuple[str, str] = ("list", "element")


@dataclass(frozen=True, slots=True)
class NullStatistic:
    """One declared path's null count, summed over files and row groups.

    ``values`` and ``nulls`` are counts the writer chose to publish. A path with
    no published statistic appears in ``unknown_paths``, never as a zero.
    """

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
