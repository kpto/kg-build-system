"""Render the topology blueprint DTO as authoring source."""
from __future__ import annotations

from typing import Any

from kg_build_system.kernel import SourceFragment

from ...model.internal.dto.blueprint_dto import GraphPartDTO


def render_graph_source(part: GraphPartDTO, context: Any) -> SourceFragment:
    """Render a topology DTO as authoring source.

    The fragment declares one class per component, parents before children.
    Properties, labels and annotations use the shared type and annotation
    renderers, and every graph name is written explicitly in ``options``.

    Example:
        ```python
        from kg_build_system.distribution.languages.topology.model.internal.dto import (
            GraphPartDTO, NodeDTO,
        )
        from kg_build_system.distribution.languages.topology.service.internal import (
            render_graph_source,
        )

        fragment = render_graph_source(
            GraphPartDTO(nodes=(NodeDTO("site"),)), None,
        )
        ```
    """
    from .._private.source import render_graph_source as render

    return render(part, context)


__all__ = ["render_graph_source"]
