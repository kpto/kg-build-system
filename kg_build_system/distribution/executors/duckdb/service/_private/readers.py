"""Read one physical source and expose its widened relation.

The source instruction owns a declaration and a location; this module turns that
declaration into a typed view over the engine scan, checks the declared columns
before any consumer reads a row, and reports declared-null statistics as a
warning. It never sets a null claim: the binding guard remains the enforcement
point.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, JsonValue

from kg_build_system.kernel.model.internal.types.dto import (
    ArrayTypeDTO,
    LogicalTypeDTO,
    NullableTypeDTO,
    UnitTypeDTO,
)
from kg_build_system.kernel.service.internal.types import type_from_document

from ...model.public.sql_types import ArraySqlType, SqlType, canonical_sql_type
from ...service._private.engine.parquet_metadata import (
    read_declared_null_statistics,
)

_SCAN_FUNCTIONS = {
    "csv": "read_csv_auto",
    "json": "read_json_auto",
    "parquet": "read_parquet",
}


@dataclass(frozen=True, slots=True)
class DeclaredColumn:
    """One declared top-level field, with the type it is declared to hold."""

    name: str
    logical_type: LogicalTypeDTO


@dataclass(frozen=True, slots=True)
class DeclaredPath:
    """One declared member path, in both forms the source step needs."""

    schema_path: str
    logical_path: str


@dataclass(frozen=True, slots=True)
class SourceSpec:
    """The declaration and location carried by one source instruction."""

    relation: str
    location: str
    format: Literal["csv", "json", "parquet"]
    credential_reference: str | None = None
    declaration: str = ""
    declared_columns: tuple[DeclaredColumn, ...] = ()
    declared_paths: tuple[DeclaredPath, ...] = ()


class CoreSourceCredentialOptions(BaseModel):
    """Secret runtime options understood only by the core source reader."""

    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)

    filesystem_options: dict[str, JsonValue]


def _text(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ValueError(
            f"source instruction field {key!r} must be a non-empty string"
        )
    return item


def _optional_text(value: Mapping[str, Any], key: str) -> str | None:
    item = value.get(key)
    if item is None:
        return None
    if not isinstance(item, str) or not item:
        raise ValueError(
            f"source instruction field {key!r} must be a non-empty string"
        )
    return item


def _sequence(value: Any, key: str) -> tuple[Any, ...]:
    if value is None:
        return ()
    if isinstance(value, (list, tuple)):
        return tuple(value)
    raise ValueError(f"source instruction field {key!r} must be a sequence")


def _mapping(value: Any, key: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"source instruction field {key!r} must be an object")
    return value


def _declared_column(value: Any) -> DeclaredColumn:
    data = _mapping(value, "declared_columns")
    logical_type = dict(_mapping(data.get("logical_type"), "logical_type"))
    return DeclaredColumn(
        name=_text(data, "name"),
        logical_type=type_from_document(logical_type),
    )


def _declared_path(value: Any) -> DeclaredPath:
    data = _mapping(value, "declared_paths")
    return DeclaredPath(
        schema_path=_text(data, "schema_path"),
        logical_path=_text(data, "logical_path"),
    )


def source_spec(payload: Mapping[str, Any]) -> SourceSpec:
    """Read and validate the source fields of one instruction payload."""
    format_value = payload.get("format")
    if format_value not in {"csv", "json", "parquet"}:
        raise ValueError(f"unknown source format {format_value!r}")
    declaration = payload.get("declaration", "")
    if not isinstance(declaration, str):
        raise ValueError("source instruction field 'declaration' must be a string")
    return SourceSpec(
        relation=_text(payload, "relation"),
        location=_text(payload, "location"),
        format=format_value,
        credential_reference=_optional_text(payload, "credential_reference"),
        declaration=declaration,
        declared_columns=tuple(
            _declared_column(item)
            for item in _sequence(payload.get("declared_columns"), "declared_columns")
        ),
        declared_paths=tuple(
            _declared_path(item)
            for item in _sequence(payload.get("declared_paths"), "declared_paths")
        ),
    )


def source_scan(spec: SourceSpec) -> str:
    """The engine scan expression for one declared source."""
    scan_function = _SCAN_FUNCTIONS[spec.format]
    location = spec.location.replace("'", "''")
    return f"{scan_function}('{location}')"


def sql_type_for(declared: LogicalTypeDTO) -> SqlType | None:
    """The SQL shape one declared property type composes to, when it has one."""
    if isinstance(declared, NullableTypeDTO):
        return sql_type_for(declared.value)
    if isinstance(declared, UnitTypeDTO):
        return declared.name
    if isinstance(declared, ArrayTypeDTO):
        item = sql_type_for(declared.item)
        return None if item is None else ArraySqlType(item)
    return None


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def widened_column(column: DeclaredColumn) -> str:
    """One select item of a source view: the declared column, widened in place."""
    name = _quote_identifier(column.name)
    sql_type = sql_type_for(column.logical_type)
    if sql_type is None:
        return name
    return f"CAST({name} AS {canonical_sql_type(sql_type)}) AS {name}"


def _require_declared_columns(
    spec: SourceSpec,
    scan: str,
    services: Any,
) -> None:
    """Check the contract's declared fields against the relation, before use."""
    if not spec.declared_columns:
        return
    query = f"DESCRIBE SELECT * FROM {scan}"
    try:
        columns = {
            str(row[0])
            for row in services.relations.query(query).fetchall()
        }
    except Exception as error:
        raise RuntimeError(
            f"the shape of the source at '{spec.location}' for "
            f"'{spec.declaration}' cannot be read as the declared "
            f"'{spec.format}' format: {error}"
        ) from error
    missing = [
        column.name for column in spec.declared_columns
        if column.name not in columns
    ]
    if missing:
        raise RuntimeError(
            f"declared field(s) {', '.join(repr(name) for name in missing)} are "
            f"absent from '{spec.location}' for "
            f"'{spec.declaration}'; the source exposes "
            f"{', '.join(sorted(map(repr, columns))) or 'no columns'}"
        )


def _report_declared_null_statistics(
    spec: SourceSpec,
    services: Any,
) -> bool:
    """Count nulls behind a declared non-null claim, from file footers only."""
    if spec.format != "parquet" or not spec.declared_paths:
        return False

    def read(query: str, parameters: Sequence[object]) -> list[tuple[Any, ...]]:
        return list(services.relations.query(query, parameters).fetchall())

    try:
        report = read_declared_null_statistics(
            read,
            (spec.location,),
            [path.schema_path for path in spec.declared_paths],
        )
    except Exception as error:
        services.logger.warning(
            "could not read null statistics from %s: %s",
            spec.location, error,
        )
        return False
    logical = {
        path.schema_path: path.logical_path for path in spec.declared_paths
    }
    for statistic in report.violations:
        services.logger.warning(
            "%s reports %d null value(s) in %d rows for the declared non-null "
            "column %r; the guard will abort the build unless the contract changes",
            spec.location, statistic.nulls, statistic.values,
            logical.get(statistic.schema_path, statistic.schema_path),
        )
    for path in report.unknown_paths:
        services.logger.debug(
            "no null statistics published for %r; unknown is not zero", path,
        )
    return bool(report.violations)


def _thaw_json(value: JsonValue) -> Any:
    if isinstance(value, dict):
        return {key: _thaw_json(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_thaw_json(item) for item in value]
    return value


def _configure_source_credentials(
    services: Any,
    *,
    location: str,
    credential_reference: str,
) -> None:
    """Resolve and apply core-owned filesystem options for one source."""
    resolved = services.credentials.resolve(credential_reference)
    options = CoreSourceCredentialOptions.model_validate_json(resolved)
    protocol = urlsplit(location).scheme
    if not protocol:
        raise ValueError("credentialed source locations require a URI scheme")

    import fsspec

    filesystem = fsspec.filesystem(
        protocol,
        **_thaw_json(options.filesystem_options),
    )
    services.relations.register_filesystem(filesystem)


def open_source(spec: SourceSpec, services: Any) -> tuple[Any, bool]:
    """Create the source view and return it with whether statistics warned."""
    if spec.credential_reference is not None:
        _configure_source_credentials(
            services,
            location=spec.location,
            credential_reference=spec.credential_reference,
        )

    scan = source_scan(spec)
    _require_declared_columns(spec, scan, services)
    select = ", ".join(
        widened_column(column) for column in spec.declared_columns
    ) or "*"
    sql = f"SELECT {select} FROM {scan}"
    try:
        relation = services.relations.view(spec.relation, sql)
    except Exception as error:
        raise RuntimeError(
            f"the source at '{spec.location}' for "
            f"'{spec.declaration}' cannot be read as the declared "
            f"'{spec.format}' format: {error}"
        ) from error
    found = _report_declared_null_statistics(spec, services)
    return relation, found


__all__ = [
    "CoreSourceCredentialOptions",
    "DeclaredColumn",
    "DeclaredPath",
    "SourceSpec",
    "open_source",
    "source_scan",
    "source_spec",
    "sql_type_for",
    "widened_column",
]
