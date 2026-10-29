"""Normalize Python authoring annotations into canonical logical types."""
from __future__ import annotations

from types import NoneType, UnionType
from typing import Any, Final, get_args, get_origin

from .models import (
    Shape,
    Array, ArrayType, BOOL, CustomDataType, CustomType, DATE, Date, FLOAT, INT, LogicalType,
    Nullable, NullableType, STR, Struct, StructType, TIME, TIMESTAMP, Time, Timestamp, UnitType,
    UUID, Uuid,
)


# The keys are the stdlib classes the representative aliases name, so an author
# writing ``Date`` or ``datetime.date`` normalizes to the same canonical unit. The
# one class-to-unit fact every exact-class dispatch reads is this mapping.
UNIT_BY_REPRESENTATIVE_CLASS: Final[dict[type[Any], UnitType]] = {
    bool: BOOL, int: INT, float: FLOAT, str: STR,
    Date: DATE, Time: TIME, Timestamp: TIMESTAMP, Uuid: UUID,
}


def _declared_type(annotation: type[Any], kind: type[CustomType] | type[StructType]) -> CustomType | StructType:
    if "<locals>" in annotation.__qualname__:
        raise TypeError("logical type declarations must be importable top-level classes")
    return kind(module=annotation.__module__, qualname=annotation.__qualname__)


def _nullable(argument: Any) -> NullableType:
    normalized = normalize_type(argument)
    if isinstance(normalized, NullableType):
        return normalized
    return NullableType(normalized)


def normalize_type(annotation: Any) -> LogicalType:
    """Convert one supported authoring annotation to canonical form."""
    if annotation is Any:
        raise TypeError("logical types must be explicit; Any is not supported")
    if annotation in UNIT_BY_REPRESENTATIVE_CLASS:
        return UNIT_BY_REPRESENTATIVE_CLASS[annotation]

    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin is Array:
        if len(arguments) != 1:
            raise TypeError("Array must declare exactly one item type")
        return ArrayType(normalize_type(arguments[0]))
    if origin is Nullable:
        if len(arguments) != 1:
            raise TypeError("Nullable must declare exactly one value type")
        return _nullable(arguments[0])
    if origin is UnionType or str(origin) == "typing.Union":
        non_null = tuple(argument for argument in arguments if argument is not NoneType)
        if len(non_null) == 1 and len(arguments) == 2:
            return _nullable(non_null[0])
        raise TypeError("logical unions are limited to T | None")

    if isinstance(annotation, type) and issubclass(annotation, CustomDataType):
        return _declared_type(annotation, CustomType)
    if isinstance(annotation, type) and issubclass(annotation, Struct):
        if not getattr(annotation, "_kg_value_record", True):
            raise TypeError(
                f"{annotation.__name__} is a row source, not a value record; "
                "field types must be Struct or ComputedStruct declarations"
            )
        return _declared_type(annotation, StructType)
    if isinstance(annotation, type) and issubclass(annotation, Shape):
        raise TypeError(
            f"{annotation.__name__} is a row source, not a value record; "
            "field types must be Struct or ComputedStruct declarations"
        )
    raise TypeError(f"unsupported logical type annotation: {annotation!r}")


__all__ = ["UNIT_BY_REPRESENTATIVE_CLASS", "normalize_type"]
