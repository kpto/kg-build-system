"""Author-facing registration and the supplied distribution modules."""
from __future__ import annotations

from .model import ModuleRegistration, ModuleRegistrationConfiguration
from .service import module_configuration_json, register_module
from ..modules.conflict_validation import (
    RejectConflictingNonNullValuesConfiguration,
    RejectConflictingNonNullValuesModule,
)
from ..modules.core import CoreConfiguration, CoreModule
from ..modules.deduplication import CollapseExactDuplicatesModule
from ..modules.file import FileModule, FileModuleConfiguration
from ..modules.merging import (
    MergeCompatibleFactsModule,
    MergeCompatibleFactsModuleConfiguration,
)
from ..modules.meta_graph import MetaGraphModule, MetaGraphModuleConfiguration
from ..modules.neo4j import Neo4jModule, Neo4jModuleConfiguration

__all__ = [
    "CollapseExactDuplicatesModule",
    "CoreConfiguration",
    "CoreModule",
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
    "module_configuration_json",
    "register_module",
]
