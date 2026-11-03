"""Frozen declaration metadata.

Class creation stores one :class:`ComponentMetadata` value on the declaration.
Transcription reads only that value; the declaration class itself is authoring
syntax and never enters the graph DTO.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

from kg_build_system.declaration.foundations.annotations.model.public import (
    Annotation,
)
from kg_build_system.kernel.model.public.types import LogicalType


@dataclass(frozen=True, slots=True)
class PropertyDeclaration:
    """One property resolved against a declaring class.

    Example:
        ```python
        from kg_build_system.declaration.languages.topology.model.internal.model import (
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
        from kg_build_system.declaration.languages.topology.model.internal.model import (
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


__all__ = ["ComponentMetadata", "PropertyDeclaration"]
