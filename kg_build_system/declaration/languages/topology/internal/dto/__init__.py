"""The topology blueprint DTO and its canonical codec."""
from __future__ import annotations

from .blueprint_dto import EdgeDTO, GraphPartDTO, NodeDTO, PropertyDTO
from .codec import graph_from_document, graph_to_document

__all__ = [
    "EdgeDTO", "GraphPartDTO", "NodeDTO", "PropertyDTO", "graph_from_document",
    "graph_to_document",
]
