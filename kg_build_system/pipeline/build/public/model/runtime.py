"""Author-facing build configuration and result.

A build reads a frozen workflow contract and produces artifacts. The values here
state how one build runs and what it produced; they carry no engine, scheduler
or storage object.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from .....kernel import Failure, PublishedArtifact


@dataclass(frozen=True, slots=True)
class BuildRuntime:
    """How a build runs: where it writes, and the settings it is given.

    Attributes:
        credentials: Resolved credential values by reference.
        module_configuration: Per-module runtime overrides by module ID.
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
    from kg_build_system.pipeline.build import BuildRuntime

    runtime = BuildRuntime(
        duckdb_storage="disk",
        duckdb_threads=4,
        module_configuration={"file": {"relative_path": "graph/current.jsonl"}},
    )
    ```
    """

    credentials: dict[str, str] = field(default_factory=dict)
    module_configuration: dict[str, dict[str, Any]] = field(default_factory=dict)
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


@dataclass(frozen=True, slots=True)
class WorkflowReport:
    """The user-facing result of a completed workflow.

    Attributes:
        published_artifacts: One entry per publication, with its type and value.
        recovered_failures: Failures that a later step handled.
        unresolved_failures: Failures that blocked a publication.
        provenance: The workflow fingerprint, compile provenance and pinned time
            zone needed to identify the run.

    Example:
    ```python
    from kg_build_system.pipeline.build import build

    report = build(contract, output_directory="build", monitor=False)
    print(report.succeeded, len(report.published_artifacts))
    ```
    """

    published_artifacts: tuple[PublishedArtifact, ...]
    recovered_failures: tuple[Failure, ...]
    unresolved_failures: tuple[Failure, ...]
    provenance: dict[str, Any]

    @property
    def succeeded(self) -> bool:
        """Whether no failure blocked a publication.

        Example:
        ```python
        report = build(contract, output_directory="build", monitor=False)
        assert report.succeeded == (not report.unresolved_failures)
        ```
        """
        return not self.unresolved_failures


__all__ = ["BuildRuntime", "WorkflowReport"]
