"""Adapter from topology declarations to the kernel ``topology`` part.

``TopologyLanguage`` implements the kernel language shape: ``collect`` selects
declarations, ``transcribe`` produces :class:`GraphPartDTO`, ``validate``
checks the DTO invariants and ``render`` returns authoring source. The class
does not carry a live declaration into the DTO.
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from kg_build_system.kernel import (
    Language,
    LanguageContext,
    Namespace,
    RenderContext,
    SourceFragment,
)

from ..dto.blueprint_dto import GraphPartDTO


class TopologyLanguage(Language):
    """The ``topology`` language: collect declarations, transcribe to a DTO.

    Collection includes abstract parents and edge endpoint categories even when
    a namespace only exposes bindings.

    Example:
        ```python
        from kg_build_system.declaration.languages.topology.internal import (
            TopologyLanguage,
        )

        language = TopologyLanguage()
        assert language.name == "topology"
        ```
    """

    name = "topology"
    requires: tuple[str, ...] = ()

    def collect(self, namespace: Namespace) -> Sequence[type[Any]]:
        """Select every graph-visible declaration reachable from the namespace.

        Example:
            ```python
            class Namespace:
                def values(self):
                    return (SiteNode,)

            declarations = TopologyLanguage().collect(Namespace())
            ```
        """
        from ..._private.transcription import collect_components

        return collect_components(namespace)

    def transcribe(
        self, declarations: Sequence[object], context: LanguageContext,
    ) -> GraphPartDTO:
        """Turn collected declarations into the topology blueprint DTO.

        Example:
            ```python
            part = TopologyLanguage().transcribe((SiteNode,), context)
            assert isinstance(part, GraphPartDTO)
            ```
        """
        from ..._private.transcription import transcribe_graph_part

        return transcribe_graph_part(declarations, context)

    def validate(self, dto: GraphPartDTO) -> None:
        """Reject a topology DTO whose references or hierarchy are invalid.

        Example:
            ```python
            TopologyLanguage().validate(GraphPartDTO())
            ```
        """
        from ..._private.transcription import validate_graph_part

        validate_graph_part(dto)

    def render(self, dto: GraphPartDTO, context: RenderContext) -> SourceFragment:
        """Render the topology DTO as authoring source.

        Example:
            ```python
            fragment = TopologyLanguage().render(GraphPartDTO(), None)
            assert fragment.body == ""
            ```
        """
        from ..service.source import render_graph_source

        return render_graph_source(dto, context)


__all__ = ["TopologyLanguage"]
