"""Frozen declaration metadata and the helpers that read it.

Class creation stores one :class:`ComponentMetadata` value on the declaration.
Transcription reads only that value; the declaration class itself is authoring
syntax and never enters the graph DTO.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from kg_build_system.declaration.foundations.annotations.internal import Annotation
from kg_build_system.kernel.internal.types import LogicalType


@dataclass(frozen=True, slots=True)
class PropertyDeclaration:
    """One property resolved against a declaring class.

    Example:
        ```python
        from kg_build_system.declaration.languages.topology.internal.model import (
            PropertyDeclaration,
        )
        from kg_build_system.types import STR

        declaration = PropertyDeclaration("name", "name", STR)
        ```
    """

    attribute: str
    name: str
    logical_type: LogicalType
    authoring_type: Any = None
    description: str | None = None
    annotations: tuple[Annotation, ...] = ()

    @property
    def attr(self) -> str:
        """The attribute name, as an alias for the declaring attribute."""
        return self.attribute


@dataclass(frozen=True, slots=True)
class ComponentMetadata:
    """The declaration facts of one graph-visible component.

    Example:
        ```python
        from kg_build_system.declaration.languages.topology.internal.model import (
            ComponentMetadata,
        )

        metadata = ComponentMetadata(kind="node", name="site")
        ```
    """

    kind: Literal["node", "edge"]
    name: str
    properties: tuple[PropertyDeclaration, ...] = ()
    description: str | None = None
    source: type[Any] | None = None
    target: type[Any] | None = None
    annotations: tuple[Annotation, ...] = ()
    abstract: bool = False
    parent: type[Any] | None = None


def metadata_for(cls: type[Any]) -> ComponentMetadata | None:
    """The frozen declaration metadata owned by ``cls``, if any.

    Example:
        ```python
        from kg_build_system.declaration.languages.topology.internal.model import (
            metadata_for,
        )

        assert metadata_for(object) is None
        ```
    """
    value = vars(cls).get("_declaration")
    return value if isinstance(value, ComponentMetadata) else None


def _metadata_for(cls: type[Any]) -> ComponentMetadata | None:
    """Compatibility alias for :func:`metadata_for` inside the package."""
    return metadata_for(cls)


def properties_for(cls: type[Any]) -> dict[str, PropertyDeclaration]:
    """Resolve inherited properties with normal Python shadowing semantics.

    Example:
        ```python
        from kg_build_system.declaration.languages.topology.internal.model import (
            properties_for,
        )

        assert properties_for(object) == {}
        ```
    """
    resolved = vars(cls).get("_properties")
    if isinstance(resolved, dict):
        return resolved
    from ..._private.properties import _resolve_properties

    return {
        declaration.attribute: declaration
        for declaration in _resolve_properties(cls)
    }


def component_kind(cls: type[Any]) -> str | None:
    """``"node"`` or ``"edge"`` when the class declares a component.

    Example:
        ```python
        from kg_build_system.declaration.languages.topology.internal.model import (
            component_kind,
        )

        assert component_kind(object) is None
        ```
    """
    metadata = metadata_for(cls)
    return metadata.kind if metadata is not None else None


def is_abstract_component(cls: type[Any]) -> bool:
    """Whether the class declares an abstract category.

    Example:
        ```python
        from kg_build_system.declaration.languages.topology.internal.model import (
            is_abstract_component,
        )

        assert is_abstract_component(object) is False
        ```
    """
    metadata = metadata_for(cls)
    return metadata.abstract if metadata is not None else False


def is_concrete_component(cls: type[Any]) -> bool:
    """Whether the class declares a concrete node or edge.

    Example:
        ```python
        from kg_build_system.declaration.languages.topology.internal.model import (
            is_concrete_component,
        )

        assert is_concrete_component(object) is False
        ```
    """
    metadata = metadata_for(cls)
    return metadata is not None and not metadata.abstract


__all__ = [
    "ComponentMetadata", "PropertyDeclaration", "component_kind",
    "is_abstract_component", "is_concrete_component", "metadata_for",
    "properties_for",
]
