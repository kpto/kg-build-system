"""Create and close the live services a DuckDB workflow execution needs."""
from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import mkdtemp
from typing import Any, Literal

from kg_build_system.kernel import RuntimeConfiguration, WorkflowPlan

from ....runtime import (
    ExecutionServices,
    LocalTemporaryStorage,
    LocalWorkingStorage,
    MappingCredentialResolver,
    NullWorkflowLogger,
)
from .engine.session import DuckDbSettings, open_engine


def _settings(configuration: RuntimeConfiguration) -> DuckDbSettings:
    """Read the safe DuckDB settings from the ``duckdb`` component configuration."""
    component = configuration.component_configuration.get("duckdb", {})
    storage = component.get("storage", "memory")
    if storage not in {"memory", "disk"}:
        raise ValueError("duckdb storage must be 'memory' or 'disk'")
    threads = component.get("threads")
    if threads is not None and (
        not isinstance(threads, int) or isinstance(threads, bool) or threads < 1
    ):
        raise ValueError("duckdb threads must be a positive integer")
    memory_limit = component.get("memory_limit")
    if memory_limit is not None and not isinstance(memory_limit, str):
        raise TypeError("duckdb memory_limit must be a string")
    compression = component.get("compression", True)
    if not isinstance(compression, bool):
        raise TypeError("duckdb compression must be a boolean")
    return DuckDbSettings(
        storage=storage,
        threads=threads,
        memory_limit=memory_limit,
        compression=compression,
    )


class DuckDbResourceProvider:
    """Open the DuckDB engine, storage and credentials one execution owns."""

    def services(
        self, plan: WorkflowPlan, configuration: RuntimeConfiguration,
    ) -> ExecutionServices:
        """Create the output, working, temporary and engine services.

        Example:
            ```python
            services = DuckDbResourceProvider().services(plan, configuration)
            ```
        """
        settings = _settings(configuration)
        output_directory = configuration.output_directory
        working_directory = configuration.working_directory
        output_directory.mkdir(parents=True, exist_ok=True)
        working_directory.mkdir(parents=True, exist_ok=True)
        temporary_parent = configuration.temporary_directory
        if temporary_parent is not None:
            temporary_parent.mkdir(parents=True, exist_ok=True)
        temporary_directory = Path(mkdtemp(
            prefix=".kg-build-temp-", dir=temporary_parent,
        ))
        if settings.storage == "disk":
            storage_directory = Path(mkdtemp(
                prefix=".kg-build-duckdb-", dir=working_directory,
            ))
        else:
            storage_directory = temporary_directory
        engine = open_engine(settings, storage_directory)
        return ExecutionServices(
            relations=engine.relations,
            output_storage=LocalWorkingStorage(output_directory),
            working_storage=LocalWorkingStorage(working_directory),
            temporary_storage=LocalTemporaryStorage(temporary_directory),
            credentials=MappingCredentialResolver(configuration.credentials),
            logger=NullWorkflowLogger(),
            engine=engine,
        )

    def close(self, services: Any) -> None:
        """Close the engine session and remove the execution's temporary storage.

        Example:
            ```python
            DuckDbResourceProvider().close(services)
            ```
        """
        try:
            engine = getattr(services, "engine", None)
            close_engine = getattr(engine, "close", None)
            if callable(close_engine):
                close_engine()
            else:
                relations = getattr(services, "relations", None)
                close_relations = getattr(relations, "close", None)
                if callable(close_relations):
                    close_relations()
        finally:
            storage = getattr(services, "temporary_storage", None)
            root = getattr(storage, "root", None)
            if root is not None:
                shutil.rmtree(root, ignore_errors=True)


__all__ = ["DuckDbResourceProvider"]
