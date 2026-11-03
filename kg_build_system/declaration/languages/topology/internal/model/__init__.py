"""The topology declaration model: frozen component metadata."""
from __future__ import annotations

from .metadata import (
    ComponentMetadata,
    PropertyDeclaration,
    component_kind,
    is_abstract_component,
    is_concrete_component,
    metadata_for,
    properties_for,
)

__all__ = [
    "ComponentMetadata", "PropertyDeclaration", "component_kind",
    "is_abstract_component", "is_concrete_component", "metadata_for",
    "properties_for",
]
