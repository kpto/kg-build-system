"""Component-name access for the merging module."""
from __future__ import annotations

from typing import Any

from .....model.public.modules.merging import (
    components_json,
    resolve_components,
)


def component_name(component: type[Any]) -> str:
    """The graph name of one declared component class."""
    name = getattr(component, "_component_name", None)
    if not isinstance(name, str) or not name:
        raise TypeError("components must name a declared node or edge")
    return name


__all__ = ["component_name", "components_json", "resolve_components"]
