"""Read the frozen declaration metadata owned by a topology declaration."""
from __future__ import annotations

from typing import Any

from ..internal.model.metadata import ComponentMetadata, PropertyDeclaration
from .properties import _resolve_properties


def metadata_for(cls: type[Any]) -> ComponentMetadata | None:
    """The frozen declaration metadata owned by ``cls``, if any."""
    value = vars(cls).get("_declaration")
    return value if isinstance(value, ComponentMetadata) else None


def properties_for(cls: type[Any]) -> dict[str, PropertyDeclaration]:
    """Resolve inherited properties with normal Python shadowing semantics."""
    resolved = vars(cls).get("_properties")
    if isinstance(resolved, dict):
        return resolved
    return {
        declaration.attribute: declaration
        for declaration in _resolve_properties(cls)
    }


def component_kind(cls: type[Any]) -> str | None:
    """``"node"`` or ``"edge"`` when the class declares a component."""
    metadata = metadata_for(cls)
    return metadata.kind if metadata is not None else None


def is_abstract_component(cls: type[Any]) -> bool:
    """Whether the class declares an abstract category."""
    metadata = metadata_for(cls)
    return metadata.abstract if metadata is not None else False


def is_concrete_component(cls: type[Any]) -> bool:
    """Whether the class declares a concrete node or edge."""
    metadata = metadata_for(cls)
    return metadata is not None and not metadata.abstract


__all__ = [
    "component_kind", "is_abstract_component", "is_concrete_component",
    "metadata_for", "properties_for",
]
