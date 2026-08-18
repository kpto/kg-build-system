"""Typed runtime capabilities shared by every workflow module."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Protocol


class WorkflowLogger(Protocol):
    """Step-scoped logging exposed to workflow module executors."""

    def debug(self, message: str, *args: object) -> None: ...

    def info(self, message: str, *args: object) -> None: ...

    def warning(self, message: str, *args: object) -> None: ...

    def error(self, message: str, *args: object) -> None: ...


class WorkingStorage(Protocol):
    """Storage rooted at a caller-selected build directory."""

    def child(self, relative_path: PurePosixPath) -> Path: ...


@dataclass(frozen=True)
class LocalWorkingStorage:
    root: Path

    def child(self, relative_path: PurePosixPath) -> Path:
        return self.root.joinpath(*relative_path.parts)


@dataclass(frozen=True)
class LocalTemporaryStorage:
    root: Path


class CredentialResolver(Protocol):
    def resolve(self, reference: str) -> str: ...


@dataclass(frozen=True)
class MappingCredentialResolver:
    credentials: Mapping[str, str]

    def resolve(self, reference: str) -> str:
        return self.credentials[reference]


@dataclass(frozen=True, slots=True)
class RelationRef:
    """Opaque reference to a relation owned by the build runtime."""

    name: str

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("relation name must be non-empty")


class RelationService(Protocol):
    """Executor-owned relational operations available to workflow modules."""

    def reference(self, value: object) -> str: ...

    def materialize(
        self, name: str, query: str, parameters: Sequence[object] = (),
    ) -> RelationRef: ...

    def query(
        self, query: str, parameters: Sequence[object] = (),
    ) -> Any: ...

    def export_parquet(
        self, query: str, destination: Path, *, compression: str = "zstd",
    ) -> None: ...

    def register_filesystem(self, filesystem: object) -> None: ...


def _quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def _sql_string(value: str) -> str:
    return "'" + value.replace("'", "''") + "'"


def _require_query(sql: str) -> None:
    parts = sql.lstrip().split(None, 1)
    keyword = parts[0].upper() if parts else ""
    if keyword not in {
        "DESCRIBE", "EXPLAIN", "SELECT", "SHOW", "SUMMARIZE", "VALUES", "WITH",
    }:
        raise ValueError("relation queries must not contain DDL or mutation statements")


class DuckDBRelationService:
    """DuckDB-backed relation lifecycle controlled by the executor."""

    def __init__(self, connection: Any, *, compression: bool) -> None:
        self._connection = connection
        self._compression = compression
        self._dirty = False

    def reference(self, value: object) -> str:
        if not isinstance(value, RelationRef):
            raise TypeError("relational artifacts must contain RelationRef values")
        return _quote_identifier(value.name)

    def materialize(
        self, name: str, query: str, parameters: Sequence[object] = (),
    ) -> RelationRef:
        reference = RelationRef(name)
        self._connection.execute(
            f"CREATE TABLE {_quote_identifier(reference.name)} AS {query}",
            list(parameters),
        )
        self._dirty = True
        return reference

    def query(
        self, query: str, parameters: Sequence[object] = (),
    ) -> Any:
        _require_query(query)
        return self._connection.execute(query, list(parameters))

    def export_parquet(
        self, query: str, destination: Path, *, compression: str = "zstd",
    ) -> None:
        self._connection.execute(
            f"COPY ({query}) TO {_sql_string(destination.resolve().as_posix())} "
            f"(FORMAT PARQUET, COMPRESSION {compression.upper()})"
        )

    def register_filesystem(self, filesystem: object) -> None:
        self._connection.register_filesystem(filesystem)

    def finish_step(self) -> None:
        """Apply storage policy once after all materializations in a step."""
        if self._dirty and self._compression:
            self._connection.execute("CHECKPOINT")
        self._dirty = False


@dataclass(frozen=True)
class ExecutionServices:
    """Runtime facilities shared by every module."""

    relations: RelationService
    output_storage: WorkingStorage
    working_storage: WorkingStorage
    temporary_storage: LocalTemporaryStorage
    credentials: CredentialResolver
    logger: WorkflowLogger
