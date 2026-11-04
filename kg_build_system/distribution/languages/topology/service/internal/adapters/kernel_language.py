"""The topology language: node and edge declarations, symbols and source."""
from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
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
from ..transcription import (
    collect_components, transcribe_graph_part, validate_graph_part,
)
from ..._private.symbols import (
    declaration_kind,
    declaration_name,
    owns_value,
    symbols_for_part,
    value_identity,
    value_references,
)


class TopologyLanguage(Language):
    """The topology language: ``node`` and ``edge`` symbols.

    Collection includes abstract parents and edge endpoint categories even when
    a namespace only exposes bindings.

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
        """Select every graph-visible declaration reachable from the namespace.

        Example:
            ```python
            declarations = TopologyLanguage().discover_declarations(namespace)
            ```
        """
        return tuple(
            Declaration(value) for value in collect_components(namespace)
        )

    def compute_key(self, declaration: Declaration) -> Key:
        """Return the graph-name key of a node or edge declaration.

        Example:
            ```python
            key = TopologyLanguage().compute_key(declaration)
            ```
        """
        return Key((declaration_name(declaration.value),))

    def get_kind(self, declaration: Declaration) -> str:
        """Return ``node`` or ``edge``.

        Example:
            ```python
            kind = TopologyLanguage().get_kind(declaration)
            ```
        """
        return declaration_kind(declaration.value)

    def owns(self, value: Any) -> bool:
        """Whether a value is a topology declaration or DTO fragment.

        Example:
            ```python
            assert TopologyLanguage().owns(declaration.value)
            ```
        """
        return owns_value(value)

    def get_identity(self, value: Any) -> SymbolRef | None:
        """Return the topology reference of a declaration or DTO fragment.

        Example:
            ```python
            reference = TopologyLanguage().get_identity(declaration.value)
            ```
        """
        return value_identity(value)

    def get_references(
        self, value: Any, resolver: Any,
    ) -> tuple[SymbolRef, ...]:
        """Return the references a transcribed node or edge DTO declares.

        The value is a DTO fragment for this wave; the linker calls this method
        after transcription.

        Example:
            ```python
            references = TopologyLanguage().get_references(fragment, resolver)
            ```
        """
        del resolver
        return value_references(value)

    def transcribe_many(
        self, declarations: Sequence[Declaration], context: SymbolContext,
    ) -> Mapping[SymbolRef, Symbol]:
        """Transcribe a batch of topology declarations and split the DTO.

        Example:
            ```python
            symbols = TopologyLanguage().transcribe_many(declarations, context)
            ```
        """
        del context
        part = transcribe_graph_part(
            tuple(declaration.value for declaration in declarations),
        )
        validate_graph_part(part)
        return symbols_for_part(part)

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
