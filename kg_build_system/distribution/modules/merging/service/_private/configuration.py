"""Component-name access for the merging planner."""
from __future__ import annotations

from typing import Any


def component_name(component: type[Any]) -> str:
    """The graph name of one declared component class."""
    name = getattr(component, "_component_name", None)
    if not isinstance(name, str) or not name:
        raise TypeError("components must name a declared node or edge")
    return name


__all__ = ["component_name"]
