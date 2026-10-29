"""Framework-internal interface of the graph-topology domain.

Other subpackages import the declaration types they must inspect, the property
and endpoint declarations, and the declaration helpers here. A graph author
writes the names re-exported by :mod:`kg_build_system.topology`; the compilation
IR is :mod:`kg_build_system.topology.ir`.
"""
from __future__ import annotations

from .declarations import (
    component_kind,
    is_abstract_component,
    is_concrete_component,
    property,
)
from .models import (
    D,
    D_co,
    N_co,
    S,
    S_co,
    AbstractEdge,
    AbstractNode,
    Edge,
    EdgeOptions,
    EdgeOptionsTemplate,
    EdgeTemplate,
    Endpoint,
    GraphValue,
    Node,
    NodeOptions,
    NodeOptionsTemplate,
    NodeSideBase,
    NodeTemplate,
    NonNullableGraphValue,
    PropertySlot,
    TopologyDeclarationBase,
    endpoint,
    properties_for,
)

__all__ = [
    "AbstractEdge",
    "AbstractNode",
    "D",
    "D_co",
    "Edge",
    "EdgeOptions",
    "EdgeOptionsTemplate",
    "EdgeTemplate",
    "Endpoint",
    "GraphValue",
    "N_co",
    "Node",
    "NodeOptions",
    "NodeOptionsTemplate",
    "NodeSideBase",
    "NodeTemplate",
    "NonNullableGraphValue",
    "PropertySlot",
    "TopologyDeclarationBase",
    "S",
    "S_co",
    "component_kind",
    "endpoint",
    "is_abstract_component",
    "is_concrete_component",
    "properties_for",
    "property",
]
