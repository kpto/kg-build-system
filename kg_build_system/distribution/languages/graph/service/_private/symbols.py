"""Project the graph language declaration into a linked symbol."""
from __future__ import annotations

from typing import Any

from kg_build_system.kernel import Key, Symbol, SymbolRef

from ...model.internal.dto.graph_dto import GraphDeclarationDTO
from .declarations import graph_name, is_graph_declaration
from .transcription import graph_declaration_dto


def value_identity(value: Any) -> SymbolRef | None:
    """Return the symbol reference of a graph declaration or DTO."""
    if is_graph_declaration(value):
        return SymbolRef("graph", Key((graph_name(value),)))
    if isinstance(value, GraphDeclarationDTO):
        return SymbolRef("graph", Key((value.name,)))
    return None


def symbol_for_declaration(value: type[Any]) -> Symbol:
    """Transcribe one graph declaration into one symbol."""
    dto = graph_declaration_dto(value)
    return Symbol(Key((dto.name,)), "graph", dto)


__all__ = ["symbol_for_declaration", "value_identity"]
