"""Options an author assigns to a node, edge or template declaration.

Options carry graph identity and portable annotations. A concrete or abstract
component uses ``NodeOptions`` or ``EdgeOptions``; an inert template uses the
matching ``*OptionsTemplate``, which has no name or description.

Example:
    ```python
    from kg_build_system import Edge, EdgeLabel, EdgeOptions, Node, NodeOptions

    class SiteNode(Node):
        options = NodeOptions(name="site")

    class UnitNode(Node):
        ...

    class HasUnitEdge(Edge[SiteNode, UnitNode]):
        options = EdgeOptions(
            name="has_unit",
            annotations=(EdgeLabel("HAS_UNIT"),),
        )
    ```
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from kg_build_system.declaration.foundations.annotations.model.public import (
    Annotation,
)
from kg_build_system.declaration.foundations.annotations.service.internal import (
    annotation_tuple,
)


@dataclass(frozen=True, slots=True)
class NodeOptions:
    """Identity and annotations for a concrete or abstract node.

    Example:
        ```python
        from kg_build_system import Node, NodeOptions, PropertySlot, property

        class SiteNode(Node):
            options = NodeOptions(name="site", description="A monitored site.")
            name: PropertySlot[str] = property()
        ```
    """

    name: str | None = None
    description: str | None = None
    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


@dataclass(frozen=True, slots=True)
class EdgeOptions:
    """Identity and annotations for a concrete or abstract edge.

    Example:
        ```python
        from kg_build_system import Edge, EdgeLabel, EdgeOptions, Node

        class SiteNode(Node):
            ...

        class HasUnitEdge(Edge[SiteNode, SiteNode]):
            options = EdgeOptions(
                name="has_unit",
                annotations=(EdgeLabel("HAS_UNIT"),),
            )
        ```
    """

    name: str | None = None
    description: str | None = None
    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


@dataclass(frozen=True, slots=True)
class NodeOptionsTemplate:
    """Annotations-only options for a node-side template.

    Example:
        ```python
        from kg_build_system import NodeLabel, NodeOptionsTemplate, NodeTemplate

        class ProvenancedNodeTemplate(NodeTemplate):
            options = NodeOptionsTemplate(
                annotations=(NodeLabel("Provenanced"),),
            )
        ```
    """

    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


@dataclass(frozen=True, slots=True)
class EdgeOptionsTemplate:
    """Annotations-only options for an edge-side template.

    Example:
        ```python
        from kg_build_system import EdgeLabel, EdgeOptionsTemplate, EdgeTemplate

        class ProvenancedEdgeTemplate(EdgeTemplate):
            options = EdgeOptionsTemplate(
                annotations=(EdgeLabel("PROVENANCED"),),
            )
        ```
    """

    annotations: Sequence[Annotation] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


__all__ = [
    "EdgeOptions", "EdgeOptionsTemplate", "NodeOptions", "NodeOptionsTemplate",
]
