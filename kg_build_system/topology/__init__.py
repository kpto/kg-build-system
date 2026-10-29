"""Author-facing typed node and edge declarations.

A graph author writes ``Node``, ``Edge``, their abstract categories and
templates, ``property()`` and ``endpoint()`` here. The framework-internal
declaration helpers are :mod:`kg_build_system.topology.interfaces`; the
compilation IR is :mod:`kg_build_system.topology.ir`.
"""
from __future__ import annotations

from .declarations import property
from .models import (
    AbstractEdge,
    AbstractNode,
    Edge,
    EdgeOptions,
    EdgeOptionsTemplate,
    EdgeTemplate,
    Endpoint,
    Node,
    NodeOptions,
    NodeOptionsTemplate,
    NodeTemplate,
    PropertySlot,
    endpoint,
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
