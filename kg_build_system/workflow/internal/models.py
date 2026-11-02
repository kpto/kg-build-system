"""Internal workflow models and kernel contract re-exports.

The module contract is owned by :mod:`kg_build_system.kernel`. Those
names are re-exported unchanged here because modules import them through the
workflow surface. The workflow package adds only the assembled
:class:`WorkflowDefinition`; runtime results are public models.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from ..._frozen_json import FrozenJson
from ...kernel import (
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
    """An assembled workflow: its contributions and resolved connections.

    Every name is settled and every connection is stored as the generated
    identity of its two openings.
    """

    contributions: tuple[DefinedContribution, ...]
    connections: tuple[Connection, ...] = ()

    @property
    def modules(self) -> tuple[ModuleDefinition, ...]:
        """Return each contribution's module definition."""
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


__all__ = [
    "Artifact",
    "ArtifactType",
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
    "WorkflowStep",
    "type_matches",
]
