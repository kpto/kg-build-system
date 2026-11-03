"""Kernel-internal logical-type interface: model, DTOs, codecs and rules.

The canonical names are ``type_to_dto``, ``type_from_dto``,
``type_to_document`` and ``type_from_document``. Normalization and validation
are framework-internal rules beside the canonical model; the canonical names
are re-exported here so a framework package has one declared zone.

Example:
    ```python
    from kg_build_system.kernel.internal.types import type_to_dto
    from kg_build_system.kernel.public.types import STR

    type_to_dto(STR)
    ```
"""
from __future__ import annotations

from ...public.types import (
    Array, ArrayType, BOOL, CANONICAL_UNIT_NAMES, CustomDataType, CustomType,
    DATE, Date, FLOAT, INT, LogicalType, NonNullableLogicalType, Nullable,
    NullableType, STR, Shape, Struct, StructType, TEXT_CANONICAL_UNIT_NAMES,
    TIME, TIMESTAMP, Time, Timestamp, UUID, UnitType, UnitTypeName, Uuid,
    is_canonical_unit_name,
)
from .codec import (
    type_from_document, type_from_dto, type_to_document, type_to_dto,
)
from .dto import (
    ArrayTypeDTO, CustomTypeDTO, LogicalTypeDTO, NonNullableLogicalTypeDTO,
    NullableTypeDTO, StructTypeDTO, UnitTypeDTO,
)
from .normalization import normalize_type
from .validation import (
    array_item, is_nullable, non_nullable, require_graph_property,
    require_non_nullable, require_scalar,
)
from .values import canonical_value_text

__all__ = [
    "Array", "ArrayType", "ArrayTypeDTO", "BOOL", "CANONICAL_UNIT_NAMES",
    "CustomDataType", "CustomType", "CustomTypeDTO", "DATE", "Date", "FLOAT",
    "INT", "LogicalType", "LogicalTypeDTO", "NonNullableLogicalType",
    "NonNullableLogicalTypeDTO", "Nullable", "NullableType", "NullableTypeDTO",
    "STR", "Shape", "Struct", "StructType", "StructTypeDTO",
    "TEXT_CANONICAL_UNIT_NAMES", "TIME", "TIMESTAMP", "Time", "Timestamp",
    "UUID", "UnitType", "UnitTypeDTO", "UnitTypeName", "Uuid", "array_item",
    "canonical_value_text", "is_canonical_unit_name", "is_nullable",
    "non_nullable", "normalize_type", "require_graph_property",
    "require_non_nullable", "require_scalar", "type_from_document",
    "type_from_dto", "type_to_document", "type_to_dto",
]
