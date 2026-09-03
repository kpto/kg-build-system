"""Portable logical type vocabulary and canonicalization API."""

from .codec import decode_type, encode_type
from .models import (
    Array,
    ArrayType,
    BOOL,
    CANONICAL_UNIT_NAMES,
    CustomDataType,
    CustomType,
    DATE,
    Date,
    FLOAT,
    INT,
    LogicalType,
    NonNullableLogicalType,
    Nullable,
    NullableType,
    STR,
    Struct,
    StructType,
    TEXT_CANONICAL_UNIT_NAMES,
    TIME,
    TIMESTAMP,
    Time,
    Timestamp,
    UnitType,
    UnitTypeName,
    UUID,
    Uuid,
    canonical_value_text,
    is_canonical_unit_name,
)
from .normalization import UNIT_BY_REPRESENTATIVE_CLASS, normalize_type
from .validation import array_item, is_nullable, non_nullable, require_non_nullable, require_scalar

__all__ = [
    "Array", "ArrayType", "BOOL", "CANONICAL_UNIT_NAMES", "CustomDataType", "CustomType",
    "DATE", "Date", "FLOAT", "INT", "LogicalType", "NonNullableLogicalType", "Nullable",
    "NullableType", "STR", "Struct", "StructType", "TEXT_CANONICAL_UNIT_NAMES", "TIME",
    "TIMESTAMP", "Time", "Timestamp", "UNIT_BY_REPRESENTATIVE_CLASS", "UUID", "UnitType",
    "UnitTypeName", "Uuid", "array_item", "canonical_value_text", "decode_type", "encode_type",
    "is_canonical_unit_name", "is_nullable", "non_nullable", "normalize_type",
    "require_non_nullable", "require_scalar",
]
