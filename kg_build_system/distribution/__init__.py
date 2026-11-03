"""The default distribution: supplied modules and their registration.

A graph author registers supplied modules and configures them here. The module
extension protocol is :mod:`kg_build_system.distribution.internal`; each supplied
module keeps its compiler and executor together under
:mod:`kg_build_system.distribution.modules`.

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

from .public import (
    CollapseExactDuplicatesModule,
    CoreConfiguration,
    CoreModule,
    FileModule,
    FileModuleConfiguration,
    MergeCompatibleFactsModule,
    MergeCompatibleFactsModuleConfiguration,
    MetaGraphModule,
    MetaGraphModuleConfiguration,
    ModuleRegistration,
    ModuleRegistrationConfiguration,
    Neo4jModule,
    Neo4jModuleConfiguration,
    RejectConflictingNonNullValuesConfiguration,
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
