"""Workflow modules supplied when creating a build blueprint."""
from .interfaces import (
    Module, ModuleRegistration, ModuleRegistrationConfiguration, register_module,
)
from .operators import (
    CollapseExactDuplicatesModule,
    MergeCompatibleFactsModule,
    MergeCompatibleFactsModuleConfiguration,
    RejectConflictingNonNullValuesConfiguration,
    RejectConflictingNonNullValuesModule,
)
from .targets.file import FileModule, FileModuleConfiguration
from .targets.meta_graph import MetaGraphModule, MetaGraphModuleConfiguration
from .targets.neo4j import Neo4jModule, Neo4jModuleConfiguration

__all__ = [
    "CollapseExactDuplicatesModule",
    "FileModule",
    "FileModuleConfiguration",
    "MergeCompatibleFactsModule",
    "MergeCompatibleFactsModuleConfiguration",
    "MetaGraphModule",
    "MetaGraphModuleConfiguration",
    "Module",
    "ModuleRegistration",
    "ModuleRegistrationConfiguration",
    "Neo4jModule",
    "Neo4jModuleConfiguration",
    "RejectConflictingNonNullValuesConfiguration",
    "RejectConflictingNonNullValuesModule",
    "register_module",
]
