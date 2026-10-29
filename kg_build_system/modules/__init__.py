"""Author-facing build-stage registration and the supplied modules.

A graph author registers supplied modules and configures them here. The module
extension protocols are :mod:`kg_build_system.modules.interfaces`; module IR is
:mod:`kg_build_system.modules.ir`.
"""
from __future__ import annotations

from .operators import (
    CollapseExactDuplicatesModule,
    MergeCompatibleFactsModule,
    MergeCompatibleFactsModuleConfiguration,
    RejectConflictingNonNullValuesConfiguration,
    RejectConflictingNonNullValuesModule,
)
from .protocols import (
    ModuleRegistration,
    ModuleRegistrationConfiguration,
    register_module,
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
    "ModuleRegistration",
    "ModuleRegistrationConfiguration",
    "Neo4jModule",
    "Neo4jModuleConfiguration",
    "RejectConflictingNonNullValuesConfiguration",
    "RejectConflictingNonNullValuesModule",
    "register_module",
]
