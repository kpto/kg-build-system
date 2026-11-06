"""Kernel language adapter for the graph language."""
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

from ....model.internal.dto.graph_dto import GraphDeclarationDTO
from ..._private.declarations import is_graph_declaration
from ..._private.symbols import symbol_for_declaration, value_identity
from ..source import render_graph_declaration_source


class GraphLanguage(Language):
    """The graph language: at most one ``graph`` symbol per namespace.

    A namespace may contain zero graph declarations. More than one is an error
    at discovery because the project has exactly one meaning root.

    Example:
        ```python
        from kg_build_system.distribution.languages.graph.service.internal import (
            GraphLanguage,
        )

        language = GraphLanguage()
        assert language.name == "graph"
        ```
    """

    name = "graph"

    def discover_declarations(
        self, namespace: Namespace,
    ) -> Iterable[Declaration]:
        """Select the one concrete ``Graph`` subclass in a namespace.

        Zero declarations are allowed. Two or more raise ``ValueError``.

        Example:
            ```python
            declarations = GraphLanguage().discover_declarations(namespace)
            ```
        """
        found: list[type[Any]] = []
        seen: set[type[Any]] = set()
        for value in namespace.values():
            if not is_graph_declaration(value) or value in seen:
                continue
            seen.add(value)
            found.append(value)
        if len(found) > 1:
            names = ", ".join(sorted(item.__name__ for item in found))
            raise ValueError(
                "a namespace may declare at most one Graph; found " + names
            )
        return tuple(Declaration(value) for value in found)

    def compute_key(self, declaration: Declaration) -> Key:
        """Return the graph-name key of one declaration.

        Example:
            ```python
            key = GraphLanguage().compute_key(declaration)
            ```
        """
        value = declaration.value
        if not is_graph_declaration(value):
            raise TypeError(f"{value!r} is not a graph declaration")
        return Key((value._graph_name,))

    def get_kind(self, declaration: Declaration) -> str:
        """Return ``graph``.

        Example:
            ```python
            assert GraphLanguage().get_kind(declaration) == "graph"
            ```
        """
        del declaration
        return "graph"

    def get_identity(self, value: Any) -> SymbolRef | None:
        """Return the graph reference of an authoring declaration.

        Example:
            ```python
            reference = GraphLanguage().get_identity(declaration.value)
            ```
        """
        return value_identity(value)

    def get_references(
        self, value: Any, resolver: Any,
    ) -> tuple[SymbolRef, ...]:
        """Return the references a graph declaration declares; it has none.

        Example:
            ```python
            assert GraphLanguage().get_references(declaration.value, None) == ()
            ```
        """
        del value, resolver
        return ()

    def transcribe(
        self, declaration: Declaration, context: SymbolContext,
    ) -> Symbol:
        """Transcribe the graph declaration into one symbol.

        Example:
            ```python
            symbol = GraphLanguage().transcribe(declaration, context)
            ```
        """
        del context
        if not is_graph_declaration(declaration.value):
            raise TypeError(
                f"{declaration.value!r} is not a graph declaration"
            )
        return symbol_for_declaration(declaration.value)

    def render(
        self, symbol: Any, context: RenderContext,
    ) -> SourceFragment:
        """Render a graph symbol or declaration DTO to source.

        Example:
            ```python
            fragment = GraphLanguage().render(symbol, None)
            ```
        """
        value = symbol.value if isinstance(symbol, Symbol) else symbol
        if not isinstance(value, GraphDeclarationDTO):
            raise TypeError(f"{value!r} is not a graph declaration DTO")
        return render_graph_declaration_source(value, context)


__all__ = ["GraphLanguage"]
