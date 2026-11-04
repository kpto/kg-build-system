"""Adapter from binding declarations to the kernel ``binding`` layer.

``BindingLanguage`` implements the kernel language shape. It references its
target node or edge by graph name, reads the data and topology layers for
validation, and renders bindings back to ``node_binding``/``edge_binding``
source.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from kg_build_system.kernel import (
    Language,
    LanguageContext,
    Layer,
    Namespace,
    RenderContext,
    SourceFragment,
)

from ....model.internal.dto.blueprint_dto import (
    EdgeBindingDTO, NodeBindingDTO,
)
from ..source import render_binding_source
from ..transcription import (
    collect_bindings, transcribe_binding_part, validate_bindings,
)


class BindingLanguage(Language):
    """The ``binding`` part of a blueprint.

    A binding is one row context mapped onto one graph component. The language
    requires the data and topology layers so it can reject a binding whose row
    source or target is not declared.

    Example:
        ```python
        from kg_build_system.distribution.languages.binding.service.internal import (
            BindingLanguage,
        )

        language = BindingLanguage()
        assert language.name == "binding"
        ```
    """

    name = "binding"
    requires: tuple[str, ...] = ("data", "topology")

    def collect(self, namespace: Namespace) -> Sequence[object]:
        """Select binding values from the namespace.

        Example:
            ```python
            class Namespace:
                def values(self):
                    return (site_binding,)

            declarations = BindingLanguage().collect(Namespace())
            ```
        """
        return collect_bindings(namespace)

    def transcribe(
        self, declarations: Sequence[object], context: LanguageContext,
    ) -> Layer:
        """Transcribe binding declarations into a binding layer.

        Example:
            ```python
            layer = BindingLanguage().transcribe((site_binding,), context)
            ```
        """
        return Layer(
            self.name, transcribe_binding_part(declarations, context),
        )

    def validate(self, layer: Layer) -> None:
        """Reject a binding layer with a duplicate identity or bad mode.

        Example:
            ```python
            BindingLanguage().validate(Layer("binding", ()))
            ```
        """
        if layer.language != self.name:
            raise ValueError(
                f"binding language received layer {layer.language!r}"
            )
        validate_bindings(layer.value)

    def render(
        self,
        layer: Any,
        context: RenderContext,
    ) -> SourceFragment:
        """Render the binding layer back to authoring source.

        Example:
            ```python
            fragment = BindingLanguage().render(Layer("binding", ()), None)
            assert fragment.body == ""
            ```
        """
        value = layer.value if isinstance(layer, Layer) else layer
        return render_binding_source(value, context)


__all__ = ["BindingLanguage"]
