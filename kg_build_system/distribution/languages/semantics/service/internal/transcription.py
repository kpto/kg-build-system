"""Transcription interface for the semantics language."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...model.internal.dto.semantics_dto import SemanticsDTO
    from ...model.public.units import Semantics


def semantics_to_dto(value: Semantics) -> SemanticsDTO:
    """Convert one declaration semantics value to its DTO."""
    from .._private.transcription import semantics_to_dto as convert

    return convert(value)


__all__ = ["semantics_to_dto"]
