"""Compatibility model module for workflow declarations and runtime results.

The kernel contract names are re-exported unchanged from
:mod:`kg_build_system.workflow.internal.models`; the workflow package's public
runtime models come from :mod:`kg_build_system.workflow.public.models`.
"""
from __future__ import annotations

from .internal.models import (
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
    WorkflowDefinition,
    WorkflowStep,
    type_matches,
)
from .public.models import BuildRuntime, WorkflowReport

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
