"""Kernel-internal logical-type interface: DTOs, codecs and rules.

The canonical names are ``type_to_dto``, ``type_from_dto``,
``type_to_document`` and ``type_from_document``. Normalization and validation
are framework-internal rules beside the canonical model. Every name here is
either frozen type vocabulary, a DTO, or a thin wrapper over the private
implementation in ``kernel._private.types``.

Example:
    ```python
    from kg_build_system.kernel.internal.types import type_to_dto
    from kg_build_system.kernel.public.types import STR

    type_to_dto(STR)
    ```
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ...public.types import (
    Array, ArrayType, BOOL, CANONICAL_UNIT_NAMES, CustomDataType, CustomType,
    DATE, Date, FLOAT, INT, LogicalType, NonNullableLogicalType, Nullable,
    NullableType, STR, Shape, Struct, StructType, TEXT_CANONICAL_UNIT_NAMES,
    TIME, TIMESTAMP, Time, Timestamp, UUID, UnitType, UnitTypeName, Uuid,
    is_canonical_unit_name,
)
from .dto import (
    ArrayTypeDTO, CustomTypeDTO, LogicalTypeDTO, NonNullableLogicalTypeDTO,
    NullableTypeDTO, StructTypeDTO, UnitTypeDTO,
)


def type_to_dto(value: LogicalType) -> LogicalTypeDTO:
    """Return the serialisable DTO for a canonical logical type.

    Example:
        ```python
        from kg_build_system.kernel.internal.types import type_to_dto
        from kg_build_system.kernel.public.types import STR

        type_to_dto(STR)
        ```
    """
    from ..._private.types.codec import type_to_dto as implementation

    return implementation(value)


def type_from_dto(value: LogicalTypeDTO) -> LogicalType:
    """Rebuild a canonical logical type from its serialisable DTO.

    Example:
        ```python
        from kg_build_system.kernel.internal.types import (
            type_from_dto, type_to_dto,
        )
        from kg_build_system.kernel.public.types import STR

        assert type_from_dto(type_to_dto(STR)) == STR
        ```
    """
    from ..._private.types.codec import type_from_dto as implementation

    return implementation(value)


def type_to_document(value: LogicalTypeDTO) -> dict[str, Any]:
    """Serialise a logical-type DTO as a canonical JSON-compatible object.

    Example:
        ```python
        from kg_build_system.kernel.internal.types import (
            type_to_document, type_to_dto,
        )
        from kg_build_system.kernel.public.types import STR

        type_to_document(type_to_dto(STR))
        ```
    """
    from ..._private.types.codec import type_to_document as implementation

    return implementation(value)


def type_from_document(value: Mapping[str, Any]) -> LogicalTypeDTO:
    """Decode a canonical JSON object into a logical-type DTO.

    Example:
        ```python
        from kg_build_system.kernel.internal.types import type_from_document

        type_from_document({"kind": "unit", "name": "str"})
        ```
    """
    from ..._private.types.codec import type_from_document as implementation

    return implementation(value)


def normalize_type(value: Any) -> LogicalType:
    """Return the canonical logical type for a Python annotation.

    Example:
        ```python
        from kg_build_system.kernel.internal.types import normalize_type
        from kg_build_system.kernel.public.types import INT

        assert normalize_type(int) == INT
        ```
    """
    from ..._private.types.normalization import normalize_type as implementation

    return implementation(value)


def is_nullable(value: LogicalType) -> bool:
    """Return whether ``value`` is a canonical nullable wrapper.

    Example:
        ```python
        from kg_build_system.kernel.internal.types import is_nullable
        from kg_build_system.kernel.public.types import INT, NullableType

        assert is_nullable(NullableType(INT))
        ```
    """
    from ..._private.types.validation import is_nullable as implementation

    return implementation(value)


def non_nullable(value: LogicalType) -> LogicalType:
    """Return the value inside a nullable wrapper, or the value itself.

    Example:
        ```python
        from kg_build_system.kernel.internal.types import non_nullable
        from kg_build_system.kernel.public.types import INT, NullableType

        assert non_nullable(NullableType(INT)) == INT
        ```
    """
    from ..._private.types.validation import non_nullable as implementation

    return implementation(value)


def array_item(value: LogicalType) -> LogicalType:
    """Return the item type of a possibly nullable array.

    Example:
        ```python
        from kg_build_system.kernel.internal.types import array_item
        from kg_build_system.kernel.public.types import ArrayType, INT

        assert array_item(ArrayType(INT)) == INT
        ```
    """
    from ..._private.types.validation import array_item as implementation

    return implementation(value)


def require_non_nullable(value: LogicalType, *, context: str) -> LogicalType:
    """Return ``value``, raising when it is nullable.

    Example:
        ```python
        from kg_build_system.kernel.internal.types import require_non_nullable
        from kg_build_system.kernel.public.types import INT

        require_non_nullable(INT, context="field")
        ```
    """
    from ..._private.types.validation import (
        require_non_nullable as implementation,
    )

    return implementation(value, context=context)


def require_scalar(value: LogicalType, *, context: str) -> LogicalType:
    """Return ``value``, raising unless it is a possibly nullable scalar.

    Example:
        ```python
        from kg_build_system.kernel.internal.types import require_scalar
        from kg_build_system.kernel.public.types import INT

        require_scalar(INT, context="field")
        ```
    """
    from ..._private.types.validation import require_scalar as implementation

    return implementation(value, context=context)


def require_graph_property(value: LogicalType, *, context: str) -> LogicalType:
    """Return ``value``, raising unless it is a valid graph property type.

    Example:
        ```python
        from kg_build_system.kernel.internal.types import require_graph_property
        from kg_build_system.kernel.public.types import INT

        require_graph_property(INT, context="property")
        ```
    """
    from ..._private.types.validation import (
        require_graph_property as implementation,
    )

    return implementation(value, context=context)


def canonical_value_text(value: Date | Time | Timestamp | Uuid) -> str:
    """Return the canonical text form of a date, time, timestamp or UUID.

    Example:
        ```python
        from datetime import date
        from kg_build_system.kernel.internal.types import canonical_value_text

        canonical_value_text(date(2024, 1, 1))
        ```
    """
    from ..._private.types.values import canonical_value_text as implementation

    return implementation(value)


__all__ = [
    "Array", "ArrayType", "ArrayTypeDTO", "BOOL", "CANONICAL_UNIT_NAMES",
    "CustomDataType", "CustomType", "CustomTypeDTO", "DATE", "Date", "FLOAT",
    "INT", "LogicalType", "LogicalTypeDTO", "NonNullableLogicalType",
    "NonNullableLogicalTypeDTO", "Nullable", "NullableType", "NullableTypeDTO",
    "STR", "Shape", "Struct", "StructType", "StructTypeDTO",
    "TEXT_CANONICAL_UNIT_NAMES", "TIME", "TIMESTAMP", "Time", "Timestamp",
    "UUID", "UnitType", "UnitTypeDTO", "UnitTypeName", "Uuid", "array_item",
    "canonical_value_text", "is_canonical_unit_name", "is_nullable",
    "non_nullable", "normalize_type", "require_graph_property",
    "require_non_nullable", "require_scalar", "type_from_document",
    "type_from_dto", "type_to_document", "type_to_dto",
]
