"""Framework-internal topology model: DTOs and frozen declaration metadata."""
from __future__ import annotations

from .dto import EdgeDTO, GraphPartDTO, NodeDTO, PropertyDTO
from .model import ComponentMetadata, PropertyDeclaration

__all__ = [
    "ComponentMetadata", "EdgeDTO", "GraphPartDTO", "NodeDTO", "PropertyDTO",
    "PropertyDeclaration",
]
