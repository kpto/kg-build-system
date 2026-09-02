"""Typed runtime capabilities shared by every workflow module."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from concurrent.futures import Future, ThreadPoolExecutor, TimeoutError as FutureTimeout
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Callable, Protocol, TypeVar

from ..engines.duckdb import NULL_GUARD_MACRO_SQL


ResultT = TypeVar("ResultT")
_WORKER_POLL_SECONDS = 0.05


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

    def view(self, name: str, query: str) -> RelationRef:
        """Expose a logical relation without materializing its query."""
        ...

    def materialize(
        self, name: str, query: str, parameters: Sequence[object] = (),
    ) -> RelationRef:
        """Expose a logical relation backed by a private materialized table."""
        ...

    def query(
        self, query: str, parameters: Sequence[object] = (),
    ) -> RelationQueryResult: ...

    def export_parquet(
        self, query: str, destination: Path, *, compression: str = "zstd",
    ) -> None: ...

    def register_filesystem(self, filesystem: object) -> None: ...


class RelationQueryResult(Protocol):
    """Synchronous result access executed through the relation worker."""

    @property
    def description(self) -> Sequence[Sequence[Any]]: ...

    def fetchone(self) -> Any: ...

    def fetchall(self) -> list[Any]: ...

    def fetchmany(self, size: int) -> list[Any]: ...


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


def configure_framework_macros(connection: Any) -> None:
    """Create the engine's framework macros on one build connection.

    The statements come from the engine that will run them; this function only
    owns when they are created. Macro names are database-scoped and a disk build
    opens a fresh database each time, so creation is idempotent and runs as part
    of connection setup — before any view exists, which is the only point at
    which a lowered guard can resolve.
    """
    connection.execute(NULL_GUARD_MACRO_SQL)


class DuckDBRelationService:
    """DuckDB operations serialized through one interruptible worker thread."""

    def __init__(self, connection: Any, *, checkpoint_on_step: bool) -> None:
        self._connection = connection
        self._checkpoint_on_step = checkpoint_on_step
        self._dirty = False
        self._worker = ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="kg-build-duckdb",
        )
        self._closed = False

    def _run(self, operation: Callable[[], ResultT]) -> ResultT:
        if self._closed:
            raise RuntimeError("relation service is closed")
        future = self._worker.submit(operation)
        try:
            return self._wait(future)
        except KeyboardInterrupt:
            self._connection.interrupt()
            try:
                self._wait(future)
            except Exception:
                pass
            raise

    @staticmethod
    def _wait(future: Future[ResultT]) -> ResultT:
        while True:
            try:
                return future.result(timeout=_WORKER_POLL_SECONDS)
            except FutureTimeout:
                continue

    def reference(self, value: object) -> str:
        if not isinstance(value, RelationRef):
            raise TypeError("relational artifacts must contain RelationRef values")
        return _quote_identifier(value.name)

    def view(self, name: str, query: str) -> RelationRef:
        reference = RelationRef(name)
        self._run(
            lambda: self._connection.execute(
                f"CREATE VIEW {_quote_identifier(reference.name)} AS {query}"
            )
        )
        return reference

    def materialize(
        self, name: str, query: str, parameters: Sequence[object] = (),
    ) -> RelationRef:
        reference = RelationRef(name)
        backing_name = f"__kg_materialized_{reference.name}"
        def create() -> None:
            self._connection.execute(
                f"CREATE TABLE {_quote_identifier(backing_name)} AS {query}",
                list(parameters),
            )
            self._connection.execute(
                f"CREATE VIEW {_quote_identifier(reference.name)} AS "
                f"SELECT * FROM {_quote_identifier(backing_name)}"
            )
            self._dirty = True

        self._run(create)
        return reference

    def query(
        self, query: str, parameters: Sequence[object] = (),
    ) -> RelationQueryResult:
        _require_query(query)
        description = self._run(lambda: self._execute_query(query, parameters))
        return _DuckDBQueryResult(self, description)

    def _execute_query(
        self, query: str, parameters: Sequence[object],
    ) -> tuple[tuple[Any, ...], ...]:
        cursor = self._connection.execute(query, list(parameters))
        return tuple(tuple(column) for column in (cursor.description or ()))

    def export_parquet(
        self, query: str, destination: Path, *, compression: str = "zstd",
    ) -> None:
        self._run(
            lambda: self._connection.execute(
                f"COPY ({query}) TO {_sql_string(destination.resolve().as_posix())} "
                f"(FORMAT PARQUET, COMPRESSION {compression.upper()})"
            )
        )

    def register_filesystem(self, filesystem: object) -> None:
        self._run(lambda: self._connection.register_filesystem(filesystem))

    def finish_step(self) -> None:
        """Apply storage policy once after all materializations in a step."""
        def finish() -> None:
            if self._dirty and self._checkpoint_on_step:
                self._connection.execute("CHECKPOINT")
            self._dirty = False

        self._run(finish)

    def close(self) -> None:
        """Close the connection on its worker and stop the worker thread."""
        if self._closed:
            return
        try:
            self._run(self._connection.close)
        finally:
            self._closed = True
            self._worker.shutdown(wait=True)


class _DuckDBQueryResult:
    def __init__(
        self, service: DuckDBRelationService,
        description: tuple[tuple[Any, ...], ...],
    ) -> None:
        self._service = service
        self._description = description

    @property
    def description(self) -> tuple[tuple[Any, ...], ...]:
        return self._description

    def fetchone(self) -> Any:
        return self._service._run(self._service._connection.fetchone)

    def fetchall(self) -> list[Any]:
        return self._service._run(self._service._connection.fetchall)

    def fetchmany(self, size: int) -> list[Any]:
        return self._service._run(lambda: self._service._connection.fetchmany(size))


@dataclass(frozen=True)
class ExecutionServices:
    """Runtime facilities shared by every module."""

    relations: RelationService
    output_storage: WorkingStorage
    working_storage: WorkingStorage
    temporary_storage: LocalTemporaryStorage
    credentials: CredentialResolver
    logger: WorkflowLogger
