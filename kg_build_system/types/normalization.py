"""Normalize Python annotations into the canonical logical type."""
from __future__ import annotations

import types as pytypes
from typing import Any, Union, get_args, get_origin

from .models import (
    Array, ArrayType, CustomDataType, CustomType, Date, LogicalType, Nullable,
    NullableType, Shape, Struct, StructType, Time, Timestamp, UnitType, Uuid,
    INT, FLOAT, STR, BOOL, DATE, TIME, TIMESTAMP, UUID,
)

_UNITS: dict[type[Any], UnitType] = {
    bool: BOOL, int: INT, float: FLOAT, str: STR,
    Date: DATE, Time: TIME, Timestamp: TIMESTAMP, Uuid: UUID,
}


def normalize_type(value: Any) -> LogicalType:
    if isinstance(value, (UnitType, CustomType, StructType, ArrayType, NullableType)):
        return value
    origin = get_origin(value)
    if origin in (Union, pytypes.UnionType):
        args = get_args(value)
        non_none = tuple(item for item in args if item is not type(None))
        if len(non_none) != len(args) - 1 or len(non_none) != 1:
            raise TypeError(f"unsupported optional type {value!r}")
        return NullableType(_non_nullable(normalize_type(non_none[0])))
    if origin is Nullable:
        args = get_args(value)
        if len(args) != 1:
            raise TypeError("Nullable requires exactly one item type")
        return NullableType(_non_nullable(normalize_type(args[0])))
    if origin is Array:
        args = get_args(value)
        if len(args) != 1:
            raise TypeError("Array requires exactly one item type")
        return ArrayType(normalize_type(args[0]))
    return _non_nullable(_scalar(value))


def _non_nullable(value: LogicalType) -> Any:
    if isinstance(value, NullableType):
        return value.value
    return value


def _scalar(value: Any) -> LogicalType:
    if value in _UNITS:
        return _UNITS[value]
    if isinstance(value, type) and issubclass(value, CustomDataType):
        return CustomType(value.__module__, value.__qualname__)
    if isinstance(value, type) and issubclass(value, Struct):
        return StructType(value.__module__, value.__qualname__)
    if isinstance(value, type) and issubclass(value, Shape):
        raise TypeError("a row source is not a value record")
    raise TypeError(f"unsupported annotation {value!r}")


__all__ = ["normalize_type"]
