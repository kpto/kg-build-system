"""Validation and JSON form of the merging module's component scope."""
from __future__ import annotations

import importlib
from collections.abc import Mapping
from typing import Any

from ...service.runtime import thaw_object
from .....declaration.languages.topology.internal import (
    component_kind,
    is_abstract_component,
)


def resolve_components(
    components: tuple[Any, ...] | None,
) -> tuple[Any, ...] | None:
    """Resolve configured component references and check they are concrete."""
    if components is None:
        return None
    values = tuple(_resolve_component(component) for component in components)
    for component in values:
        if (
            not isinstance(component, type)
            or component_kind(component) not in {"node", "edge"}
            or is_abstract_component(component)
        ):
            raise TypeError("components must be concrete Node or Edge classes")
    return values


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
    """The graph name of one declared component class."""
    name = getattr(component, "_component_name", None)
    if not isinstance(name, str) or not name:
        raise TypeError("components must name a declared node or edge")
    return name


__all__ = ["component_name", "components_json", "resolve_components"]
