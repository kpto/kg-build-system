"""Transcribe authoring meaning values into their blueprint DTOs."""
from __future__ import annotations

from ...model.internal.dto.meaning_dto import (
    ClaimDTO,
    LimitationDTO,
    PurposeDTO,
    MeaningDTO,
)
from ...model.public.units import Purpose, Meaning


def _claims(value: Meaning) -> tuple[ClaimDTO, ...]:
    return tuple(ClaimDTO(text=claim.text) for claim in value.claims)


def meaning_to_dto(value: Meaning) -> MeaningDTO:
    """Convert one declaration meaning value to its DTO."""
    return MeaningDTO(
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


__all__ = ["meaning_to_dto"]
