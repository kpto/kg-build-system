"""The table language: collect, transcribe, validate and render its DTO."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from ..service.source import SourceFragment, render_data
from ..service.transcription import (
    collect_values, transcribe_data, validate_data,
)
from ..dto.blueprint_dto import DataPartDTO


class TableLanguage:
    """The table part of a blueprint; implements ``kernel.Language``.

    A language transcribes authoring declarations to its DTO and renders that
    DTO back to authoring source.
    """

    name = "data"
    requires: tuple[str, ...] = ()

    def collect(self, namespace: Any) -> Sequence[object]:
        """Select the table declarations and source bindings to transcribe."""
        return collect_values(namespace)

    def transcribe(self, declarations: Sequence[object], context: Any = None) -> DataPartDTO:
        """Transcribe declarations into the table language DTO."""
        del context
        return transcribe_data(tuple(declarations))

    def validate(self, dto: DataPartDTO) -> None:
        """Reject a table DTO that violates the language invariants."""
        if not isinstance(dto, DataPartDTO):
            raise TypeError("the table language transcribes to DataPartDTO")
        validate_data(dto)

    def render(
        self,
        dto: DataPartDTO,
        context: Any = None,
        *,
        class_names: Any = None,
    ) -> SourceFragment:
        """Render the table DTO back to authoring source."""
        del context
        return render_data(dto, class_names=class_names)


__all__ = ["TableLanguage"]
