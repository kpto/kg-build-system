"""The binding language: binding declarations, symbols and source."""
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

from ....model.internal.dto.blueprint_dto import (
    EdgeBindingDTO,
    NodeBindingDTO,
)
from ..source import render_binding_source
from ..transcription import collect_bindings
from ..._private.symbols import (
    binding_identity,
    symbol_for_declaration,
    value_identity,
    value_references,
)


class BindingLanguage(Language):
    """The binding language: ``binding`` symbols for nodes and edges.

    A binding is one row context mapped onto one graph component. The language
    reads the data and topology symbols already transcribed so it can reject a
    binding whose row source or target is not declared.

    Example:
        ```python
        from kg_build_system.distribution.languages.binding.service.internal import (
            BindingLanguage,
        )

        language = BindingLanguage()
        assert language.name == "binding"
        ```
    """

    name = "binding"

    def discover_declarations(
        self, namespace: Namespace,
    ) -> Iterable[Declaration]:
        """Select binding values from the namespace.

        Example:
            ```python
            declarations = BindingLanguage().discover_declarations(namespace)
            ```
        """
        return tuple(
            Declaration(value) for value in collect_bindings(namespace)
        )

    def compute_key(self, declaration: Declaration) -> Key:
        """Return the binding's identity key.

        Example:
            ```python
            key = BindingLanguage().compute_key(declaration)
            ```
        """
        return Key((binding_identity(declaration.value),))

    def get_kind(self, declaration: Declaration) -> str:
        """Return ``binding``.

        Example:
            ```python
            kind = BindingLanguage().get_kind(declaration)
            ```
        """
        del declaration
        return "binding"

    def get_identity(self, value: Any) -> SymbolRef | None:
        """Return the binding reference of an authoring value.

        Example:
            ```python
            reference = BindingLanguage().get_identity(declaration.value)
            ```
        """
        return value_identity(value)

    def get_references(
        self, value: Any, resolver: Any,
    ) -> tuple[SymbolRef, ...]:
        """Return the references an authoring binding declares.

        References name the target node or edge, the edge endpoints, the data
        sources read by the rows and every expression leaf. The value is the
        authoring binding, never a transcribed DTO.

        Example:
            ```python
            references = BindingLanguage().get_references(binding, resolver)
            ```
        """
        del resolver
        return value_references(value)

    def transcribe(
        self, declaration: Declaration, context: SymbolContext,
    ) -> Symbol:
        """Transcribe one binding against the data and topology symbols.

        Example:
            ```python
            symbol = BindingLanguage().transcribe(declaration, context)
            ```
        """
        return symbol_for_declaration(declaration, context)

    def render(
        self, symbol: Any, context: RenderContext,
    ) -> SourceFragment:
        """Render a binding symbol, fragment or whole binding part to source.

        Example:
            ```python
            fragment = BindingLanguage().render(blueprint.bindings, None)
            ```
        """
        value = symbol.value if isinstance(symbol, Symbol) else symbol
        if isinstance(value, (NodeBindingDTO, EdgeBindingDTO)):
            value = (value,)
        return render_binding_source(value, context)


__all__ = ["BindingLanguage"]
