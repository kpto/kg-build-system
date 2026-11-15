"""Transcribe authoring semantics values into their blueprint DTOs."""
from __future__ import annotations

from ...model.internal.dto.semantics_dto import (
    ClaimDTO,
    LimitationDTO,
    PurposeDTO,
    SemanticsDTO,
)
from ...model.public.units import Purpose, Semantics


def _claims(value: Semantics) -> tuple[ClaimDTO, ...]:
    return tuple(ClaimDTO(text=claim.text) for claim in value.claims)


def semantics_to_dto(value: Semantics) -> SemanticsDTO:
    """Convert one declaration semantics value to its DTO."""
    return SemanticsDTO(
        purpose=_purpose(value.purpose),
        claims=_claims(value),
    )


def _purpose(value: Purpose | None) -> PurposeDTO | None:
    if value is None:
        return None
    return PurposeDTO(
        text=value.text,
        limitations=tuple(
            LimitationDTO(text=limitation.text)
            for limitation in value.limitations
        ),
    )


__all__ = ["semantics_to_dto"]
