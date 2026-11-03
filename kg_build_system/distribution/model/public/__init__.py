"""The distribution's authoring model: configurations and registration values."""
from __future__ import annotations

from .artifacts import (
    ComponentDTO,
    CoreArtifactTypes,
    GraphRecordArtifact,
    component_kind,
    graph_components,
    graph_record_components,
)
from .modules import (
    ConflictingNonNullValueFinding,
    ConflictingNonNullValuesReport,
    CoreConfiguration,
    DeduplicationConfiguration,
    FileModuleConfiguration,
    MergeCompatibleFactsModuleConfiguration,
    MetaGraphModuleConfiguration,
    Neo4jModuleConfiguration,
    RejectConflictingNonNullValuesConfiguration,
)
from .registration import ModuleRegistration, ModuleRegistrationConfiguration

__all__ = [
    "ComponentDTO",
    "ConflictingNonNullValueFinding",
    "ConflictingNonNullValuesReport",
    "CoreArtifactTypes",
    "CoreConfiguration",
    "DeduplicationConfiguration",
    "FileModuleConfiguration",
    "GraphRecordArtifact",
    "MergeCompatibleFactsModuleConfiguration",
    "MetaGraphModuleConfiguration",
    "ModuleRegistration",
    "ModuleRegistrationConfiguration",
    "Neo4jModuleConfiguration",
    "RejectConflictingNonNullValuesConfiguration",
    "component_kind",
    "graph_components",
    "graph_record_components",
]
