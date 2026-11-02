"""Predicates and requirements over canonical logical types."""
from __future__ import annotations

from ..public.models import (
    ArrayType, CustomType, LogicalType, NullableType, StructType, UnitType,
)


def is_nullable(value: LogicalType) -> bool:
    return isinstance(value, NullableType)


def non_nullable(value: LogicalType) -> LogicalType:
    return value.value if isinstance(value, NullableType) else value


def array_item(value: LogicalType) -> LogicalType:
    base = non_nullable(value)
    if not isinstance(base, ArrayType):
        raise TypeError("expected an array logical type")
    return base.item


def require_non_nullable(value: LogicalType, *, context: str) -> LogicalType:
    if isinstance(value, NullableType):
        raise TypeError(f"{context} must be non-nullable")
    return value


def require_scalar(value: LogicalType, *, context: str) -> LogicalType:
    base = non_nullable(value)
    if not isinstance(base, (UnitType, CustomType, StructType)):
        raise TypeError(f"{context} must be scalar")
    return value


def require_graph_property(value: LogicalType, *, context: str) -> LogicalType:
    base = non_nullable(value)
    if isinstance(base, StructType):
        raise TypeError(f"{context} cannot be a nested record")
    if isinstance(base, ArrayType):
        item = non_nullable(base.item)
        if isinstance(item, (ArrayType, StructType)):
            raise TypeError(f"{context} must be an array of scalars")
    return value


__all__ = [
    "array_item", "is_nullable", "non_nullable", "require_graph_property",
    "require_non_nullable", "require_scalar",
]
