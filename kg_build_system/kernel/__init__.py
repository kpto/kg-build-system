"""Domain-agnostic kernel: languages, modules, build composition."""
from __future__ import annotations

from .build import BuildIR, Build
from .contract import (
    Artifact,
    ArtifactType,
    CompilationContext,
    ContinuableInput,
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
    "ContinuableInput", "DisruptedExecutionContext", "DisruptingInput",
    "ExecutionContext", "ExecutorFactoryContext", "Failure", "Given", "Input",
    "Language", "LanguageContext", "Module", "ModuleCompiler",
    "ModuleDefinition", "ModuleExecutor", "ModuleReference", "Namespace",
    "Output", "Publication", "PublishedArtifact", "Registry",
    "RuntimeFieldDefinition", "StepOutcome", "StepStatus", "TakenInput",
    "WorkflowContribution", "WorkflowStep", "type_matches",
]
