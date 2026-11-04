"""Link language declarations into a graph blueprint.

The linker fixes the transcription order to ``expressions``, ``data``,
``topology`` then ``binding``: data and bindings read expression operations and
bindings read the other two languages. It indexes declarations,
transcribes each language, resolves references, validates the symbol graph and
assembles the current blueprint shapes.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from kg_build_system.kernel import (
    Declaration,
    Key,
    Language,
    Namespace,
    ReferenceResolver,
    Symbol,
    SymbolContext,
    SymbolRef,
)

from ...model.public import GraphBlueprint
from ....languages.binding.model.internal.dto.blueprint_dto import (
    EdgeBindingDTO, NodeBindingDTO,
)
from ....languages.data.model.internal.dto.blueprint_dto import (
    DataPartDTO, ProjectionDTO, RelationDTO, SourceDTO, StructDTO,
)
from ....languages.topology.model.internal.dto.blueprint_dto import (
    EdgeDTO, GraphPartDTO, NodeDTO,
)
from .assembly import assemble_blueprint
from .validation import validate_blueprint

ORDER = ("expressions", "data", "topology", "binding")


class _LanguageResolver:
    """Resolve values by asking the language that owns them."""

    def __init__(
        self, languages: Sequence[Language], symbols: dict[SymbolRef, Symbol],
    ) -> None:
        self._languages = tuple(languages)
        self._symbols = symbols

    def get_identity(self, value: Any) -> SymbolRef | None:
        for language in self._languages:
            if language.owns(value):
                return language.get_identity(value)
        return None

    def get_references(self, value: Any) -> tuple[SymbolRef, ...]:
        for language in self._languages:
            if language.owns(value):
                return language.get_references(value, self)
        return ()


def _index_language(
    language: Language, namespace: Namespace,
) -> tuple[tuple[Declaration, ...], dict[Key, Declaration]]:
    declarations = tuple(language.discover_declarations(namespace))
    index: dict[Key, Declaration] = {}
    for declaration in declarations:
        key = language.compute_key(declaration)
        if key in index:
            raise ValueError(
                f"language {language.name!r} declares key {key!s} twice"
            )
        index[key] = declaration
    return declarations, index


def order_symbols(symbols: dict[SymbolRef, Symbol]) -> tuple[SymbolRef, ...]:
    """Validate every reference and order symbols dependencies-first."""
    ordered: list[SymbolRef] = []
    state: dict[SymbolRef, int] = {}

    def visit(reference: SymbolRef) -> None:
        status = state.get(reference)
        if status == 1:
            raise ValueError(f"symbol reference cycle at {reference}")
        if status == 2:
            return
        symbol = symbols.get(reference)
        if symbol is None:
            raise ValueError(f"unknown symbol reference {reference}")
        state[reference] = 1
        for dependency in symbol.references:
            visit(dependency)
        state[reference] = 2
        ordered.append(reference)

    for reference in symbols:
        visit(reference)
    return tuple(ordered)


def _assemble(symbols: dict[SymbolRef, Symbol]) -> GraphBlueprint:
    ordered = order_symbols(symbols)
    resolved = [symbols[reference] for reference in ordered]
    data = DataPartDTO(
        structs=tuple(
            symbol.value for symbol in resolved
            if isinstance(symbol.value, StructDTO)
        ),
        relations=tuple(
            symbol.value for symbol in resolved
            if isinstance(symbol.value, RelationDTO)
        ),
        projections=tuple(
            symbol.value for symbol in resolved
            if isinstance(symbol.value, ProjectionDTO)
        ),
        sources=tuple(
            symbol.value for symbol in resolved
            if isinstance(symbol.value, SourceDTO)
        ),
    )
    graph = GraphPartDTO(
        nodes=tuple(
            symbol.value for symbol in resolved
            if isinstance(symbol.value, NodeDTO)
        ),
        edges=tuple(
            symbol.value for symbol in resolved
            if isinstance(symbol.value, EdgeDTO)
        ),
    )
    bindings = tuple(
        symbol.value for symbol in resolved
        if isinstance(symbol.value, (NodeBindingDTO, EdgeBindingDTO))
    )
    blueprint = assemble_blueprint(graph, data, bindings)
    validate_blueprint(blueprint)
    return blueprint


def link_blueprint(
    languages: Sequence[Language], namespace: Namespace,
) -> GraphBlueprint:
    """Index, transcribe, resolve and assemble one graph blueprint."""
    by_name: dict[str, Language] = {}
    for language in languages:
        if language.name in by_name:
            raise ValueError(f"duplicate language name {language.name!r}")
        by_name[language.name] = language
    missing = [name for name in ORDER if name not in by_name]
    if missing:
        raise ValueError(
            "the graph linker requires languages " + ", ".join(missing)
        )

    declarations: dict[str, tuple[Declaration, ...]] = {}
    for name in ORDER:
        declarations[name], _ = _index_language(by_name[name], namespace)

    symbols: dict[SymbolRef, Symbol] = {}
    for name in ORDER:
        context = SymbolContext(symbols)
        produced = by_name[name].transcribe_many(declarations[name], context)
        for reference, symbol in produced.items():
            if reference.language != name:
                raise ValueError(
                    f"language {name!r} produced symbol {reference} for "
                    f"another language"
                )
            if reference in symbols:
                raise ValueError(f"duplicate symbol reference {reference}")
            symbols[reference] = symbol

    ordered = tuple(by_name[name] for name in ORDER)
    resolver = _LanguageResolver(ordered, symbols)
    resolved: dict[SymbolRef, Symbol] = {}
    for reference, symbol in symbols.items():
        language = by_name[reference.language]
        extra = language.get_references(symbol.value, resolver)
        references = tuple(dict.fromkeys((*symbol.references, *extra)))
        resolved[reference] = replace(symbol, references=references)
    return _assemble(resolved)


__all__ = ["ORDER", "link_blueprint", "order_symbols"]
