"""Author-facing topology declarations, options and reference helpers.

Example:
    ```python
    from kg_build_system.declaration.languages.topology import (
        Edge, Node, PropertySlot, property,
    )

    class SiteNode(Node):
        name: PropertySlot[str] = property()

    class HasUnitEdge(Edge[SiteNode, SiteNode]):
        since: PropertySlot[str | None] = property()
    ```
"""
from __future__ import annotations

from .model import (
    AbstractEdge, AbstractNode, Edge, EdgeOptions, EdgeOptionsTemplate,
    EdgeTemplate, Endpoint, Node, NodeOptions, NodeOptionsTemplate,
    NodeTemplate, PropertySlot, endpoint, property,
)

__all__ = [
    "AbstractEdge", "AbstractNode", "Edge", "EdgeOptions",
    "EdgeOptionsTemplate", "EdgeTemplate", "Endpoint", "Node", "NodeOptions",
    "NodeOptionsTemplate", "NodeTemplate", "PropertySlot", "endpoint",
    "property",
]
