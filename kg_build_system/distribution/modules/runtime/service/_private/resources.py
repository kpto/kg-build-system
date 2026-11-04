"""Open and close the storage and credential resources one execution owns."""
from __future__ import annotations

import shutil
from pathlib import Path
from tempfile import mkdtemp
from typing import Any

from kg_build_system.kernel import RuntimeConfiguration

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
    temporary root. It owns only the temporary root, which ``close`` removes.

    Example:
    ```python
    from kg_build_system.distribution.modules.runtime import RuntimeResources

    provider = RuntimeResources()
    resources = provider.resources(configuration)
    provider.close()
    ```
    """

    def __init__(self) -> None:
        self._temporary_directories: list[Path] = []

    def resources(
        self, configuration: RuntimeConfiguration,
    ) -> dict[type, Any]:
        """Create the storage and credential resources for one execution.

        Example:
        ```python
        resources = RuntimeResources().resources(configuration)
        ```
        """
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
        return {
            OutputStorage: LocalWorkingStorage(output_directory),
            WorkingStorage: LocalWorkingStorage(working_directory),
            TemporaryStorage: LocalTemporaryStorage(temporary_directory),
            CredentialResolver: MappingCredentialResolver(
                configuration.credentials,
            ),
        }

    def close(self) -> None:
        """Remove the temporary root this provider owns.

        Example:
        ```python
        RuntimeResources().close()
        ```
        """
        directories = self._temporary_directories
        self._temporary_directories = []
        for directory in directories:
            shutil.rmtree(directory, ignore_errors=True)


__all__ = ["RuntimeResources"]
