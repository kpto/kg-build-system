"""Internal logical-type interface."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, TypeGuard

from .codec import (
    decode_type as _decode_type,
    decode_type_ir as _decode_type_ir,
    encode_type as _encode_type,
    encode_type_ir as _encode_type_ir,
)
from .ir import LogicalTypeIR
from .mapping import type_to_ir as _type_to_ir
from .models import (
    Array, ArrayType, BOOL, CANONICAL_UNIT_NAMES, CustomDataType, CustomType,
    DATE, Date, FLOAT, INT, LogicalType, NonNullableLogicalType, Nullable,
    NullableType, STR, Shape, Struct, StructType, TEXT_CANONICAL_UNIT_NAMES,
    TIME, TIMESTAMP, Time, Timestamp, UUID, UnitType, UnitTypeName, Uuid,
    canonical_value_text as _canonical_value_text,
    is_canonical_unit_name as _is_canonical_unit_name,
)
from .normalization import normalize_type as _normalize_type
from .validation import (
    array_item as _array_item,
    is_nullable as _is_nullable,
    non_nullable as _non_nullable,
    require_graph_property as _require_graph_property,
    require_non_nullable as _require_non_nullable,
    require_scalar as _require_scalar,
)


def normalize_type(value: Any) -> LogicalType:
    """Normalize a Python annotation or logical type to the canonical type.

    A canonical logical type is returned unchanged; ``str | None`` becomes a
    nullable unit and ``Array[str]`` becomes an array of unit strings.

    Example:
        ```python
        from kg_build_system.types import Array
        from kg_build_system.types.interfaces import normalize_type

        normalize_type(str | None)
        normalize_type(Array[str])
        ```
    """
    return _normalize_type(value)


def is_nullable(value: LogicalType) -> bool:
    """Return whether a logical type is wrapped in ``NullableType``.

    Example:
        ```python
        from kg_build_system.types import INT
        from kg_build_system.types.interfaces import is_nullable, normalize_type

        is_nullable(normalize_type(int | None))
        is_nullable(INT)
        ```
    """
    return _is_nullable(value)


def non_nullable(value: LogicalType) -> LogicalType:
    """Strip one top-level ``NullableType`` wrapper and return the inner type.

    A value that is already non-nullable is returned unchanged.

    Example:
        ```python
        from kg_build_system.types.interfaces import non_nullable, normalize_type

        non_nullable(normalize_type(str | None))
        ```
    """
    return _non_nullable(value)


def array_item(value: LogicalType) -> LogicalType:
    """Return the item type of an array, unwrapping a nullable array first.

    Raises ``TypeError`` when the value is not an array. Item nullability is
    preserved.

    Example:
        ```python
        from kg_build_system.types import Array
        from kg_build_system.types.interfaces import array_item, normalize_type

        array_item(normalize_type(Array[str]))
        ```
    """
    return _array_item(value)


def require_graph_property(value: LogicalType, *, context: str) -> LogicalType:
    """Require a value a graph property can hold and return it unchanged.

    A scalar and a one-level array of non-null scalars are accepted. A struct,
    a nested array and an array with nullable items are rejected.

    Example:
        ```python
        from kg_build_system.types import Array
        from kg_build_system.types.interfaces import (
            normalize_type, require_graph_property,
        )

        require_graph_property(normalize_type(Array[str]), context="tags")
        ```
    """
    return _require_graph_property(value, context=context)


def require_non_nullable(value: LogicalType, *, context: str) -> LogicalType:
    """Require a non-nullable logical type and return it unchanged.

    Raises ``TypeError`` naming ``context`` when the value is nullable.

    Example:
        ```python
        from kg_build_system.types import STR
        from kg_build_system.types.interfaces import require_non_nullable

        require_non_nullable(STR, context="key")
        ```
    """
    return _require_non_nullable(value, context=context)


def require_scalar(value: LogicalType, *, context: str) -> LogicalType:
    """Require a scalar logical type and return it unchanged.

    A nullable scalar is accepted; an array or a nested container is rejected.

    Example:
        ```python
        from kg_build_system.types.interfaces import normalize_type, require_scalar

        require_scalar(normalize_type(str | None), context="name")
        ```
    """
    return _require_scalar(value, context=context)


def type_to_ir(value: LogicalType) -> LogicalTypeIR:
    """Lower a logical type to its frozen compilation IR value.

    Example:
        ```python
        from kg_build_system.types import STR
        from kg_build_system.types.interfaces import type_to_ir

        type_to_ir(STR)
        ```
    """
    return _type_to_ir(value)


def encode_type(value: LogicalType) -> dict[str, Any]:
    """Encode a logical type as a canonical JSON-compatible object.

    Example:
        ```python
        from kg_build_system.types import STR
        from kg_build_system.types.interfaces import encode_type

        encode_type(STR)
        ```
    """
    return _encode_type(value)


def decode_type(value: Mapping[str, Any]) -> LogicalType:
    """Decode a canonical JSON object into a logical type.

    Example:
        ```python
        from kg_build_system.types.interfaces import decode_type

        decode_type({"kind": "unit", "name": "str"})
        ```
    """
    return _decode_type(value)


def encode_type_ir(value: LogicalTypeIR) -> dict[str, Any]:
    """Encode a logical-type IR value as a canonical JSON-compatible object.

    Example:
        ```python
        from kg_build_system.types import STR
        from kg_build_system.types.interfaces import encode_type_ir, type_to_ir

        encode_type_ir(type_to_ir(STR))
        ```
    """
    return _encode_type_ir(value)


def decode_type_ir(value: Mapping[str, Any]) -> LogicalTypeIR:
    """Decode a canonical JSON object into a logical-type IR value.

    Example:
        ```python
        from kg_build_system.types.interfaces import decode_type_ir

        decode_type_ir({"kind": "unit", "name": "str"})
        ```
    """
    return _decode_type_ir(value)


def canonical_value_text(value: Date | Time | Timestamp | Uuid) -> str:
    """Return the canonical text form of a date, time, timestamp or UUID.

    Dates and times use ``isoformat()`` and UUIDs use lowercase hyphenated
    text. Other values raise ``TypeError``.

    Example:
        ```python
        import datetime
        from kg_build_system.types.interfaces import canonical_value_text

        canonical_value_text(datetime.date(2026, 11, 2))
        ```
    """
    return _canonical_value_text(value)


def is_canonical_unit_name(name: str) -> TypeGuard[UnitTypeName]:
    """Return whether ``name`` is one of the canonical unit type names.

    Example:
        ```python
        from kg_build_system.types.interfaces import is_canonical_unit_name

        is_canonical_unit_name("timestamp")
        is_canonical_unit_name("Timestamp")
        ```
    """
    return _is_canonical_unit_name(name)


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
