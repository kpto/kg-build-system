"""Author-facing build-stage registration and the supplied modules.

A graph author registers supplied modules and configures them here. The module
extension protocols are :mod:`kg_build_system.modules.interfaces`; module IR is
:mod:`kg_build_system.modules.ir`. Target modules are loaded on first use so the
core package does not import an engine or a target it does not need.
"""
from __future__ import annotations

from importlib import import_module
from typing import TYPE_CHECKING, Any

from .interfaces import (
    Module,
    ModuleRegistration,
    ModuleRegistrationConfiguration,
    register_module,
)
from .operators import (
    CollapseExactDuplicatesModule,
    MergeCompatibleFactsModule,
    MergeCompatibleFactsModuleConfiguration,
    RejectConflictingNonNullValuesConfiguration,
    RejectConflictingNonNullValuesModule,
)

if TYPE_CHECKING:
    from .targets.file import FileModule, FileModuleConfiguration
    from .targets.meta_graph import MetaGraphModule, MetaGraphModuleConfiguration
    from .targets.neo4j import Neo4jModule, Neo4jModuleConfiguration


_TARGET_EXPORTS: dict[str, tuple[str, str]] = {
    "FileModule": (".targets.file", "FileModule"),
    "FileModuleConfiguration": (".targets.file", "FileModuleConfiguration"),
    "MetaGraphModule": (".targets.meta_graph", "MetaGraphModule"),
    "MetaGraphModuleConfiguration": (
        ".targets.meta_graph", "MetaGraphModuleConfiguration",
    ),
    "Neo4jModule": (".targets.neo4j", "Neo4jModule"),
    "Neo4jModuleConfiguration": (
        ".targets.neo4j", "Neo4jModuleConfiguration",
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
