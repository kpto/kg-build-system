"""The kernel's public surface: protocols, build values and module contract.

This package is domain-agnostic. It knows languages, build parts, modules,
steps, artifacts and connections; it knows no table, topology, expression, SQL
or graph vocabulary. A graph author uses the names exported by
:mod:`kg_build_system.kernel`, which re-exports this module unchanged.
"""
from __future__ import annotations

from .build import Build
from .capability import Capability
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
from .language import (
    Language, LanguageContext, Namespace, RenderContext, SourceFragment,
)
from .module import Module, ModuleCompiler, ModuleExecutor
from .registry import Registry
from .types import (
    BOOL, CANONICAL_UNIT_NAMES, DATE, FLOAT, INT, STR, TEXT_CANONICAL_UNIT_NAMES,
    TIME, TIMESTAMP, UUID, Array, ArrayType, CustomDataType, CustomType, Date,
    LogicalType, NonNullableLogicalType, Nullable, NullableType, Shape, Struct,
    StructType, Time, Timestamp, UnitType, UnitTypeName, Uuid,
    is_canonical_unit_name,
)

__all__ = [
    "Array", "ArrayType", "Artifact", "ArtifactType", "BOOL", "Build",
    "CANONICAL_UNIT_NAMES", "Capability", "CompilationContext", "Connection",
    "ContinuableInput", "CustomDataType", "CustomType", "DATE", "Date",
    "DefinedContribution", "DefinedStep", "DisruptedExecutionContext",
    "DisruptingInput", "ExecutionContext", "ExecutorFactoryContext", "FLOAT",
    "Failure", "Given", "Input", "INT", "Language", "LanguageContext",
    "LogicalType", "Module", "ModuleCompiler", "ModuleDefinition",
    "ModuleExecutor", "ModuleReference", "Namespace", "NonNullableLogicalType",
    "Nullable", "NullableType", "Output", "Publication", "PublishedArtifact",
    "Registry", "RenderContext", "RuntimeFieldDefinition", "STR", "Shape",
    "SourceFragment", "StepOutcome", "StepStatus", "Struct", "StructType",
    "TEXT_CANONICAL_UNIT_NAMES", "TIME", "TIMESTAMP", "TakenInput", "Time",
    "Timestamp", "UUID", "UnitType", "UnitTypeName", "Uuid",
    "WorkflowContribution", "WorkflowStep", "is_canonical_unit_name",
    "type_matches",
]
