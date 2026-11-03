"""Author-facing typed node and edge declarations.

The authoring model lives in
:mod:`kg_build_system.declaration.languages.topology.model.public`; the
authoring functions live in
:mod:`kg_build_system.declaration.languages.topology.service.public`.
"""
from __future__ import annotations

from .model.public import (
    AbstractEdge, AbstractNode, Edge, EdgeOptions, EdgeOptionsTemplate,
    EdgeTemplate, Endpoint, Node, NodeOptions, NodeOptionsTemplate, NodeTemplate,
    PropertySlot,
)
from .service.public import endpoint, property

__all__ = [
    "AbstractEdge",
    "AbstractNode",
    "Edge",
    "EdgeOptions",
    "EdgeOptionsTemplate",
    "EdgeTemplate",
    "Endpoint",
    "Node",
    "NodeOptions",
    "NodeOptionsTemplate",
    "NodeTemplate",
    "PropertySlot",
    "endpoint",
    "property",
]
