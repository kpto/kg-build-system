"""Open and close the DuckDB engine one workflow execution owns."""
from __future__ import annotations

from pathlib import Path
from tempfile import mkdtemp

from kg_build_system.distribution.service.internal.relations import (
    RelationService,
)
from kg_build_system.kernel import (
    PipelineEvent,
    PipelineFinished,
    PipelineHalted,
    PipelineStarted,
    ResourceRegistry,
    RuntimeConfiguration,
)

from .engine.session import DuckDbSettings, open_engine
from .service import DuckDbService


def _settings(configuration: RuntimeConfiguration) -> DuckDbSettings:
    """Read the safe DuckDB settings from the ``duckdb`` provider configuration."""
    component = configuration.provider_configuration.get("duckdb", {})
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
    """Provide the DuckDB engine and its non-owning relation service.

    The provider creates only the engine's private storage directory when it
    receives ``PipelineStarted``. Output, working, temporary and credential
    resources belong to ``RuntimeResources``. The engine is closed on
    ``PipelineFinished`` or ``PipelineHalted``.

    Example:
    ```python
    from kg_build_system.distribution.modules.duckdb import (
        DuckDbResourceProvider,
    )

    provider = DuckDbResourceProvider()
    provider.on_event(event)
    ```
    """

    def __init__(self) -> None:
        self._services: list[DuckDbService] = []

    def on_event(self, event: PipelineEvent) -> None:
        """Open the engine on start and close it on finish or halt.

        Example:
            ```python
            provider.on_event(PipelineStarted(plan, configuration, resources))
            ```
        """
        if isinstance(event, PipelineStarted):
            self._create(event.configuration, event.resources)
        elif isinstance(event, (PipelineFinished, PipelineHalted)):
            self._dispose()

    def _create(
        self,
        configuration: RuntimeConfiguration,
        resources: ResourceRegistry,
    ) -> None:
        settings = _settings(configuration)
        working_directory = configuration.working_directory
        working_directory.mkdir(parents=True, exist_ok=True)
        storage_directory = Path(mkdtemp(
            prefix=".kg-build-duckdb-", dir=working_directory,
        ))
        engine = open_engine(settings, storage_directory)
        service = DuckDbService(engine)
        self._services.append(service)
        resources.add(DuckDbService, service)
        resources.add(RelationService, service.relations)

    def _dispose(self) -> None:
        services = self._services
        self._services = []
        for service in reversed(services):
            service.close()


__all__ = ["DuckDbResourceProvider"]
