"""Options an author assigns to a node, edge or template declaration.

Options carry graph identity, portable annotations and a declaration meaning
fragment. A concrete or abstract component uses ``NodeOptions`` or
``EdgeOptions``; an inert template uses the matching ``*OptionsTemplate``, which
has no name or description.

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
from typing import TYPE_CHECKING

from kg_build_system.distribution.languages.annotations.model.public import (
    Annotation,
)
from kg_build_system.distribution.languages.annotations.service.internal import (
    annotation_tuple,
)
from ..internal.model.metadata import require_meaning

if TYPE_CHECKING:
    from kg_build_system.distribution.languages.meaning.model.public import (
        Meaning,
    )


@dataclass(frozen=True, slots=True)
class NodeOptions:
    """Identity, annotations and meaning for a concrete or abstract node.

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
    meaning: Meaning | None = None

    def __post_init__(self) -> None:
        require_meaning(self.meaning, "node")
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


@dataclass(frozen=True, slots=True)
class EdgeOptions:
    """Identity, annotations and meaning for a concrete or abstract edge.

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
    meaning: Meaning | None = None

    def __post_init__(self) -> None:
        require_meaning(self.meaning, "edge")
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


@dataclass(frozen=True, slots=True)
class NodeOptionsTemplate:
    """Identity-free annotations and meaning for a node-side template.

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
    meaning: Meaning | None = None

    def __post_init__(self) -> None:
        require_meaning(self.meaning, "node template")
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


@dataclass(frozen=True, slots=True)
class EdgeOptionsTemplate:
    """Identity-free annotations and meaning for an edge-side template.

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
    meaning: Meaning | None = None

    def __post_init__(self) -> None:
        require_meaning(self.meaning, "edge template")
        object.__setattr__(self, "annotations", annotation_tuple(list(self.annotations)))


__all__ = [
    "EdgeOptions", "EdgeOptionsTemplate", "NodeOptions", "NodeOptionsTemplate",
]
