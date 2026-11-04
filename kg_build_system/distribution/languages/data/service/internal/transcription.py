"""Transcribe table declarations into the data language's blueprint DTO.

The transcription and validation live in the package's private zone; each name
here is a thin delegation kept for the internal service path.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ...model.internal.dto.blueprint_dto import DataPartDTO


def collect_declarations(
    values: Sequence[Any],
) -> tuple[dict[int, Any], dict[int, Any]]:
    """Return every reachable declaration and its nested structs."""
    from .._private.transcription import collect_declarations as collect

    return collect(values)


def collect_values(namespace: Any) -> tuple[object, ...]:
    """Select table declarations and source bindings from a namespace."""
    from .._private.transcription import collect_values as collect

    return collect(namespace)


def transcribe_data(declarations: Sequence[object]) -> DataPartDTO:
    """Transcribe collected declarations into the data language DTO."""
    from .._private.transcription import transcribe_data as transcribe

    return transcribe(declarations)


def validate_data(data: DataPartDTO) -> None:
    """Reject a data DTO that violates the language invariants."""
    from .._private.transcription import validate_data as validate

    return validate(data)


__all__ = [
    "collect_declarations", "collect_values", "transcribe_data", "validate_data",
]
