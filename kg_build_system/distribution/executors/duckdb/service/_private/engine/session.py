"""The DuckDB engine session one workflow execution holds open."""
from __future__ import annotations

import shutil
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Literal

from .service import DuckDBRelationService, configure_framework_macros

_DUCKDB_BUILD_DATABASE = "kg_build_memory"
_DUCKDB_BUILD_FILENAME = "kg_build.duckdb"
# A TIMESTAMPTZ reaches Python with the session time zone, whose default is the
# machine's zone. A workflow pins it so the same data reads back the same way.
PINNED_TIME_ZONE = "UTC"


@dataclass(frozen=True, slots=True)
class DuckDbSettings:
    """The safe DuckDB settings one execution is configured with."""

    storage: Literal["memory", "disk"] = "memory"
    threads: int | None = None
    memory_limit: str | None = None
    compression: bool = True


@dataclass(frozen=True, slots=True)
class EngineSession:
    """The opened engine behind one execution, with its effective settings."""

    relations: DuckDBRelationService
    time_zone: str
    memory_limit: str | None
    threads: int | None
    storage_directory: Path | None = None

    def close(self) -> None:
        """Close the relation service and remove the engine's private storage.

        Safe to call more than once: the relation service ignores a repeated
        close and removing an absent directory is a no-op.
        """
        self.relations.close()
        if self.storage_directory is not None:
            shutil.rmtree(self.storage_directory, ignore_errors=True)

    def finish_step(self) -> None:
        """Apply the engine's storage policy after one finished step."""
        self.relations.finish_step()


def _open_duckdb(
    duckdb: Any, settings: DuckDbSettings, storage_directory: Path,
) -> Any:
    """Open the configured in-memory or working-directory database."""
    if settings.storage == "memory":
        return duckdb.connect()
    if settings.storage == "disk":
        return duckdb.connect(str(storage_directory / _DUCKDB_BUILD_FILENAME))
    raise ValueError("duckdb storage must be 'memory' or 'disk'")


def _configure_duckdb(
    connection: Any, settings: DuckDbSettings, storage_directory: Path,
) -> None:
    """Configure resource limits and storage policy for one execution."""
    if settings.threads is not None:
        if settings.threads < 1:
            raise ValueError("duckdb threads must be at least one")
        connection.execute("SET threads = ?", [settings.threads])

    if settings.memory_limit is not None:
        if not isinstance(settings.memory_limit, str):
            raise TypeError("duckdb memory_limit must be a string")
        if not settings.memory_limit.strip():
            raise ValueError("duckdb memory_limit must be non-empty")
        connection.execute(
            "SET memory_limit = ?", [settings.memory_limit]
        )

    if not isinstance(settings.compression, bool):
        raise TypeError("duckdb compression must be a boolean")

    connection.execute(
        "SET temp_directory = ?", [storage_directory.resolve().as_posix()]
    )
    if settings.storage == "memory":
        compression = " (COMPRESS)" if settings.compression else ""
        connection.execute(
            f"ATTACH ':memory:' AS {_DUCKDB_BUILD_DATABASE}{compression}"
        )
        connection.execute(f"USE {_DUCKDB_BUILD_DATABASE}")
    elif settings.storage == "disk":
        if not settings.compression:
            connection.execute("PRAGMA force_compression = 'uncompressed'")
    else:
        raise ValueError("duckdb storage must be 'memory' or 'disk'")
    configure_framework_macros(connection)
    connection.execute("SET TimeZone = ?", [PINNED_TIME_ZONE])


def _effective_duckdb_resources(connection: Any) -> tuple[str, int]:
    """Read DuckDB's normalized effective resource settings."""
    settings = dict(connection.execute(
        "SELECT name, value FROM duckdb_settings() "
        "WHERE name IN ('memory_limit', 'threads')"
    ).fetchall())
    return str(settings["memory_limit"]), int(settings["threads"])


def _effective_duckdb_time_zone(connection: Any) -> str:
    """Read the normalized session time zone the execution ended up with."""
    return str(connection.execute(
        "SELECT current_setting('TimeZone')"
    ).fetchone()[0])


def open_engine(
    settings: DuckDbSettings,
    storage_directory: Path,
) -> EngineSession:
    """Open, configure and return the one relational engine an execution uses."""
    try:
        import duckdb
    except ImportError as error:
        raise RuntimeError("DuckDB is required to execute workflows") from error
    storage_directory.mkdir(parents=True, exist_ok=True)
    connection = _open_duckdb(duckdb, settings, storage_directory)
    try:
        _configure_duckdb(connection, settings, storage_directory)
        time_zone = _effective_duckdb_time_zone(connection)
        memory_limit, threads = _effective_duckdb_resources(connection)
    except BaseException:
        connection.close()
        raise
    relations = DuckDBRelationService(
        connection,
        checkpoint_on_step=(
            settings.compression or settings.storage == "disk"
        ),
    )
    return EngineSession(
        relations=relations,
        time_zone=time_zone,
        memory_limit=memory_limit,
        threads=threads,
        storage_directory=storage_directory,
    )


@contextmanager
def engine_session(
    settings: DuckDbSettings,
    storage_directory: Path,
) -> Iterator[EngineSession]:
    """Open and close one engine session around a caller's work."""
    session = open_engine(settings, storage_directory)
    try:
        yield session
    finally:
        session.close()


__all__ = [
    "DuckDbSettings",
    "EngineSession",
    "PINNED_TIME_ZONE",
    "engine_session",
    "open_engine",
]
