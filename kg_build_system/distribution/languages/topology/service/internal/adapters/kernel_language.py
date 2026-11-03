"""Adapter from topology declarations to the kernel ``topology`` layer.

``TopologyLanguage`` implements the kernel language shape: ``collect`` selects
declarations, ``transcribe`` produces a ``Layer`` wrapping :class:`GraphPartDTO`,
``validate`` checks the DTO invariants and ``render`` returns authoring source.
The class does not carry a live declaration into the DTO.
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

from ....model.internal.dto.blueprint_dto import GraphPartDTO
from ..source import render_graph_source
from ..transcription import (
    collect_components, transcribe_graph_part, validate_graph_part,
)


class TopologyLanguage(Language):
    """The ``topology`` language: collect declarations, transcribe to a DTO.

    Collection includes abstract parents and edge endpoint categories even when
    a namespace only exposes bindings.

    Example:
        ```python
        from kg_build_system.distribution.languages.topology.service.internal import (
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
        return collect_components(namespace)

    def transcribe(
        self, declarations: Sequence[object], context: LanguageContext,
    ) -> Layer:
        """Turn collected declarations into a topology layer.

        Example:
            ```python
            layer = TopologyLanguage().transcribe((SiteNode,), context)
            assert isinstance(layer.value, GraphPartDTO)
            ```
        """
        return Layer(self.name, transcribe_graph_part(declarations, context))

    def validate(self, layer: Layer) -> None:
        """Reject a topology layer whose references or hierarchy are invalid.

        Example:
            ```python
            TopologyLanguage().validate(Layer("topology", GraphPartDTO()))
            ```
        """
        if layer.language != self.name:
            raise ValueError(
                f"topology language received layer {layer.language!r}"
            )
        if not isinstance(layer.value, GraphPartDTO):
            raise TypeError("the topology language transcribes to GraphPartDTO")
        validate_graph_part(layer.value)

    def render(self, layer: Any, context: RenderContext) -> SourceFragment:
        """Render the topology layer as authoring source.

        Example:
            ```python
            fragment = TopologyLanguage().render(
                Layer("topology", GraphPartDTO()), None,
            )
            assert fragment.body == ""
            ```
        """
        value = layer.value if isinstance(layer, Layer) else layer
        return render_graph_source(value, context)


__all__ = ["TopologyLanguage"]
