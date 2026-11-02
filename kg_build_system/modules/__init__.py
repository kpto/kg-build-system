"""Author-facing build-stage registration and the supplied modules.

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

from typing import TYPE_CHECKING, Any

from . import public as _public
from .public import (
    CollapseExactDuplicatesModule,
    MergeCompatibleFactsModule,
    MergeCompatibleFactsModuleConfiguration,
    Module,
    ModuleRegistration,
    ModuleRegistrationConfiguration,
    RejectConflictingNonNullValuesConfiguration,
    RejectConflictingNonNullValuesModule,
    register_module as _register_module,
)

if TYPE_CHECKING:
    from .public import (
        FileModule, FileModuleConfiguration, MetaGraphModule,
        MetaGraphModuleConfiguration, Neo4jModule, Neo4jModuleConfiguration,
    )


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


def register_module(
    module_class: type[Module],
    configuration: ModuleRegistrationConfiguration | None = None,
) -> ModuleRegistration[Any]:
    """Pair a module class with its configuration, or construct its default.

    With no configuration, the module's ``CONFIGURATION_TYPE`` is called with
    no arguments; a type with required fields therefore needs an explicit
    instance. Registration is inert: it holds data and does not import a
    callable or run a module.

    Example:
        ```python
        from kg_build_system.modules import (
            FileModule, FileModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                FileModule, FileModuleConfiguration("graph.jsonl"),
            ),
        )
        ```
    """
    return _register_module(module_class, configuration)


def __getattr__(name: str) -> Any:
    if name in __all__:
        return getattr(_public, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(__all__)
