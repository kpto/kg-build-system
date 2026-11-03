"""Adapter from binding declarations to the kernel ``binding`` part.

``BindingLanguage`` implements the kernel language shape. It references its
target node or edge by graph name, reads the table and topology parts for
validation, and renders bindings back to ``node_binding``/``edge_binding``
source.
"""
from __future__ import annotations

from collections.abc import Sequence

from kg_build_system.kernel import (
    Language,
    LanguageContext,
    Namespace,
    RenderContext,
    SourceFragment,
)

from ..dto.blueprint_dto import EdgeBindingDTO, NodeBindingDTO


class BindingLanguage(Language):
    """The ``binding`` part of a blueprint.

    A binding is one row context mapped onto one graph component. The language
    requires the data and topology parts so it can reject a binding whose row
    source or target is not declared.

    Example:
        ```python
        from kg_build_system.declaration.languages.binding.internal import (
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
        from ..._private.transcription import collect_bindings

        return collect_bindings(namespace)

    def transcribe(
        self, declarations: Sequence[object], context: LanguageContext,
    ) -> tuple[NodeBindingDTO | EdgeBindingDTO, ...]:
        """Transcribe binding declarations into binding DTOs.

        Example:
            ```python
            bindings = BindingLanguage().transcribe((site_binding,), context)
            ```
        """
        from ..._private.transcription import transcribe_binding_part

        return transcribe_binding_part(declarations, context)

    def validate(
        self, dto: tuple[NodeBindingDTO | EdgeBindingDTO, ...],
    ) -> None:
        """Reject a binding part with a duplicate identity or bad mode.

        Example:
            ```python
            BindingLanguage().validate(())
            ```
        """
        from ..._private.transcription import validate_bindings

        validate_bindings(dto)

    def render(
        self,
        dto: tuple[NodeBindingDTO | EdgeBindingDTO, ...],
        context: RenderContext,
    ) -> SourceFragment:
        """Render the binding part back to authoring source.

        Example:
            ```python
            fragment = BindingLanguage().render((), None)
            assert fragment.body == ""
            ```
        """
        from ..service.source import render_binding_source

        return render_binding_source(dto, context)


__all__ = ["BindingLanguage"]
