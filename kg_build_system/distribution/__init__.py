"""The default distribution: supplied modules and their registration.

A graph author registers supplied modules and configures them here. The module
protocol is :mod:`kg_build_system.distribution.model.internal`; module classes
and registration live in :mod:`kg_build_system.distribution.service.public`.

Example:
    ```python
    from kg_build_system.distribution import (
        FileModule, FileModuleConfiguration, register_module,
    )

    modules = (
        register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
    )
    ```
"""
from __future__ import annotations

from .model.public import (
    CoreConfiguration,
    FileModuleConfiguration,
    MergeCompatibleFactsModuleConfiguration,
    MetaGraphModuleConfiguration,
    ModuleRegistration,
    ModuleRegistrationConfiguration,
    Neo4jModuleConfiguration,
    RejectConflictingNonNullValuesConfiguration,
)
from .service.public import (
    CollapseExactDuplicatesModule,
    CoreModule,
    FileModule,
    MergeCompatibleFactsModule,
    MetaGraphModule,
    Neo4jModule,
    RejectConflictingNonNullValuesModule,
    module_configuration_json,
    register_module,
)

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
