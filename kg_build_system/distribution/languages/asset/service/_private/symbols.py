"""Project the asset language declaration into a linked symbol."""
from __future__ import annotations

from typing import Any

from kg_build_system.kernel import Key, Symbol, SymbolRef

from ...model.internal.dto.asset_dto import AssetDTO
from ...model.public.descriptor import asset_name
from .declarations import is_asset_declaration
from .transcription import asset_to_dto


def value_identity(value: Any) -> SymbolRef | None:
    """Return the symbol reference of an asset declaration or DTO."""
    if is_asset_declaration(value):
        return SymbolRef("asset", Key((asset_name(value),)))
    if isinstance(value, AssetDTO):
        return SymbolRef("asset", Key((value.name,)))
    return None


def symbol_for_declaration(value: type[Any]) -> Symbol:
    """Transcribe one asset declaration into one symbol."""
    dto = asset_to_dto(value)
    key = Key((dto.name,))
    return Symbol(key, "asset", dto)


__all__ = ["symbol_for_declaration", "value_identity"]
