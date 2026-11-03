"""Adapter from binding declarations to the kernel ``binding`` part.

``BindingLanguage`` implements the kernel language shape. It references its
target node or edge by graph name, reads the table and topology parts for
validation, and renders bindings back to ``node_binding``/``edge_binding``
source.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from kg_build_system.declaration.languages.table.internal import DataPartDTO
from kg_build_system.declaration.languages.topology.internal import GraphPartDTO
from kg_build_system.kernel import (
    Language,
    LanguageContext,
    Namespace,
    RenderContext,
    SourceFragment,
)

from ..dto.blueprint_dto import EdgeBindingDTO, NodeBindingDTO
from ..service.source import render_binding_source
from ..service.transcription import (
    collect_bindings,
    transcribe_bindings,
    validate_bindings,
)


def _part(context: Any, name: str) -> Any:
    try:
        return context.part(name)
    except (AttributeError, KeyError):
        return None


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
        data = _part(context, "data")
        topology = _part(context, "topology")
        bindings = transcribe_bindings(
            declarations,
            data if isinstance(data, DataPartDTO) else None,
        )
        if isinstance(topology, GraphPartDTO):
            _validate_references(bindings, topology)
        return bindings

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


def _validate_references(
    bindings: Sequence[NodeBindingDTO | EdgeBindingDTO],
    topology: GraphPartDTO,
) -> None:
    nodes = {item.name for item in topology.nodes}
    components = nodes | {item.name for item in topology.edges}
    for binding in bindings:
        if binding.component not in components:
            raise ValueError(
                f"binding targets an unknown component {binding.component!r}"
            )
        if isinstance(binding, EdgeBindingDTO):
            for side, name in (
                ("source_node", binding.source_node),
                ("target_node", binding.target_node),
            ):
                if name is not None and name not in nodes:
                    raise ValueError(
                        f"edge binding {side} {name!r} is not a node component"
                    )


__all__ = ["BindingLanguage"]
