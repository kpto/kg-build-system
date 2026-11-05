"""Link language declarations into a graph blueprint.

The linker fixes the transcription order to ``expressions``, ``asset``,
``data``, ``topology`` then ``binding``: data reads expression operations and
names its assets, and bindings read the other three languages. It indexes
declarations, selects roots, resolves the reference closure from authoring
values, orders the reachable declarations, transcribes only those declarations
and assembles the blueprint. Declarations are candidates; only reachable ones
become symbols.
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
    Symbol,
    SymbolContext,
    SymbolRef,
)

from ...model.public import GraphBlueprint
from ....languages.asset.model.internal.dto import AssetDTO, AssetPartDTO
from ....languages.binding.model.internal.dto.blueprint_dto import (
    EdgeBindingDTO, NodeBindingDTO,
)
from ....languages.data.model.internal.dto.blueprint_dto import (
    DataPartDTO, ProjectionDTO, RelationDTO, StructDTO,
)
from ....languages.topology.model.internal.dto.blueprint_dto import (
    EdgeDTO, GraphPartDTO, NodeDTO,
)
from .assembly import assemble_blueprint
from .validation import validate_blueprint

ORDER = ("expressions", "asset", "data", "topology", "binding")


class _LanguageResolver:
    """Resolve authoring values by asking every language for their identity."""

    def __init__(self, languages: Sequence[Language]) -> None:
        self._languages = tuple(languages)

    def get_identity(self, value: Any) -> SymbolRef | None:
        matches = tuple(
            reference
            for language in self._languages
            if (reference := language.get_identity(value)) is not None
        )
        if len(matches) > 1:
            raise ValueError(
                "more than one language claims value identity: "
                + ", ".join(str(reference) for reference in matches)
            )
        return matches[0] if matches else None


def _index_language(
    language: Language, namespace: Namespace,
) -> tuple[tuple[Key, Declaration], ...]:
    declarations = tuple(language.discover_declarations(namespace))
    keys: set[Key] = set()
    indexed: list[tuple[Key, Declaration]] = []
    for declaration in declarations:
        key = language.compute_key(declaration)
        if key in keys:
            raise ValueError(
                f"language {language.name!r} declares key {key!s} twice"
            )
        keys.add(key)
        indexed.append((key, declaration))
    return tuple(indexed)


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
    )
    assets = AssetPartDTO(assets=tuple(
        symbol.value for symbol in resolved
        if isinstance(symbol.value, AssetDTO)
    ))
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
    blueprint = assemble_blueprint(graph, data, assets, bindings)
    validate_blueprint(blueprint)
    return blueprint


def link_blueprint(
    languages: Sequence[Language],
    namespace: Namespace,
    *,
    roots: Sequence[str] | None = None,
) -> GraphBlueprint:
    """Index, select, transcribe, resolve and assemble one graph blueprint.

    ``roots`` names the languages whose declarations are starting points.
    ``None`` uses every language, preserving the full blueprint. A narrower
    policy such as ``("binding",)`` selects the closure reachable from bindings
    before any declaration is transcribed.
    """
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
    root_names = tuple(ORDER if roots is None else roots)
    root_languages = set(root_names)
    unknown_roots = root_languages - set(by_name)
    if unknown_roots:
        raise ValueError(
            "unknown root language(s): " + ", ".join(sorted(unknown_roots))
        )

    indexed: dict[SymbolRef, tuple[Language, Declaration]] = {}
    for name in ORDER:
        language = by_name[name]
        for key, declaration in _index_language(language, namespace):
            indexed[SymbolRef(name, key)] = (language, declaration)

    resolver = _LanguageResolver(
        tuple(by_name[name] for name in ORDER),
    )
    references: dict[SymbolRef, tuple[SymbolRef, ...]] = {}

    def references_for(reference: SymbolRef) -> tuple[SymbolRef, ...]:
        cached = references.get(reference)
        if cached is not None:
            return cached
        entry = indexed.get(reference)
        if entry is None:
            raise ValueError(f"unknown symbol reference {reference}")
        language, declaration = entry
        resolved = tuple(
            language.get_references(declaration.value, resolver)
        )
        references[reference] = resolved
        return resolved

    reachable: dict[SymbolRef, None] = {}

    def collect(reference: SymbolRef) -> None:
        if reference in reachable:
            return
        if reference not in indexed:
            raise ValueError(f"unknown symbol reference {reference}")
        reachable[reference] = None
        for dependency in references_for(reference):
            collect(dependency)

    for reference in indexed:
        if reference.language in root_languages:
            collect(reference)

    state: dict[SymbolRef, int] = {}
    ordered: list[SymbolRef] = []

    def order(reference: SymbolRef) -> None:
        status = state.get(reference)
        if status == 1:
            raise ValueError(f"symbol reference cycle at {reference}")
        if status == 2:
            return
        state[reference] = 1
        for dependency in references_for(reference):
            order(dependency)
        state[reference] = 2
        ordered.append(reference)

    for reference in reachable:
        order(reference)

    symbols: dict[SymbolRef, Symbol] = {}
    for reference in ordered:
        language, declaration = indexed[reference]
        symbol = language.transcribe(
            declaration, SymbolContext(symbols),
        )
        if symbol.key != reference.key:
            raise ValueError(
                f"language {language.name!r} transcribed {reference.key!s} "
                f"as {symbol.key!s}"
            )
        symbols[reference] = replace(
            symbol, references=references_for(reference),
        )
    return _assemble(symbols)


__all__ = ["ORDER", "link_blueprint", "order_symbols"]
