"""Authoring alias for the kernel's canonical logical types.

An author imports the type vocabulary from here; every layer, the blueprint and
the contract use the same canonical type ontology. The definitions live in
:mod:`kg_build_system.kernel.model.public.types`.

Example:
    ```python
    from kg_build_system.types import Array, INT, Nullable

    Array[INT]
    Nullable[INT]
    ```
"""
from __future__ import annotations

from kg_build_system.kernel.model.public.types import (
    Array, ArrayType, BOOL, CANONICAL_UNIT_NAMES, CustomDataType, CustomType,
    DATE, Date, FLOAT, INT, LogicalType, NonNullableLogicalType, Nullable,
    NullableType, STR, Shape, Struct, StructType, TEXT_CANONICAL_UNIT_NAMES,
    TIME, TIMESTAMP, Time, Timestamp, UUID, UnitType, UnitTypeName, Uuid,
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
