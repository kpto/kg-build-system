"""Project the asset language DTO into linked symbols."""
from __future__ import annotations

from typing import Any

from kg_build_system.kernel import Key, Symbol, SymbolRef

from ...model.internal.dto.asset_dto import AssetDTO, AssetPartDTO
from ...model.public.descriptor import asset_name
from .declarations import is_asset_declaration


def owns_value(value: Any) -> bool:
    """Whether the asset language owns an authoring value or DTO."""
    return is_asset_declaration(value) or isinstance(value, AssetDTO)


def value_identity(value: Any) -> SymbolRef | None:
    """Return the symbol reference of an asset declaration or DTO."""
    if is_asset_declaration(value):
        return SymbolRef("asset", Key((asset_name(value),)))
    if isinstance(value, AssetDTO):
        return SymbolRef("asset", Key((value.name,)))
    return None


def symbols_for_part(part: AssetPartDTO) -> dict[SymbolRef, Symbol]:
    """Split one asset DTO part into one symbol per asset."""
    symbols: dict[SymbolRef, Symbol] = {}
    for asset in part.assets:
        reference = SymbolRef("asset", Key((asset.name,)))
        symbols[reference] = Symbol(Key((asset.name,)), "asset", asset)
    return symbols


__all__ = ["owns_value", "symbols_for_part", "value_identity"]
