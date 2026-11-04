"""Create and dispose the storage and credential resources one execution owns."""
from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import mkdtemp

from kg_build_system.kernel import (
    PipelineEvent,
    PipelineFinished,
    PipelineHalted,
    PipelineStarted,
    ResourceRegistry,
    RuntimeConfiguration,
)

from ...model.public import (
    CredentialResolver,
    OutputStorage,
    TemporaryStorage,
    WorkingStorage,
)
from .storage import (
    LocalTemporaryStorage,
    LocalWorkingStorage,
    MappingCredentialResolver,
)


class RuntimeResources:
    """Provide output, working and temporary storage and credentials.

    The provider creates the output and working directories and one private
    temporary root when it receives ``PipelineStarted``. It adds them to the
    event registry and removes only the temporary root on ``PipelineFinished``
    or ``PipelineHalted``.

    Example:
    ```python
    from kg_build_system.distribution.modules.runtime import RuntimeResources

    provider = RuntimeResources()
    provider.on_event(event)
    ```
    """

    def __init__(self) -> None:
        self._temporary_directories: list[Path] = []

    def on_event(self, event: PipelineEvent) -> None:
        """Create resources on start and remove them on finish or halt.

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
        self._temporary_directories.append(temporary_directory)
        resources.add(OutputStorage, LocalWorkingStorage(output_directory))
        resources.add(WorkingStorage, LocalWorkingStorage(working_directory))
        resources.add(
            TemporaryStorage,
            LocalTemporaryStorage(temporary_directory),
        )
        resources.add(
            CredentialResolver,
            MappingCredentialResolver(configuration.credentials),
        )

    def _dispose(self) -> None:
        directories = self._temporary_directories
        self._temporary_directories = []
        for directory in directories:
            shutil.rmtree(directory, ignore_errors=True)


__all__ = ["RuntimeResources"]
