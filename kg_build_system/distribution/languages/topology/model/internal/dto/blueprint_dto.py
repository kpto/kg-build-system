"""Blueprint DTO for the topology part.

The DTO is a semantic graph model: nodes, edges, labels, properties and
endpoints. It carries no Python module path, symbol ID or declaration
expression. ``source`` and ``target`` are node references, ``parent`` names the
node or edge category above the component, and every property carries its
property reference.
"""
from __future__ import annotations

from dataclasses import dataclass

from kg_build_system.distribution.languages.annotations.model.internal.dto import AnnotationDTO
from kg_build_system.distribution.model.public.refs import (
    EdgeRef, NodeRef, PropertyRef,
)
from kg_build_system.kernel.model.internal.types.dto import LogicalTypeDTO


@dataclass(frozen=True, slots=True)
class PropertyDTO:
    """One declared graph property in the blueprint.

    Example:
        ```python
        from kg_build_system.distribution.languages.topology.model.internal.dto import (
            PropertyDTO,
        )
        from kg_build_system.distribution.model.public.refs import PropertyRef
        from kg_build_system.kernel import Key
        from kg_build_system.kernel.model.internal.types.dto import UnitTypeDTO

        prop = PropertyDTO(
            "name",
            UnitTypeDTO("str"),
            PropertyRef("topology", Key(("site.name",))),
        )
        ```
    """

    name: str
    logical_type: LogicalTypeDTO
    ref: PropertyRef
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
        from kg_build_system.distribution.model.public.refs import NodeRef
        from kg_build_system.kernel import Key

        site = NodeDTO(
            name="site",
            labels=("Site",),
            parent=NodeRef("topology", Key(("entity",))),
        )
        ```
    """

    name: str
    labels: tuple[str, ...] = ()
    properties: tuple[PropertyDTO, ...] = ()
    annotations: tuple[AnnotationDTO, ...] = ()
    abstract: bool = False
    parent: NodeRef | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        from ....service._private.validation import validate_component

        validate_component(
            self.name,
            self.labels,
            tuple(item.name for item in self.properties),
            None if self.parent is None else self.parent.name,
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
        from kg_build_system.distribution.model.public.refs import NodeRef
        from kg_build_system.kernel import Key

        edge = EdgeDTO(
            name="has_unit",
            labels=(),
            source=NodeRef("topology", Key(("site",))),
            target=NodeRef("topology", Key(("unit",))),
        )
        ```
    """

    name: str
    labels: tuple[str, ...]
    source: NodeRef
    target: NodeRef
    properties: tuple[PropertyDTO, ...] = ()
    annotations: tuple[AnnotationDTO, ...] = ()
    abstract: bool = False
    parent: EdgeRef | None = None
    description: str | None = None

    def __post_init__(self) -> None:
        from ....service._private.validation import validate_component

        validate_component(
            self.name,
            self.labels,
            tuple(item.name for item in self.properties),
            None if self.parent is None else self.parent.name,
            self.description,
        )
        if not self.source.name or not self.target.name:
            raise ValueError(
                f"edge {self.name!r} requires a source and target node reference"
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
