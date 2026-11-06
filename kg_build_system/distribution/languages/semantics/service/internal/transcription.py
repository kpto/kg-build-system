"""Transcription interface for the semantics language."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...model.internal.dto.semantics_dto import (
        GraphSemanticsDTO,
        SemanticsDTO,
    )
    from ...model.public.units import GraphSemantics, Semantics


def semantics_to_dto(value: Semantics) -> SemanticsDTO:
    """Convert one declaration semantics fragment to its DTO."""
    from .._private.transcription import semantics_to_dto as convert

    return convert(value)


def graph_semantics_to_dto(value: GraphSemantics) -> GraphSemanticsDTO:
    """Convert the graph meaning root to its DTO."""
    from .._private.transcription import graph_semantics_to_dto as convert

    return convert(value)


__all__ = ["graph_semantics_to_dto", "semantics_to_dto"]
