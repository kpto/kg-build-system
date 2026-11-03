"""Canonical JSON codec for the topology blueprint DTO."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ...model.internal.dto.blueprint_dto import GraphPartDTO


def graph_to_document(part: GraphPartDTO) -> dict[str, Any]:
    """Encode the topology part as a JSON-compatible object.

    Example:
        ```python
        from kg_build_system.declaration.languages.topology.model.internal.dto import (
            GraphPartDTO, graph_to_document,
        )

        document = graph_to_document(GraphPartDTO())
        assert document == {"nodes": [], "edges": []}
        ```
    """
    from .._private.codec import graph_to_document as encode

    return encode(part)


def graph_from_document(document: Mapping[str, Any]) -> GraphPartDTO:
    """Rebuild the topology part from its JSON-compatible object.

    Example:
        ```python
        from kg_build_system.declaration.languages.topology.model.internal.dto import (
            graph_from_document,
        )

        part = graph_from_document({"nodes": [], "edges": []})
        ```
    """
    from .._private.codec import graph_from_document as decode

    return decode(document)


__all__ = ["graph_from_document", "graph_to_document"]
