"""Transcribe the graph declaration into the graph blueprint DTO."""
from __future__ import annotations

from typing import Any

from kg_build_system.distribution.languages.semantics.model.internal.dto import (
    ClaimDTO,
    FrameDTO,
    GraphSemanticsDTO,
    LimitationDTO,
    PurposeDTO,
)
from kg_build_system.distribution.languages.semantics.model.public import (
    GraphSemantics,
)

from ...model.internal.dto.graph_dto import GraphDeclarationDTO


def graph_semantics_dto(value: GraphSemantics) -> GraphSemanticsDTO:
    """Turn one graph semantics value into its blueprint DTO."""
    from kg_build_system.distribution.languages.semantics.service.internal import (
        graph_semantics_to_dto,
    )

    return graph_semantics_to_dto(value)


def graph_declaration_dto(value: type[Any]) -> GraphDeclarationDTO:
    """Turn one prepared graph declaration into its blueprint DTO."""
    options = value._graph_options
    return GraphDeclarationDTO(
        name=value._graph_name,
        description=options.description,
        semantics=graph_semantics_dto(options.semantics),
    )


__all__ = ["graph_declaration_dto", "graph_semantics_dto"]
