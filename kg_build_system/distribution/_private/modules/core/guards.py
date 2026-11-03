"""The source-shape checks and declared-null statistics pre-flight.

These checks test the contract against the physical source before a consumer
reads a row. Neither sets a claim: a missing column is a shape failure, a null
count is a warning, and the binding guard remains the enforcement point.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .....pipeline.build.internal.engine.duckdb import (
    read_declared_null_statistics,
)
from .....pipeline.compilation.internal.instruction.duckdb import (
    canonical_sql_type,
)
from ....internal.dto.instruction_dto import (
    DeclaredColumnDTO,
    SourceRelationInstructionDTO,
)
from ...dto.instruction_codec import declared_column_type
from .relations import sql_type_for


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def widened_column(column: DeclaredColumnDTO) -> str:
    """One select item of a source view: the declared column, widened in place.

    The alias repeats the column's own name, so widening the type cannot rename
    anything — the declared-column check and every emitted expression still
    reach the column by the name the contract declares.
    """
    name = _quote_identifier(column.name)
    sql_type = sql_type_for(declared_column_type(column))
    if sql_type is None:
        return name
    return f"CAST({name} AS {canonical_sql_type(sql_type)}) AS {name}"


def require_declared_columns(
    instruction: SourceRelationInstructionDTO,
    scan: str,
    services: Any,
) -> None:
    """Check the contract's declared fields against the relation, before use.

    A missing column otherwise surfaces much later as a DuckDB binder error
    naming candidate columns from the file, and a source whose declared format
    does not match its bytes fails mid-execution in DuckDB's vocabulary. Both
    are framework facts — a declaration and a location — so both are reported
    here, in framework terms, while nothing has yet read a row.

    The scan is described rather than the view built over it: a declared column
    the file does not have would otherwise fail the widening cast's own binding,
    where DuckDB reads it as a self-reference and blames the alias.
    """
    if not instruction.declared_columns:
        return
    query = f"DESCRIBE SELECT * FROM {scan}"
    try:
        columns = {
            str(row[0])
            for row in services.relations.query(query).fetchall()
        }
    except Exception as error:
        raise RuntimeError(
            f"the shape of the source at '{instruction.location}' for "
            f"'{instruction.declaration}' cannot be read as the declared "
            f"'{instruction.format}' format: {error}"
        ) from error
    missing = [
        column.name for column in instruction.declared_columns
        if column.name not in columns
    ]
    if missing:
        raise RuntimeError(
            f"declared field(s) {', '.join(repr(name) for name in missing)} are "
            f"absent from '{instruction.location}' for "
            f"'{instruction.declaration}'; the source exposes "
            f"{', '.join(sorted(map(repr, columns))) or 'no columns'}"
        )


def report_declared_null_statistics(
    instruction: SourceRelationInstructionDTO,
    services: Any,
) -> bool:
    """Count nulls behind a declared non-null claim, from file footers only.

    A statistic tests a claim, it never sets or enforces one, so this reports
    and never fails: enforcement belongs to the guard at the point of use. A
    path with no published statistic is unknown, which is not the same as zero.
    """
    if instruction.format != "parquet" or not instruction.declared_paths:
        return False

    def read(query: str, parameters: Sequence[object]) -> list[tuple[Any, ...]]:
        return list(services.relations.query(query, parameters).fetchall())

    try:
        report = read_declared_null_statistics(
            read,
            (instruction.location,),
            [path.schema_path for path in instruction.declared_paths],
        )
    except Exception as error:
        services.logger.warning(
            "could not read null statistics from %s: %s",
            instruction.location, error,
        )
        return False
    logical = {
        path.schema_path: path.logical_path for path in instruction.declared_paths
    }
    for statistic in report.violations:
        services.logger.warning(
            "%s reports %d null value(s) in %d rows for the declared non-null "
            "column %r; the guard will abort the build unless the contract changes",
            instruction.location, statistic.nulls, statistic.values,
            logical.get(statistic.schema_path, statistic.schema_path),
        )
    for path in report.unknown_paths:
        services.logger.debug(
            "no null statistics published for %r; unknown is not zero", path,
        )
    return bool(report.violations)


__all__ = [
    "report_declared_null_statistics",
    "require_declared_columns",
    "widened_column",
]
