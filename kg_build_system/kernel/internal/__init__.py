"""Kernel-internal interface.

The kernel's internal type surface is :mod:`kg_build_system.kernel.internal.types`.
The module re-exports it so another package can import the kernel's internal
logical-type DTOs, codecs and rules from one declared zone.

Example:
    ```python
    from kg_build_system.kernel.internal import type_to_dto
    from kg_build_system.kernel.public.types import STR

    type_to_dto(STR)
    ```
"""
from __future__ import annotations

from .types import (
    ArrayTypeDTO, CustomTypeDTO, LogicalTypeDTO, NonNullableLogicalTypeDTO,
    NullableTypeDTO, StructTypeDTO, UnitTypeDTO, array_item,
    canonical_value_text, is_nullable, non_nullable, normalize_type,
    require_graph_property, require_non_nullable, require_scalar,
    type_from_document, type_from_dto, type_to_document, type_to_dto,
)

__all__ = [
    "ArrayTypeDTO", "CustomTypeDTO", "LogicalTypeDTO",
    "NonNullableLogicalTypeDTO", "NullableTypeDTO", "StructTypeDTO",
    "UnitTypeDTO", "array_item", "canonical_value_text", "is_nullable",
    "non_nullable", "normalize_type", "require_graph_property",
    "require_non_nullable", "require_scalar", "type_from_document",
    "type_from_dto", "type_to_document", "type_to_dto",
]
