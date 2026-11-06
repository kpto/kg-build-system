"""Render the graph declaration DTO back to authoring source.

The renderer lives in the package's private zone; this module is the internal
entry point another layer composes.
"""
from __future__ import annotations

from typing import Any

from kg_build_system.kernel import SourceFragment

from ...model.internal.dto.graph_dto import GraphDeclarationDTO


def render_graph_declaration_source(
    value: GraphDeclarationDTO, context: Any = None,
) -> SourceFragment:
    """Render a graph declaration DTO as deterministic authoring source.

    Example:
        ```python
        from kg_build_system.distribution.languages.graph.model.internal import (
            GraphDeclarationDTO,
        )
        from kg_build_system.distribution.languages.graph.service.internal import (
            render_graph_declaration_source,
        )

        fragment = render_graph_declaration_source(declaration)
        ```
    """
    from .._private.source import (
        render_graph_declaration_source as render,
    )

    return render(value, context)


__all__ = ["render_graph_declaration_source"]
