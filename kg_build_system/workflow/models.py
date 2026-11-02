"""Compatibility model module for workflow declarations and runtime results.

The module contract is owned by :mod:`kg_build_system.kernel.contract`. Every
kernel contract name below is re-exported here, unchanged, because modules and
Open Targets still import it from the historical ``workflow.models`` path. This
module does not define a second copy of those values.

It adds only the values the workflow package itself owns: the assembled
:class:`WorkflowDefinition` and the runtime results :class:`BuildRuntime` and
:class:`WorkflowReport`.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from .._frozen_json import FrozenJson
from ..kernel.contract import (
    Artifact,
    ArtifactType,
    CompilationContext,
    Connection,
    ContinuableInput,
    DefinedContribution,
    DefinedStep,
    DisruptedExecutionContext,
    DisruptingInput,
    ExecutionContext,
    ExecutorFactoryContext,
    Failure,
    Given,
    Input,
    ModuleDefinition,
    ModuleReference,
    Output,
    Publication,
    PublishedArtifact,
    RuntimeFieldDefinition,
    StepOutcome,
    StepStatus,
    TakenInput,
    WorkflowContribution,
    WorkflowStep,
    type_matches,
)


@dataclass(frozen=True, slots=True)
class WorkflowDefinition:
    """An assembled workflow: its contributions and their resolved connections.

    Every name is settled and every connection is stored as the generated
    identity of its two openings. The definition stores no owner reference and
    derives all wider views from these two fields.
    """

    contributions: tuple[DefinedContribution, ...]
    connections: tuple[Connection, ...] = ()

    @property
    def modules(self) -> tuple[ModuleDefinition, ...]:
        return tuple(contribution.module for contribution in self.contributions)

    @property
    def steps_by_module(self) -> tuple[tuple[str, DefinedStep], ...]:
        """Every step with the id of the module that contributed it."""
        return tuple(
            (contribution.module.reference.module_id, step)
            for contribution in self.contributions
            for step in contribution.steps
        )

    @property
    def variables_by_module(self) -> Mapping[str, FrozenJson | None]:
        """Each module's own data, which no workflow rule reads."""
        return {
            contribution.module.reference.module_id: contribution.variables
            for contribution in self.contributions
        }


@dataclass(frozen=True, slots=True)
class BuildRuntime:
    """How a build runs: where it writes, and the settings it is given."""

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
    """The user-facing result of a completed workflow."""

    published_artifacts: tuple[PublishedArtifact, ...]
    recovered_failures: tuple[Failure, ...]
    unresolved_failures: tuple[Failure, ...]
    provenance: dict[str, Any]

    @property
    def succeeded(self) -> bool:
        return not self.unresolved_failures


__all__ = [
    "Artifact",
    "ArtifactType",
    "BuildRuntime",
    "CompilationContext",
    "Connection",
    "ContinuableInput",
    "DefinedContribution",
    "DefinedStep",
    "DisruptedExecutionContext",
    "DisruptingInput",
    "ExecutionContext",
    "ExecutorFactoryContext",
    "Failure",
    "Given",
    "Input",
    "ModuleDefinition",
    "ModuleReference",
    "Output",
    "Publication",
    "PublishedArtifact",
    "RuntimeFieldDefinition",
    "StepOutcome",
    "StepStatus",
    "TakenInput",
    "WorkflowContribution",
    "WorkflowDefinition",
    "WorkflowReport",
    "WorkflowStep",
    "type_matches",
]
