"""Transcribe authoring semantics values into their blueprint DTOs."""
from __future__ import annotations

from ...model.internal.dto.semantics_dto import (
    ClaimDTO,
    FrameDTO,
    GraphSemanticsDTO,
    LimitationDTO,
    PurposeDTO,
    SemanticsDTO,
)
from ...model.public.units import GraphSemantics, Semantics


def _claims(value: Semantics | GraphSemantics) -> tuple[ClaimDTO, ...]:
    return tuple(ClaimDTO(text=claim.text) for claim in value.claims)


def _frame(value: object) -> FrameDTO:
    limitations = getattr(value, "limitations")
    return FrameDTO(
        text=getattr(value, "text"),
        limitations=tuple(
            LimitationDTO(text=limitation.text) for limitation in limitations
        ),
    )


def semantics_to_dto(value: Semantics) -> SemanticsDTO:
    """Convert one declaration semantics fragment to its DTO."""
    return SemanticsDTO(
        claims=_claims(value),
        frames=tuple(_frame(frame) for frame in value.frames),
    )


def graph_semantics_to_dto(value: GraphSemantics) -> GraphSemanticsDTO:
    """Convert the graph meaning root to its DTO."""
    purpose = value.purpose
    return GraphSemanticsDTO(
        claims=_claims(value),
        purpose=PurposeDTO(
            text=purpose.text,
            frames=tuple(_frame(frame) for frame in purpose.frames),
        ),
    )


__all__ = ["graph_semantics_to_dto", "semantics_to_dto"]
