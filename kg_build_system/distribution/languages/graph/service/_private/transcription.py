"""Transcribe the graph declaration into the graph blueprint DTO."""
from __future__ import annotations

from typing import Any

from kg_build_system.distribution.languages.meaning.model.internal.dto import (
    MeaningDTO,
)
from kg_build_system.distribution.languages.meaning.model.public import (
    Meaning,
)

from ...model.internal.dto.graph_dto import GraphDeclarationDTO


def graph_meaning_dto(value: Meaning) -> MeaningDTO:
    """Turn the graph's meaning value into its blueprint DTO."""
    from kg_build_system.distribution.languages.meaning.service.internal import (
        meaning_to_dto,
    )

    return meaning_to_dto(value)


def graph_declaration_dto(value: type[Any]) -> GraphDeclarationDTO:
    """Turn one prepared graph declaration into its blueprint DTO."""
    options = value._graph_options
    return GraphDeclarationDTO(
        name=value._graph_name,
        description=options.description,
        meaning=graph_meaning_dto(options.meaning),
    )


__all__ = ["graph_declaration_dto", "graph_meaning_dto"]
