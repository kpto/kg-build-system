"""Internal topology model: metadata, declaration helpers, IR and language."""
from __future__ import annotations

from .adapters.kernel_language import (
    TopologyLanguage, component_ir, decode_component, decode_topology_part,
    encode_component, encode_topology_part, symbol_id,
)
from .ir import ComponentIR, PropertyIR
from .metadata import (
    ComponentMetadata, PropertyDeclaration, component_kind,
    is_abstract_component, is_concrete_component, properties_for,
)

__all__ = [
    "ComponentIR", "ComponentMetadata", "PropertyDeclaration",
    "PropertyIR", "TopologyLanguage", "component_ir", "component_kind",
    "decode_component", "decode_topology_part", "encode_component",
    "encode_topology_part", "is_abstract_component",
    "is_concrete_component", "properties_for", "symbol_id",
]
