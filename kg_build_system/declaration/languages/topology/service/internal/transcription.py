"""Transcribe topology declarations into the topology blueprint DTO."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ...model.internal.dto.blueprint_dto import GraphPartDTO


def collect_components(namespace: Any) -> Sequence[type[Any]]:
    """Select every graph-visible declaration reachable from the namespace."""
    from .._private.transcription import collect_components as collect

    return collect(namespace)


def transcribe_graph_part(
    declarations: Sequence[object], context: Any = None,
) -> GraphPartDTO:
    """Turn collected declarations into the topology blueprint DTO."""
    from .._private.transcription import transcribe_graph_part as transcribe

    return transcribe(declarations, context)


def validate_graph_part(dto: GraphPartDTO) -> None:
    """Reject a topology DTO whose references or hierarchy are invalid."""
    from .._private.transcription import validate_graph_part as validate

    validate(dto)


__all__ = [
    "collect_components", "transcribe_graph_part", "validate_graph_part",
]
