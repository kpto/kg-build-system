"""Kernel language adapter for the asset language."""
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

from ....model.internal.dto.asset_dto import AssetDTO, AssetPartDTO
from ..._private.declarations import is_asset_declaration
from ..._private.symbols import symbol_for_declaration, value_identity
from ..source import render_asset_source


class AssetLanguage(Language):
    """The asset language: one ``asset`` symbol per logical source-data unit.

    Example:
        ```python
        from kg_build_system.distribution.languages.asset.service.internal import (
            AssetLanguage,
        )

        language = AssetLanguage()
        assert language.name == "asset"
        ```
    """

    name = "asset"

    def discover_declarations(
        self, namespace: Namespace,
    ) -> Iterable[Declaration]:
        """Select every concrete ``Asset`` subclass in a namespace.

        Example:
            ```python
            declarations = AssetLanguage().discover_declarations(namespace)
            ```
        """
        return tuple(
            Declaration(value)
            for value in namespace.values()
            if is_asset_declaration(value)
        )

    def compute_key(self, declaration: Declaration) -> Key:
        """Return the asset-name key of one declaration.

        Example:
            ```python
            key = AssetLanguage().compute_key(declaration)
            ```
        """
        from ....model.public.descriptor import asset_name

        return Key((asset_name(declaration.value),))

    def get_kind(self, declaration: Declaration) -> str:
        """Return ``asset``.

        Example:
            ```python
            assert AssetLanguage().get_kind(declaration) == "asset"
            ```
        """
        del declaration
        return "asset"

    def get_identity(self, value: Any) -> SymbolRef | None:
        """Return the asset reference of an authoring declaration.

        Example:
            ```python
            reference = AssetLanguage().get_identity(declaration.value)
            ```
        """
        return value_identity(value)

    def get_references(
        self, value: Any, resolver: Any,
    ) -> tuple[SymbolRef, ...]:
        """Return the references an asset declaration declares; an asset has none.

        Example:
            ```python
            assert AssetLanguage().get_references(declaration.value, resolver) == ()
            ```
        """
        del value, resolver
        return ()

    def transcribe(
        self, declaration: Declaration, context: SymbolContext,
    ) -> Symbol:
        """Transcribe one asset declaration into one symbol.

        Example:
            ```python
            symbol = AssetLanguage().transcribe(declaration, context)
            ```
        """
        del context
        if not is_asset_declaration(declaration.value):
            raise TypeError(
                f"{declaration.value!r} is not an asset declaration"
            )
        return symbol_for_declaration(declaration.value)

    def render(
        self, symbol: Any, context: RenderContext,
    ) -> SourceFragment:
        """Render an asset symbol, DTO or whole asset part to source.

        Example:
            ```python
            fragment = AssetLanguage().render(blueprint.assets, None)
            ```
        """
        value = symbol.value if isinstance(symbol, Symbol) else symbol
        if isinstance(value, AssetDTO):
            value = AssetPartDTO((value,))
        return render_asset_source(value, context)


__all__ = ["AssetLanguage"]
