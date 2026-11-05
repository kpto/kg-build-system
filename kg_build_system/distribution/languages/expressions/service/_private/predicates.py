"""Predicates over canonical logical types used by operation specifications."""
from __future__ import annotations

from collections.abc import Callable

from kg_build_system.kernel.model.public.types import ArrayType, LogicalType, NullableType, StructType, UnitType
from kg_build_system.kernel.service.internal.types import non_nullable

type TypePredicate = Callable[[LogicalType], bool]


def is_unit(*names: str) -> TypePredicate:
    """Return a predicate accepting one of the named unit logical types."""
    expected = frozenset(names)

    def predicate(logical_type: LogicalType) -> bool:
        base = non_nullable(logical_type)
        return isinstance(base, UnitType) and base.name in expected

    return predicate


def is_exact(logical_type: LogicalType) -> TypePredicate:
    return lambda value: value == logical_type


def is_numeric(logical_type: LogicalType) -> bool:
    base = non_nullable(logical_type)
    return isinstance(base, UnitType) and base.name in {"int", "float"}


def is_array(logical_type: LogicalType) -> bool:
    return isinstance(non_nullable(logical_type), ArrayType)


def is_struct(logical_type: LogicalType) -> bool:
    return isinstance(non_nullable(logical_type), StructType)


def is_array_of(predicate: TypePredicate) -> TypePredicate:
    def check(logical_type: LogicalType) -> bool:
        base = non_nullable(logical_type)
        if not isinstance(base, ArrayType):
            return False
        return predicate(base.item)

    return check


def is_non_null_unit(*names: str) -> TypePredicate:
    expected = frozenset(names)
    return lambda value: (
        isinstance(value, UnitType) and value.name in expected
    )


def is_scalar_unit(logical_type: LogicalType) -> bool:
    return isinstance(non_nullable(logical_type), UnitType)


__all__ = [
    "TypePredicate", "is_array", "is_array_of", "is_exact", "is_non_null_unit",
    "is_numeric", "is_scalar_unit", "is_struct", "is_unit",
]
