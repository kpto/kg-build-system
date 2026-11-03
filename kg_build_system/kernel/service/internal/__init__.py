"""Kernel service-internal interface: registry composition and type rules."""
from __future__ import annotations

from .registry import compose, order_languages
from .types import (
    array_item, canonical_value_text, is_nullable, non_nullable, normalize_type,
    require_graph_property, require_non_nullable, require_scalar,
    type_from_document, type_from_dto, type_to_document, type_to_dto,
)

__all__ = [
    "array_item", "canonical_value_text", "compose", "is_nullable",
    "non_nullable", "normalize_type", "order_languages",
    "require_graph_property", "require_non_nullable", "require_scalar",
    "type_from_document", "type_from_dto", "type_to_document", "type_to_dto",
]
