"""Framework-internal interface of the graph-topology domain.

Another subpackage reads declaration facts with the helpers here and lowers a
build through :class:`TopologyLanguage`. A graph author writes the names in
:mod:`kg_build_system.topology`; the compilation IR is
:mod:`kg_build_system.topology.ir`.
"""
from __future__ import annotations

from .ir import ComponentIR, PropertyIR
from .language import (
    TopologyLanguage, component_ir, decode_component, decode_topology_part,
    effective_components, encode_component, encode_topology_part, symbol_id,
)
from .models import (
    D,
    D_co,
    N_co,
    S,
    S_co,
    AbstractEdge,
    AbstractNode,
    ComponentMetadata,
    Edge,
    EdgeOptions,
    EdgeOptionsTemplate,
    EdgeTemplate,
    Endpoint,
    GraphScalar,
    GraphValue,
    Node,
    NodeOptions,
    NodeOptionsTemplate,
    NodeSideBase,
    NodeTemplate,
    NonNullableGraphValue,
    PropertyDeclaration,
    PropertySlot,
    TopologyDeclarationBase,
    component_kind,
    endpoint,
    is_abstract_component,
    is_concrete_component,
    properties_for,
    property,
)

__all__ = [
    "AbstractEdge", "AbstractNode", "ComponentIR", "ComponentMetadata",
    "D", "D_co", "Edge", "EdgeOptions", "EdgeOptionsTemplate", "EdgeTemplate",
    "Endpoint", "GraphScalar", "GraphValue", "N_co", "Node", "NodeOptions",
    "NodeOptionsTemplate", "NodeSideBase", "NodeTemplate",
    "NonNullableGraphValue", "PropertyDeclaration", "PropertyIR",
    "PropertySlot", "S", "S_co", "TopologyDeclarationBase", "TopologyLanguage",
    "component_ir", "component_kind", "decode_component",
    "decode_topology_part", "effective_components", "encode_component",
    "encode_topology_part", "endpoint", "is_abstract_component",
    "is_concrete_component", "properties_for", "property", "symbol_id",
]
