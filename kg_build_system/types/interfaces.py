"""Internal logical-type interface."""
from __future__ import annotations

from .codec import decode_type, decode_type_ir, encode_type, encode_type_ir
from .mapping import type_to_ir
from .models import (
    Array, ArrayType, BOOL, CANONICAL_UNIT_NAMES, CustomDataType, CustomType,
    DATE, Date, FLOAT, INT, LogicalType, NonNullableLogicalType, Nullable,
    NullableType, STR, Shape, Struct, StructType, TEXT_CANONICAL_UNIT_NAMES,
    TIME, TIMESTAMP, Time, Timestamp, UUID, UnitType, UnitTypeName, Uuid,
    canonical_value_text, is_canonical_unit_name,
)
from .normalization import normalize_type
from .validation import (
    array_item, is_nullable, non_nullable, require_graph_property,
    require_non_nullable, require_scalar,
)

__all__ = [
    "Array", "ArrayType", "BOOL", "CANONICAL_UNIT_NAMES", "CustomDataType",
    "CustomType", "DATE", "Date", "FLOAT", "INT", "LogicalType",
    "NonNullableLogicalType", "Nullable", "NullableType", "STR", "Shape",
    "Struct", "StructType", "TEXT_CANONICAL_UNIT_NAMES", "TIME", "TIMESTAMP",
    "Time", "Timestamp", "UUID", "UnitType", "UnitTypeName", "Uuid",
    "array_item", "canonical_value_text", "decode_type", "decode_type_ir",
    "encode_type", "encode_type_ir", "is_canonical_unit_name", "is_nullable",
    "non_nullable", "normalize_type", "require_graph_property",
    "require_non_nullable", "require_scalar", "type_to_ir",
]
