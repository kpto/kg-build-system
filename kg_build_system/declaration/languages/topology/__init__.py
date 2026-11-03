"""Author-facing typed node and edge declarations.

A graph author writes ``Node``, ``Edge``, their abstract categories and
templates, ``property()`` and ``endpoint()`` here. The public declarations and
options live in :mod:`kg_build_system.declaration.languages.topology.public`;
the internal model, DTO and language live in
:mod:`kg_build_system.declaration.languages.topology.internal`.
"""
from __future__ import annotations

from .public import (
    AbstractEdge, AbstractNode, Edge, EdgeOptions, EdgeOptionsTemplate,
    EdgeTemplate, Endpoint, Node, NodeOptions, NodeOptionsTemplate,
    NodeTemplate, PropertySlot, endpoint, property,
)

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
