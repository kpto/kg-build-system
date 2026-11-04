"""Kernel-internal logical-type interface.

This is the service-side interface to the type rules: each name is a thin
wrapper over ``kernel.model._private.types``. The DTOs themselves live in
``kernel.model.internal.types``.
"""
from __future__ import annotations

from .functions import (
    array_item, canonical_value_text, is_nullable, non_nullable, normalize_type,
    require_graph_property, require_non_nullable, require_scalar,
    type_from_document, type_from_dto, type_to_document, type_to_dto,
)

__all__ = [
    "array_item", "canonical_value_text", "is_nullable", "non_nullable",
    "normalize_type", "require_graph_property", "require_non_nullable",
    "require_scalar", "type_from_document", "type_from_dto",
    "type_to_document", "type_to_dto",
]
