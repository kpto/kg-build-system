"""Frozen declaration metadata and the helpers that read it.

Class creation stores one :class:`ComponentMetadata` value on the declaration;
lowering and other subpackages read only that value.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from ...annotations.internal import Annotation
from ...types.internal import LogicalType


@dataclass(frozen=True, slots=True)
class PropertyDeclaration:
    """One property resolved against a declaring class."""

    attribute: str
    name: str
    logical_type: LogicalType
    authoring_type: Any = None
    description: str | None = None
    annotations: tuple[Annotation, ...] = ()

    @property
    def attr(self) -> str:
        return self.attribute


@dataclass(frozen=True, slots=True)
class ComponentMetadata:
    """The declaration facts of one graph-visible component."""

    kind: Literal["node", "edge"]
    name: str
    properties: tuple[PropertyDeclaration, ...] = ()
    description: str | None = None
    source: type[Any] | None = None
    target: type[Any] | None = None
    annotations: tuple[Annotation, ...] = ()
    abstract: bool = False
    parent: type[Any] | None = None


def _metadata_for(cls: type[Any]) -> ComponentMetadata | None:
    """The frozen declaration metadata owned by ``cls``, if any."""
    value = vars(cls).get("_declaration")
    return value if isinstance(value, ComponentMetadata) else None


def properties_for(cls: type[Any]) -> dict[str, PropertyDeclaration]:
    """Resolve inherited properties with normal Python shadowing semantics."""
    resolved = vars(cls).get("_properties")
    if isinstance(resolved, dict):
        return resolved
    from .._private.properties import _resolve_properties

    return {
        declaration.attribute: declaration
        for declaration in _resolve_properties(cls)
    }


def component_kind(cls: type[Any]) -> str | None:
    """``"node"`` or ``"edge"`` when the class declares a component."""
    metadata = _metadata_for(cls)
    return metadata.kind if metadata is not None else None


def is_abstract_component(cls: type[Any]) -> bool:
    """Whether the class declares an abstract category."""
    metadata = _metadata_for(cls)
    return metadata.abstract if metadata is not None else False


def is_concrete_component(cls: type[Any]) -> bool:
    """Whether the class declares a concrete node or edge."""
    metadata = _metadata_for(cls)
    return metadata is not None and not metadata.abstract


__all__ = [
    "ComponentMetadata", "PropertyDeclaration", "component_kind",
    "is_abstract_component", "is_concrete_component", "properties_for",
]
