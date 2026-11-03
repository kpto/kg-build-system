"""Blueprint DTO for the topology part.

The DTO is a semantic graph model: nodes, edges, labels, properties and
endpoints. It carries no Python module path, symbol ID or declaration
expression. ``source``, ``target`` and ``parent`` are logical graph names.
"""
from __future__ import annotations

from dataclasses import dataclass

from kg_build_system.distribution.languages.annotations.model.internal.dto import AnnotationDTO
from kg_build_system.kernel.model.internal.types.dto import LogicalTypeDTO


@dataclass(frozen=True, slots=True)
class PropertyDTO:
    """One declared graph property in the blueprint.

    Example:
        ```python
        from kg_build_system.distribution.languages.topology.model.internal.dto import (
            PropertyDTO,
        )
        from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO

        name = PropertyDTO("name", UnitTypeDTO("str"))
        ```
    """

    name: str
    logical_type: LogicalTypeDTO
    description: str | None = None
    annotations: tuple[AnnotationDTO, ...] = ()

    def __post_init__(self) -> None:
        if not self.name:
            raise ValueError("topology properties require a non-empty name")


@dataclass(frozen=True, slots=True)
class NodeDTO:
    """One node component in the blueprint.

    Example:
        ```python
        from kg_build_system.distribution.languages.topology.model.internal.dto import (
            NodeDTO,
        )

        site = NodeDTO(name="site", labels=("Site",))
        ```
    """

    name: str
    labels: tuple[str, ...] = ()
    properties: tuple[PropertyDTO, ...] = ()
    annotations: tuple[AnnotationDTO, ...] = ()
    abstract: bool = False
    parent: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        from ....service._private.validation import validate_component

        validate_component(
            self.name,
            self.labels,
            tuple(item.name for item in self.properties),
            self.parent,
            self.description,
        )


@dataclass(frozen=True, slots=True)
class EdgeDTO:
    """One directed edge component in the blueprint.

    Example:
        ```python
        from kg_build_system.distribution.languages.topology.model.internal.dto import (
            EdgeDTO,
        )

        edge = EdgeDTO(name="has_unit", source="site", target="unit")
        ```
    """

    name: str
    labels: tuple[str, ...]
    source: str
    target: str
    properties: tuple[PropertyDTO, ...] = ()
    annotations: tuple[AnnotationDTO, ...] = ()
    abstract: bool = False
    parent: str | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        from ....service._private.validation import validate_component

        validate_component(
            self.name,
            self.labels,
            tuple(item.name for item in self.properties),
            self.parent,
            self.description,
        )
        if not self.source or not self.target:
            raise ValueError(
                f"edge {self.name!r} requires a source and target graph name"
            )


@dataclass(frozen=True, slots=True)
class GraphPartDTO:
    """The complete topology part of a blueprint.

    Example:
        ```python
        from kg_build_system.distribution.languages.topology.model.internal.dto import (
            GraphPartDTO, NodeDTO,
        )

        part = GraphPartDTO(nodes=(NodeDTO("site"),), edges=())
        ```
    """

    nodes: tuple[NodeDTO, ...] = ()
    edges: tuple[EdgeDTO, ...] = ()

    def __post_init__(self) -> None:
        names = tuple(item.name for item in self.nodes) + tuple(
            item.name for item in self.edges
        )
        if len(names) != len(set(names)):
            raise ValueError("topology component names must be unique")


__all__ = ["EdgeDTO", "GraphPartDTO", "NodeDTO", "PropertyDTO"]
