"""The compatible-facts merging module's configuration."""
from __future__ import annotations

import importlib
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from kg_build_system.declaration.languages.topology.service.internal import component_kind, is_abstract_component
from .....kernel.model.internal.json import FrozenObject, thaw_json
from ..registration import ModuleRegistrationConfiguration


def resolve_components(
    components: tuple[Any, ...] | None,
) -> tuple[Any, ...] | None:
    """Resolve configured component references and check they are concrete."""
    if components is None:
        return None
    values = tuple(resolve_component(component) for component in components)
    for component in values:
        if (
            not isinstance(component, type)
            or component_kind(component) not in {"node", "edge"}
            or is_abstract_component(component)
        ):
            raise TypeError("components must be concrete Node or Edge classes")
    return values


def resolve_component(value: Any) -> Any:
    """Resolve one configured component class from a class or stored reference."""
    if isinstance(value, type):
        return value
    if isinstance(value, FrozenObject):
        value = thaw_json(value)
    if isinstance(value, Mapping):
        module = importlib.import_module(str(value["module"]))
        component: Any = module
        for part in str(value["qualname"]).split("."):
            component = getattr(component, part)
        return component
    raise TypeError("components must be concrete Node or Edge classes")


def components_json(components: tuple[Any, ...] | None) -> Any:
    """The JSON-compatible form of the configured component scope."""
    return {
        "components": (
            None if components is None
            else [
                {
                    "module": component.__module__,
                    "qualname": component.__qualname__,
                }
                for component in components
            ]
        ),
    }


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
        object.__setattr__(self, "components", resolve_components(self.components))

    def to_json(self) -> Any:
        return components_json(self.components)


__all__ = [
    "MergeCompatibleFactsModuleConfiguration",
    "components_json",
    "resolve_component",
    "resolve_components",
]
