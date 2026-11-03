"""Author-facing node-side and edge-side declaration classes."""
from __future__ import annotations

from .declarations import (
    AbstractEdge,
    AbstractNode,
    Edge,
    EdgeTemplate,
    Endpoint,
    Node,
    NodeTemplate,
    PropertySlot,
    endpoint,
    property,
)
from .options import (
    EdgeOptions,
    EdgeOptionsTemplate,
    NodeOptions,
    NodeOptionsTemplate,
)

__all__ = [
    "AbstractEdge", "AbstractNode", "Edge", "EdgeOptions",
    "EdgeOptionsTemplate", "EdgeTemplate", "Endpoint", "Node", "NodeOptions",
    "NodeOptionsTemplate", "NodeTemplate", "PropertySlot", "endpoint",
    "property",
]
