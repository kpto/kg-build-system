"""Declaration helpers shared by the topology authoring and internal surfaces."""
from __future__ import annotations

from typing import Any

from .models import property


def component_kind(cls: type[Any]) -> str | None:
    """``"node"`` or ``"edge"`` when the class is a declared component."""
    kind = vars(cls).get("_component_declaration_kind")
    return kind if kind in {"node", "edge"} else None


def is_abstract_component(cls: type[Any]) -> bool:
    """Whether the class declares an abstract category."""
    return bool(vars(cls).get("_component_abstract", False))


def is_concrete_component(cls: type[Any]) -> bool:
    """Whether the class declares a concrete node or edge."""
    return component_kind(cls) is not None and not is_abstract_component(cls)


__all__ = [
    "component_kind",
    "is_abstract_component",
    "is_concrete_component",
    "property",
]
