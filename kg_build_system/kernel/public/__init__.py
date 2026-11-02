"""The kernel's public surface: protocols, build values and module contract.

This package is domain-agnostic. It knows languages, build parts, modules,
steps, artifacts and connections; it knows no table, topology, expression, SQL
or graph vocabulary. A graph author uses the names exported by
:mod:`kg_build_system.kernel`, which re-exports this module unchanged.
"""
from __future__ import annotations

from .build import Build, BuildIR
from .contract import (
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
from .language import Language, LanguageContext, Namespace
from .module import Module, ModuleCompiler, ModuleExecutor
from .registry import Registry

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
