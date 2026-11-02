"""Domain-agnostic kernel: languages, modules, build composition.

This is the import surface for other framework packages and for module
implementations. It re-exports :mod:`kg_build_system.kernel.public` unchanged.
"""
from __future__ import annotations

from .public import (
    Artifact,
    ArtifactType,
    Build,
    BuildIR,
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
    Language,
    LanguageContext,
    Module,
    ModuleCompiler,
    ModuleDefinition,
    ModuleExecutor,
    ModuleReference,
    Namespace,
    Output,
    Publication,
    PublishedArtifact,
    Registry,
    RuntimeFieldDefinition,
    StepOutcome,
    StepStatus,
    TakenInput,
    WorkflowContribution,
    WorkflowStep,
    type_matches,
)

__all__ = [
    "Artifact", "ArtifactType", "Build", "BuildIR", "CompilationContext",
    "Connection", "ContinuableInput", "DefinedContribution", "DefinedStep",
    "DisruptedExecutionContext", "DisruptingInput", "ExecutionContext",
    "ExecutorFactoryContext", "Failure", "Given", "Input", "Language",
    "LanguageContext", "Module", "ModuleCompiler", "ModuleDefinition",
    "ModuleExecutor", "ModuleReference", "Namespace", "Output", "Publication",
    "PublishedArtifact", "Registry", "RuntimeFieldDefinition", "StepOutcome",
    "StepStatus", "TakenInput", "WorkflowContribution", "WorkflowStep",
    "type_matches",
]
