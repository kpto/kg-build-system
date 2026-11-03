"""Author-facing build configuration.

A build reads a workflow plan and produces artifacts. The values here state how
one build runs; they carry no engine, scheduler or storage object.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from kg_build_system.kernel import RuntimeConfiguration


@dataclass(frozen=True, slots=True)
class BuildRuntime:
    """How a build runs: where it writes, and the settings it is given.

    Attributes:
        credentials: Resolved credential values by reference.
        component_configuration: Per-component runtime overrides by component ID.
        output_directory: Where publications and reports are written.
        working_directory: Working storage; a relative path resolves beneath
            ``output_directory``.
        temporary_directory: Temporary storage, or ``None`` for the system
            temporary directory.
        duckdb_storage: Keep the engine database in ``"memory"`` or on
            ``"disk"``.
        duckdb_threads: Query parallelism, or the platform default.
        duckdb_memory_limit: A size such as ``"4GiB"``, or the platform default.
        duckdb_compression: Whether the engine compresses its columns.

    Example:
    ```python
    from kg_build_system.distribution.model.public.runtime import BuildRuntime

    runtime = BuildRuntime(
        duckdb_storage="disk",
        duckdb_threads=4,
        component_configuration={"file": {"relative_path": "graph/current.jsonl"}},
    )
    configuration = runtime.to_configuration()
    assert configuration.component_configuration["duckdb"]["threads"] == 4
    ```
    """

    credentials: dict[str, str] = field(default_factory=dict)
    component_configuration: dict[str, dict[str, Any]] = field(
        default_factory=dict,
    )
    output_directory: Path = field(default_factory=lambda: Path.cwd() / "build")
    working_directory: Path = field(default_factory=lambda: Path("_workdir"))
    temporary_directory: Path | None = None
    duckdb_storage: Literal["memory", "disk"] = "memory"
    duckdb_threads: int | None = None
    duckdb_memory_limit: str | None = None
    duckdb_compression: bool = True

    def __post_init__(self) -> None:
        if not self.working_directory.is_absolute():
            object.__setattr__(
                self,
                "working_directory",
                self.output_directory / self.working_directory,
            )

    def to_configuration(self) -> RuntimeConfiguration:
        """Return the kernel configuration one execution reads.

        Per-component overrides are copied unchanged. The ``duckdb`` component
        entry is built from the safe engine settings, so an executor reads them
        from the same per-component map as every other component's values.

        Example:
            ```python
            configuration = BuildRuntime().to_configuration()
            assert configuration.component_configuration["duckdb"]["storage"] == (
                "memory"
            )
            ```
        """
        component_configuration = {
            component: dict(values)
            for component, values in self.component_configuration.items()
        }
        component_configuration["duckdb"] = {
            "storage": self.duckdb_storage,
            "threads": self.duckdb_threads,
            "memory_limit": self.duckdb_memory_limit,
            "compression": self.duckdb_compression,
        }
        return RuntimeConfiguration(
            output_directory=self.output_directory,
            working_directory=self.working_directory,
            temporary_directory=self.temporary_directory,
            credentials=dict(self.credentials),
            component_configuration=component_configuration,
        )


__all__ = ["BuildRuntime"]
