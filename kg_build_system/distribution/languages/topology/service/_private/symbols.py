"""Project topology declarations and properties into linked symbols.

A node and an edge are symbols; each declared property is a symbol too. Property
keys join the component name and the property name with a dot, so node ``site``
and property ``name`` produce ``Key(("site.name",))``. References are read from
the frozen authoring metadata, never from a transcribed DTO.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from kg_build_system.distribution.model.public.refs import (
    EdgeRef, NodeRef, PropertyRef,
)
from kg_build_system.kernel import Key, Symbol, SymbolRef

from ...model.internal.dto.blueprint_dto import (
    EdgeDTO, NodeDTO, PropertyDTO,
)
from ...model.internal.model.metadata import PropertyDeclaration
from .metadata import component_kind, metadata_for
from .transcription import _edges_of, _nodes_of, _property_dto


@dataclass(frozen=True, slots=True)
class PropertyEntry:
    """One declared property offered to the linker as its own declaration."""

    owner: type[Any]
    declaration: PropertyDeclaration


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


def _edge_ref(name: str) -> EdgeRef:
    return EdgeRef("topology", Key((name,)))


def _property_ref(owner: str, name: str) -> PropertyRef:
    return PropertyRef("topology", Key((f"{owner}.{name}",)))


def property_key(owner: str, name: str) -> Key:
    """Return the key of one property declared by a component."""
    return _property_ref(owner, name).key


def property_declarations(component: type[Any]) -> tuple[PropertyEntry, ...]:
    """Return one property declaration per property of ``component``."""
    metadata = metadata_for(component)
    if metadata is None:
        return ()
    return tuple(
        PropertyEntry(component, prop) for prop in metadata.properties
    )


def value_identity(value: Any) -> SymbolRef | None:
    """Return the topology reference of an authoring value or DTO."""
    if isinstance(value, PropertyEntry):
        owner = declaration_name(value.owner)
        return _property_ref(owner, value.declaration.name).symbol
    if isinstance(value, PropertyDTO):
        return value.ref.symbol
    if isinstance(value, NodeDTO):
        return _node_ref(value.name).symbol
    if isinstance(value, EdgeDTO):
        return _edge_ref(value.name).symbol
    if isinstance(value, type) and metadata_for(value) is not None:
        return SymbolRef("topology", Key((declaration_name(value),)))
    return None


def declaration_references(value: Any) -> tuple[SymbolRef, ...]:
    """Return the direct dependencies an authoring topology value declares.

    A node names its properties and its parent category. An edge also names its
    source and target nodes. A property declares no outgoing reference.
    """
    if isinstance(value, PropertyEntry):
        return ()
    metadata = metadata_for(value)
    if metadata is None:
        return ()
    references: list[SymbolRef] = [
        _property_ref(metadata.name, prop.name).symbol
        for prop in metadata.properties
    ]
    if metadata.parent is not None:
        if metadata.kind == "node":
            references.append(_node_ref(declaration_name(metadata.parent)).symbol)
        else:
            references.append(_edge_ref(declaration_name(metadata.parent)).symbol)
    if metadata.kind == "edge":
        if metadata.source is not None:
            references.append(_node_ref(declaration_name(metadata.source)).symbol)
        if metadata.target is not None:
            references.append(_node_ref(declaration_name(metadata.target)).symbol)
    return tuple(dict.fromkeys(references))


def _validate_parent_chain(metadata: Any) -> None:
    """Reject a concrete or cyclic parent category before transcription."""
    seen: set[str] = set()
    current = metadata
    while current.parent is not None:
        if current.name in seen:
            raise ValueError(
                f"component parent chain cycle includes {current.name!r}"
            )
        seen.add(current.name)
        parent = metadata_for(current.parent)
        if parent is None:
            raise ValueError(
                f"component {current.name!r} parent "
                f"{declaration_name(current.parent)!r} is not a graph component"
            )
        if not parent.abstract:
            raise ValueError(
                f"component {current.name!r} parent {parent.name!r} "
                "is not abstract"
            )
        current = parent


def symbol_for_declaration(value: Any) -> Symbol:
    """Transcribe one node, edge or property declaration into one symbol."""
    if isinstance(value, PropertyEntry):
        metadata = metadata_for(value.owner)
        assert metadata is not None
        prop = _property_dto(metadata.name, value.declaration)
        return Symbol(
            property_key(metadata.name, value.declaration.name),
            "property",
            prop,
        )
    metadata = metadata_for(value)
    if metadata is None:
        raise TypeError(f"topology declaration {value!r} has no metadata")
    _validate_parent_chain(metadata)
    if metadata.kind == "node":
        dto = _nodes_of((value,))[metadata.name]
        return Symbol(
            Key((metadata.name,)), "node", dto,
            declaration_references(value),
        )
    dto = _edges_of((value,))[metadata.name]
    return Symbol(
        Key((metadata.name,)), "edge", dto,
        declaration_references(value),
    )


__all__ = [
    "PropertyEntry", "declaration_kind", "declaration_name",
    "declaration_references", "property_declarations", "property_key",
    "symbol_for_declaration", "value_identity",
]
