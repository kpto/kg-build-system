"""The table language: collect, transcribe, validate and render its DTO."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from kg_build_system.kernel import SourceFragment
from kg_build_system.kernel import Layer

from ..source import render_data
from ..transcription import collect_values, transcribe_data, validate_data
from ....model.internal.dto.blueprint_dto import DataPartDTO


class TableLanguage:
    """The table part of a blueprint; implements ``kernel.Language``.

    A language transcribes authoring declarations to its DTO and renders that
    DTO back to authoring source. The transcribed value is wrapped in the
    kernel's ``Layer`` with the language name ``data``.
    """

    name = "data"
    requires: tuple[str, ...] = ()

    def collect(self, namespace: Any) -> Sequence[object]:
        """Select the table declarations and source bindings to transcribe."""
        return collect_values(namespace)

    def transcribe(self, declarations: Sequence[object], context: Any = None) -> Layer:
        """Transcribe declarations into a table layer."""
        del context
        return Layer(self.name, transcribe_data(tuple(declarations)))

    def validate(self, layer: Layer) -> None:
        """Reject a table layer that violates the language invariants."""
        if not isinstance(layer, Layer):
            raise TypeError("the table language validates a Layer")
        if layer.language != self.name:
            raise ValueError(
                f"table language received layer {layer.language!r}"
            )
        if not isinstance(layer.value, DataPartDTO):
            raise TypeError("the table language transcribes to DataPartDTO")
        validate_data(layer.value)

    def render(
        self,
        layer: Any,
        context: Any = None,
        *,
        class_names: Any = None,
    ) -> SourceFragment:
        """Render the table layer back to authoring source."""
        del context
        value = layer.value if isinstance(layer, Layer) else layer
        return render_data(value, class_names=class_names)


__all__ = ["TableLanguage"]
