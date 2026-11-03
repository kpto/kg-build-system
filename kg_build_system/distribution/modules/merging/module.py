"""The compatible-facts merging module."""
from __future__ import annotations

import importlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, ClassVar

from ....kernel import ExecutorFactoryContext
from ...internal.adapters.kernel_module import KernelModule
from ...internal.service.runtime import thaw_object
from ...public.model.registration import ModuleRegistrationConfiguration


@dataclass(frozen=True)
class MergeCompatibleFactsModuleConfiguration(ModuleRegistrationConfiguration):
    """``components=None`` merges every record component; a tuple restricts the
    operator to those component classes, leaving every other component's records
    untouched by this step.

    Merging folds same-key rows into one record (a ``min()`` per column), so it
    is only sound for components whose parallel same-key rows are meant to be one
    fact. Edge families that deliberately keep parallel facts stay outside the
    scope.

    Example:
        ```python
        from kg_build_system.distribution import (
            MergeCompatibleFactsModule,
            MergeCompatibleFactsModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                MergeCompatibleFactsModule,
                MergeCompatibleFactsModuleConfiguration(),
            ),
        )
        ```
    """

    components: tuple[type[Any], ...] | None = None

    def __post_init__(self) -> None:
        if self.components is not None:
            from ....declaration.languages.topology.internal import (
                component_kind,
                is_abstract_component,
            )

            values = tuple(
                _resolve_component(component) for component in self.components
            )
            for component in values:
                if (
                    not isinstance(component, type)
                    or component_kind(component) not in {"node", "edge"}
                    or is_abstract_component(component)
                ):
                    raise TypeError(
                        "components must be concrete Node or Edge classes"
                    )
            object.__setattr__(self, "components", values)

    def to_json(self) -> Any:
        return {
            "components": (
                None if self.components is None
                else [
                    {
                        "module": component.__module__,
                        "qualname": component.__qualname__,
                    }
                    for component in self.components
                ]
            ),
        }


def _resolve_component(value: Any) -> Any:
    if isinstance(value, type):
        return value
    value = thaw_object(value)
    if isinstance(value, Mapping):
        module = importlib.import_module(str(value["module"]))
        component: Any = module
        for part in str(value["qualname"]).split("."):
            component = getattr(component, part)
        return component
    raise TypeError("components must be concrete Node or Edge classes")


def component_name(component: type[Any]) -> str:
    name = getattr(component, "_component_name", None)
    if not isinstance(name, str) or not name:
        raise TypeError("components must name a declared node or edge")
    return name


class MergeCompatibleFactsModule(KernelModule):
    """Fold same-key graph records into one, keeping the minimum value.

    The operator is only sound when parallel same-key rows express one fact.
    ``MergeCompatibleFactsModuleConfiguration`` selects the components.

    Example:
        ```python
        from kg_build_system.distribution import (
            MergeCompatibleFactsModule,
            MergeCompatibleFactsModuleConfiguration, register_module,
        )

        modules = (
            register_module(
                MergeCompatibleFactsModule,
                MergeCompatibleFactsModuleConfiguration(),
            ),
        )
        ```
    """

    ID: ClassVar[str] = "merge_compatible_facts"
    VERSION: ClassVar[str] = "1"
    CONFIGURATION_TYPE: ClassVar[type[MergeCompatibleFactsModuleConfiguration]] = (
        MergeCompatibleFactsModuleConfiguration
    )

    @classmethod
    def compiler(cls, configuration: Any) -> Any:
        """Create the compiler for this module version."""
        from .compiler import MergingCompiler

        return MergingCompiler(configuration)

    @classmethod
    def executor(cls, context: ExecutorFactoryContext) -> Any:
        """Create the executor for this module version."""
        from .executor import MergingExecutor

        return MergingExecutor()


__all__ = [
    "MergeCompatibleFactsModule",
    "MergeCompatibleFactsModuleConfiguration",
    "component_name",
]
