"""Canonical logical types and the authoring markers an author writes.

The canonical model lives in :mod:`.model`; the authoring markers and
representative aliases live in :mod:`.markers`. The package re-exports both.

Example:
    ```python
    from kg_build_system.kernel.model.public.types import Array, INT, Nullable

    Array[INT]
    Nullable[INT]
    ```
"""
from __future__ import annotations

from .markers import (
    Array, CustomDataType, Date, Nullable, Shape, Struct, Time, Timestamp, Uuid,
)
from .model import (
    BOOL, CANONICAL_UNIT_NAMES, DATE, FLOAT, INT, STR, TEXT_CANONICAL_UNIT_NAMES,
    TIME, TIMESTAMP, UUID, ArrayType, CustomType, LogicalType,
    NonNullableLogicalType, NullableType, StructType, UnitType, UnitTypeName,
    is_canonical_unit_name,
)

__all__ = [
    "Array", "ArrayType", "BOOL", "CANONICAL_UNIT_NAMES", "CustomDataType",
    "CustomType", "DATE", "Date", "FLOAT", "INT", "LogicalType",
    "NonNullableLogicalType", "Nullable", "NullableType", "STR", "Shape",
    "Struct", "StructType", "TEXT_CANONICAL_UNIT_NAMES", "TIME", "TIMESTAMP",
    "Time", "Timestamp", "UUID", "UnitType", "UnitTypeName", "Uuid",
    "is_canonical_unit_name",
]
