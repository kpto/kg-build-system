"""Queries and contextual validation for canonical logical types."""
from __future__ import annotations

from .models import ArrayType, CustomType, LogicalType, NullableType, StructType, UnitType


def is_nullable(logical_type: LogicalType) -> bool:
    return isinstance(logical_type, NullableType)


def non_nullable(logical_type: LogicalType) -> UnitType | CustomType | StructType | ArrayType:
    return logical_type.value if isinstance(logical_type, NullableType) else logical_type


def array_item(logical_type: LogicalType) -> LogicalType | None:
    base = non_nullable(logical_type)
    return base.item if isinstance(base, ArrayType) else None


def require_non_nullable(logical_type: LogicalType, *, context: str) -> LogicalType:
    if is_nullable(logical_type):
        raise TypeError(f"{context} must not be nullable")
    return logical_type


def require_scalar(logical_type: LogicalType, *, context: str) -> LogicalType:
    if isinstance(non_nullable(logical_type), (ArrayType, StructType)):
        raise TypeError(f"{context} must be a scalar")
    return logical_type


def require_graph_property(logical_type: LogicalType, *, context: str) -> LogicalType:
    """Accept a scalar, or a one-level array of non-null scalars, as a graph property.

    Struct members and nested arrays stay expression-only values: a property
    must survive as a Neo4j/JSON scalar or a flat homogeneous list. Nullable
    array items are refused because no target stores them faithfully — the
    author converts explicitly with ``where_items_present()``.
    """
    base = non_nullable(logical_type)
    if not isinstance(base, ArrayType):
        return require_scalar(logical_type, context=context)
    if isinstance(base.item, (ArrayType, StructType)):
        raise TypeError(
            f"{context} array properties require scalar items; flatten nested "
            "structures with expand() instead"
        )
    if isinstance(base.item, NullableType):
        raise TypeError(
            f"{context} array properties require non-null items; apply "
            "where_items_present() to drop null items"
        )
    return logical_type


__all__ = [
    "array_item", "is_nullable", "non_nullable", "require_graph_property",
    "require_non_nullable", "require_scalar",
]
