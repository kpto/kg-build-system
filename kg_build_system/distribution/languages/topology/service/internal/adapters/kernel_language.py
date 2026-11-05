"""The topology language: node and edge declarations, symbols and source."""
from __future__ import annotations

from collections.abc import Iterable
from typing import Any

from kg_build_system.kernel import (
    Declaration,
    Key,
    Language,
    Namespace,
    RenderContext,
    SourceFragment,
    Symbol,
    SymbolContext,
    SymbolRef,
)

from ....model.internal.dto.blueprint_dto import EdgeDTO, GraphPartDTO, NodeDTO
from ..source import render_graph_source
from ..transcription import collect_components
from ..._private.symbols import (
    PropertyEntry,
    declaration_kind,
    declaration_name,
    declaration_references,
    property_declarations,
    symbol_for_declaration,
    value_identity,
)


class TopologyLanguage(Language):
    """The topology language: ``node``, ``edge`` and ``property`` symbols.

    Collection includes abstract parents and edge endpoint categories even when
    a namespace only exposes bindings. Each declared property is its own
    declaration so the closure walk can reach it from its component.

    Example:
        ```python
        from kg_build_system.distribution.languages.topology.service.internal import (
            TopologyLanguage,
        )

        language = TopologyLanguage()
        assert language.name == "topology"
        ```
    """

    name = "topology"

    def discover_declarations(
        self, namespace: Namespace,
    ) -> Iterable[Declaration]:
        """Select every graph-visible declaration and property from a namespace.

        Example:
            ```python
            declarations = TopologyLanguage().discover_declarations(namespace)
            ```
        """
        components = tuple(collect_components(namespace))
        declarations: list[Declaration] = [
            Declaration(component) for component in components
        ]
        for component in components:
            declarations.extend(
                Declaration(prop)
                for prop in property_declarations(component)
            )
        return tuple(declarations)

    def compute_key(self, declaration: Declaration) -> Key:
        """Return the graph-name key of a node, edge or property declaration.

        Example:
            ```python
            key = TopologyLanguage().compute_key(declaration)
            ```
        """
        value = declaration.value
        if isinstance(value, PropertyEntry):
            owner = declaration_name(value.owner)
            return Key((f"{owner}.{value.declaration.name}",))
        return Key((declaration_name(value),))

    def get_kind(self, declaration: Declaration) -> str:
        """Return ``node``, ``edge`` or ``property``.

        Example:
            ```python
            kind = TopologyLanguage().get_kind(declaration)
            ```
        """
        value = declaration.value
        if isinstance(value, PropertyEntry):
            return "property"
        return declaration_kind(value)

    def get_identity(self, value: Any) -> SymbolRef | None:
        """Return the topology reference of an authoring value.

        Example:
            ```python
            reference = TopologyLanguage().get_identity(declaration.value)
            ```
        """
        return value_identity(value)

    def get_references(
        self, value: Any, resolver: Any,
    ) -> tuple[SymbolRef, ...]:
        """Return the direct dependencies an authoring topology value declares.

        A node names its property declarations and its parent category; an edge
        also names its source and target nodes. The value is authoring topology,
        never a transcribed DTO.

        Example:
            ```python
            references = TopologyLanguage().get_references(declaration.value, resolver)
            ```
        """
        del resolver
        return declaration_references(value)

    def transcribe(
        self, declaration: Declaration, context: SymbolContext,
    ) -> Symbol:
        """Transcribe one node, edge or property declaration into one symbol.

        Example:
            ```python
            symbol = TopologyLanguage().transcribe(declaration, context)
            ```
        """
        del context
        return symbol_for_declaration(declaration.value)

    def render(
        self, symbol: Any, context: RenderContext,
    ) -> SourceFragment:
        """Render a topology symbol, fragment or whole graph part to source.

        Example:
            ```python
            fragment = TopologyLanguage().render(blueprint.graph, None)
            ```
        """
        value = symbol.value if isinstance(symbol, Symbol) else symbol
        if isinstance(value, NodeDTO):
            value = GraphPartDTO(nodes=(value,), edges=())
        elif isinstance(value, EdgeDTO):
            value = GraphPartDTO(nodes=(), edges=(value,))
        return render_graph_source(value, context)


__all__ = ["TopologyLanguage"]
