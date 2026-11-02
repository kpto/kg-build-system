"""Author-facing registration and the supplied build modules.

A graph author registers supplied modules and configures them here. The module
extension protocols are :mod:`kg_build_system.modules.internal`; module IR is
:mod:`kg_build_system.modules.internal.ir`. Target modules are loaded on first use so the
core package does not import an engine or a target it does not need.

Example:
    ```python
    from kg_build_system.modules import (
        FileModule, FileModuleConfiguration, register_module,
    )

    modules = (
        register_module(FileModule, FileModuleConfiguration("graph.jsonl")),
    )
    ```
"""
from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .._private.operators import (
    CollapseExactDuplicatesModule,
    MergeCompatibleFactsModule,
    MergeCompatibleFactsModuleConfiguration,
    RejectConflictingNonNullValuesConfiguration,
    RejectConflictingNonNullValuesModule,
)
from ..internal.module import Module, ModuleRegistration, ModuleRegistrationConfiguration
from .registration import module_configuration_json, register_module

if TYPE_CHECKING:
    from .._private.targets.file import FileModule, FileModuleConfiguration
    from .._private.targets.meta_graph import (
        MetaGraphModule, MetaGraphModuleConfiguration,
    )
    from .._private.targets.neo4j import Neo4jModule, Neo4jModuleConfiguration


_TARGET_EXPORTS: dict[str, tuple[str, str]] = {
    "FileModule": (".._private.targets.file", "FileModule"),
    "FileModuleConfiguration": (".._private.targets.file", "FileModuleConfiguration"),
    "MetaGraphModule": (".._private.targets.meta_graph", "MetaGraphModule"),
    "MetaGraphModuleConfiguration": (
        ".._private.targets.meta_graph", "MetaGraphModuleConfiguration",
    ),
    "Neo4jModule": (".._private.targets.neo4j", "Neo4jModule"),
    "Neo4jModuleConfiguration": (
        ".._private.targets.neo4j", "Neo4jModuleConfiguration",
    ),
}

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
    "module_configuration_json",
    "register_module",
]


def __getattr__(name: str) -> Any:
    target = _TARGET_EXPORTS.get(name)
    if target is None:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
    module_name, attribute = target
    value = getattr(import_module(module_name, __name__), attribute)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    return sorted(__all__)
