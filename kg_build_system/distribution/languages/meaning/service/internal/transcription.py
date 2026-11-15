"""Transcription interface for the meaning language."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...model.internal.dto.meaning_dto import MeaningDTO
    from ...model.public.units import Meaning


def meaning_to_dto(value: Meaning) -> MeaningDTO:
    """Convert one declaration meaning value to its DTO."""
    from .._private.transcription import meaning_to_dto as convert

    return convert(value)


__all__ = ["meaning_to_dto"]
