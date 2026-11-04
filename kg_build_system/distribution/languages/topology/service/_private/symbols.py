"""Project the topology language DTO into linked symbols.

A node and an edge are symbols; each declared property is a symbol too. Property
keys join the component name and the property name with a dot, so node ``site``
and property ``name`` produce ``Key(("site.name",))``.
"""
from __future__ import annotations

from typing import Any

from kg_build_system.distribution.model.public.refs import (
    NodeRef, PropertyRef,
)
from kg_build_system.kernel import Key, Symbol, SymbolRef

from ...model.internal.dto.blueprint_dto import (
    EdgeDTO, GraphPartDTO, NodeDTO, PropertyDTO,
)
from .metadata import component_kind, metadata_for


def declaration_name(value: Any) -> str:
    """Return the graph name of one node or edge declaration."""
    metadata = metadata_for(value)
    if metadata is None:
        raise TypeError(f"topology declaration {value!r} has no graph name")
    return metadata.name


def declaration_kind(value: Any) -> str:
    """Return ``node`` or ``edge`` for one topology declaration."""
    kind = component_kind(value)
    if kind is None:
        raise TypeError(f"topology declaration {value!r} has no kind")
    return kind


def _node_ref(name: str) -> NodeRef:
    return NodeRef("topology", Key((name,)))


def owns_value(value: Any) -> bool:
    """Whether the topology language owns an authoring value or DTO."""
    if isinstance(value, type) and metadata_for(value) is not None:
        return True
    return isinstance(value, (NodeDTO, EdgeDTO, PropertyDTO))


def value_identity(value: Any) -> SymbolRef | None:
    """Return the topology reference of a declaration or DTO fragment."""
    if isinstance(value, PropertyDTO):
        return value.ref.symbol
    if isinstance(value, NodeDTO):
        return _node_ref(value.name).symbol
    if isinstance(value, EdgeDTO):
        return SymbolRef("topology", Key((value.name,)))
    if isinstance(value, type) and metadata_for(value) is not None:
        return SymbolRef("topology", Key((declaration_name(value),)))
    return None


def value_references(value: Any) -> tuple[SymbolRef, ...]:
    """Return the references a topology DTO fragment declares.

    A property declares no outgoing reference. A node refers to its property
    symbols and its parent node; an edge also refers to its source and target
    nodes.
    """
    if isinstance(value, PropertyDTO):
        return ()
    if isinstance(value, NodeDTO):
        references: list[SymbolRef] = [
            prop.ref.symbol for prop in value.properties
        ]
        if value.parent is not None:
            references.append(value.parent.symbol)
        return tuple(dict.fromkeys(references))
    if isinstance(value, EdgeDTO):
        references = [prop.ref.symbol for prop in value.properties]
        if value.parent is not None:
            references.append(value.parent.symbol)
        references.extend((value.source.symbol, value.target.symbol))
        return tuple(dict.fromkeys(references))
    return ()


def _property_symbols(
    component: NodeDTO | EdgeDTO,
) -> dict[SymbolRef, Symbol]:
    symbols: dict[SymbolRef, Symbol] = {}
    for prop in component.properties:
        reference = prop.ref.symbol
        symbols[reference] = Symbol(
            reference.key, "property", prop,
        )
    return symbols


def symbols_for_part(part: GraphPartDTO) -> dict[SymbolRef, Symbol]:
    """Split one topology DTO into one symbol per component and property."""
    symbols: dict[SymbolRef, Symbol] = {}
    for node in part.nodes:
        reference = _node_ref(node.name)
        symbols[reference.symbol] = Symbol(
            reference.key, "node", node, value_references(node),
        )
        symbols.update(_property_symbols(node))
    for edge in part.edges:
        reference = SymbolRef("topology", Key((edge.name,)))
        symbols[reference] = Symbol(
            reference.key, "edge", edge, value_references(edge),
        )
        symbols.update(_property_symbols(edge))
    return symbols


__all__ = [
    "declaration_kind", "declaration_name", "owns_value", "symbols_for_part",
    "value_identity", "value_references",
]
