"""Canonical document codec interface for the graph declaration.

The codec itself lives in the package's private zone; this module is the internal
entry point another layer composes.
"""
from __future__ import annotations

from typing import Any

from ...model.internal.dto.graph_dto import GraphDeclarationDTO


def graph_declaration_to_document(
    value: GraphDeclarationDTO,
) -> dict[str, Any]:
    """Encode the graph declaration as a JSON-compatible object.

    Example:
        ```python
        from kg_build_system.distribution.languages.graph.model.internal import (
            GraphDeclarationDTO,
        )
        from kg_build_system.distribution.languages.graph.service.internal import (
            graph_declaration_to_document,
        )
        ```
    """
    from .._private.codec import graph_declaration_to_document as encode

    return encode(value)


def graph_declaration_from_document(value: Any) -> GraphDeclarationDTO:
    """Rebuild the graph declaration from its JSON-compatible object.

    Example:
        ```python
        from kg_build_system.distribution.languages.graph.service.internal import (
            graph_declaration_from_document,
        )

        declaration = graph_declaration_from_document(document)
        ```
    """
    from .._private.codec import graph_declaration_from_document as decode

    return decode(value)


__all__ = [
    "graph_declaration_from_document", "graph_declaration_to_document",
]
