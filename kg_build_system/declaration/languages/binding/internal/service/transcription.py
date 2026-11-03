"""Transcribe binding declarations into the binding language DTO."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from kg_build_system.declaration.languages.table.internal import DataPartDTO

from ..dto.blueprint_dto import BindingDTO
from ..model import Binding


def collect_bindings(namespace: Any) -> tuple[Binding, ...]:
    """Select binding values from a namespace, preserving first occurrence."""
    from ..._private.transcription import collect_bindings as collect

    return collect(namespace)


def transcribe_bindings(
    declarations: Sequence[object],
    data: DataPartDTO | None = None,
) -> tuple[BindingDTO, ...]:
    """Transcribe binding declarations into binding DTOs, sorted by target."""
    from ..._private.transcription import transcribe_bindings as transcribe

    return transcribe(declarations, data)


def validate_bindings(bindings: Sequence[BindingDTO]) -> None:
    """Reject a binding part with duplicate identities or invalid modes."""
    from ..._private.transcription import validate_bindings as validate

    validate(bindings)


__all__ = [
    "collect_bindings", "transcribe_bindings", "validate_bindings",
]
