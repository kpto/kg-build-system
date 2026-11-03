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
    requires the data and topology parts so it can reject a binding whose row
    source or target is not declared.

    Example:
        ```python
        from kg_build_system.declaration.languages.binding.service.internal import (
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
    ) -> tuple[NodeBindingDTO | EdgeBindingDTO, ...]:
        """Transcribe binding declarations into binding DTOs.

        Example:
            ```python
            bindings = BindingLanguage().transcribe((site_binding,), context)
            ```
        """
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
        return render_binding_source(dto, context)


__all__ = ["BindingLanguage"]
