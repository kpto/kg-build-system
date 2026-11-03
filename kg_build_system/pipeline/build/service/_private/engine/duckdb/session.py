"""The DuckDB engine session one build holds open."""
from __future__ import annotations

from contextlib import ExitStack, contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from .service import DuckDBRelationService, configure_framework_macros

from .....model.public import BuildRuntime

_DUCKDB_BUILD_DATABASE = "kg_build_memory"
_DUCKDB_BUILD_FILENAME = "kg_build.duckdb"
# A TIMESTAMPTZ reaches Python with the session time zone, whose default is the
# machine's zone. A build pins it so the same data reads back the same way.
PINNED_TIME_ZONE = "UTC"


@dataclass(frozen=True, slots=True)
class EngineSession:
    """The opened engine behind one build, with its effective settings."""

    relations: DuckDBRelationService
    time_zone: str
    memory_limit: str | None
    threads: int | None


def _open_duckdb(
    duckdb: Any, runtime: BuildRuntime, storage_directory: Path,
) -> Any:
    """Open the configured in-memory or working-directory database."""
    if runtime.duckdb_storage == "memory":
        return duckdb.connect()
    if runtime.duckdb_storage == "disk":
        return duckdb.connect(str(storage_directory / _DUCKDB_BUILD_FILENAME))
    raise ValueError("duckdb_storage must be 'memory' or 'disk'")


def _configure_duckdb(
    connection: Any, runtime: BuildRuntime, storage_directory: Path,
) -> None:
    """Configure resource limits and storage policy for one build."""
    if runtime.duckdb_threads is not None:
        if runtime.duckdb_threads < 1:
            raise ValueError("duckdb_threads must be at least one")
        connection.execute("SET threads = ?", [runtime.duckdb_threads])

    if runtime.duckdb_memory_limit is not None:
        if not isinstance(runtime.duckdb_memory_limit, str):
            raise TypeError("duckdb_memory_limit must be a string")
        if not runtime.duckdb_memory_limit.strip():
            raise ValueError("duckdb_memory_limit must be non-empty")
        connection.execute(
            "SET memory_limit = ?", [runtime.duckdb_memory_limit]
        )

    if not isinstance(runtime.duckdb_compression, bool):
        raise TypeError("duckdb_compression must be a boolean")

    connection.execute(
        "SET temp_directory = ?", [storage_directory.resolve().as_posix()]
    )
    if runtime.duckdb_storage == "memory":
        compression = " (COMPRESS)" if runtime.duckdb_compression else ""
        connection.execute(
            f"ATTACH ':memory:' AS {_DUCKDB_BUILD_DATABASE}{compression}"
        )
        connection.execute(f"USE {_DUCKDB_BUILD_DATABASE}")
    elif runtime.duckdb_storage == "disk":
        if not runtime.duckdb_compression:
            connection.execute("PRAGMA force_compression = 'uncompressed'")
    else:
        raise ValueError("duckdb_storage must be 'memory' or 'disk'")
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
    """Read the normalized session time zone the build ended up with."""
    return str(connection.execute(
        "SELECT current_setting('TimeZone')"
    ).fetchone()[0])


@contextmanager
def engine_session(
    runtime: BuildRuntime, storage_directory: Path,
) -> Iterator[EngineSession]:
    """Open, configure and close the one relational engine a build uses."""
    try:
        import duckdb
    except ImportError as error:
        raise RuntimeError("DuckDB is required to execute builds") from error
    with ExitStack() as resources:
        connection = _open_duckdb(duckdb, runtime, storage_directory)
        try:
            _configure_duckdb(connection, runtime, storage_directory)
            time_zone = _effective_duckdb_time_zone(connection)
            memory_limit, threads = _effective_duckdb_resources(connection)
        except BaseException:
            connection.close()
            raise
        relations = DuckDBRelationService(
            connection,
            checkpoint_on_step=(
                runtime.duckdb_compression or runtime.duckdb_storage == "disk"
            ),
        )
        resources.callback(relations.close)
        yield EngineSession(
            relations=relations,
            time_zone=time_zone,
            memory_limit=memory_limit,
            threads=threads,
        )


__all__ = ["EngineSession", "PINNED_TIME_ZONE", "engine_session"]
