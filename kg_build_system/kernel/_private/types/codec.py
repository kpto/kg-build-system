"""Codecs between canonical logical types, their DTOs and canonical documents.

Private implementation behind ``kernel.internal.types``. ``type_to_dto`` and
``type_from_dto`` move between the canonical model and its serialisable DTO.
``type_to_document`` and ``type_from_document`` serialise a DTO as a canonical
JSON-compatible object keyed by ``kind``.

Example:
    ```python
    from kg_build_system.kernel.internal.types import (
        type_from_document, type_to_document, type_to_dto,
    )
    from kg_build_system.kernel.public.types import STR

    document = type_to_document(type_to_dto(STR))
    assert type_from_document(document) == type_to_dto(STR)
    ```
"""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from ...internal.types.dto import (
    ArrayTypeDTO, CustomTypeDTO, LogicalTypeDTO, NonNullableLogicalTypeDTO,
    NullableTypeDTO, StructTypeDTO, UnitTypeDTO,
)
from ...public.types.model import (
    ArrayType, CustomType, LogicalType, NonNullableLogicalType, NullableType,
    StructType, UnitType, is_canonical_unit_name,
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
    if isinstance(value, UnitType):
        return UnitTypeDTO(value.name)
    if isinstance(value, CustomType):
        return CustomTypeDTO(value.module, value.qualname)
    if isinstance(value, StructType):
        return StructTypeDTO(value.module, value.qualname)
    if isinstance(value, ArrayType):
        return ArrayTypeDTO(type_to_dto(value.item))
    if isinstance(value, NullableType):
        return NullableTypeDTO(
            cast(NonNullableLogicalTypeDTO, type_to_dto(value.value))
        )
    raise TypeError(f"unsupported logical type {value!r}")


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
    if isinstance(value, UnitTypeDTO):
        return UnitType(value.name)
    if isinstance(value, CustomTypeDTO):
        return CustomType(value.module, value.qualname)
    if isinstance(value, StructTypeDTO):
        return StructType(value.module, value.qualname)
    if isinstance(value, ArrayTypeDTO):
        return ArrayType(type_from_dto(value.item))
    if isinstance(value, NullableTypeDTO):
        inner = type_from_dto(value.value)
        if isinstance(inner, NullableType):
            raise ValueError("canonical nullable types may not be nested")
        return NullableType(cast(NonNullableLogicalType, inner))
    raise TypeError(f"unsupported logical type DTO {value!r}")


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
    if isinstance(value, UnitTypeDTO):
        return {"kind": "unit", "name": value.name}
    if isinstance(value, CustomTypeDTO):
        return {"kind": "custom", "module": value.module, "qualname": value.qualname}
    if isinstance(value, StructTypeDTO):
        return {"kind": "struct", "module": value.module, "qualname": value.qualname}
    if isinstance(value, ArrayTypeDTO):
        return {"kind": "array", "item": type_to_document(value.item)}
    if isinstance(value, NullableTypeDTO):
        return {"kind": "nullable", "value": type_to_document(value.value)}
    raise TypeError(f"unsupported logical type DTO {value!r}")


def _text(value: Mapping[str, Any], key: str) -> str:
    item = value.get(key)
    if not isinstance(item, str) or not item:
        raise ValueError(f"logical type field {key!r} must be a non-empty string")
    return item


def _mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    item = value.get(key)
    if not isinstance(item, Mapping):
        raise ValueError(f"logical type field {key!r} must be an object")
    return item


def type_from_document(value: Mapping[str, Any]) -> LogicalTypeDTO:
    """Decode a canonical JSON object into a logical-type DTO.

    Example:
        ```python
        from kg_build_system.kernel.internal.types import type_from_document

        type_from_document({"kind": "unit", "name": "str"})
        ```
    """
    kind = value.get("kind")
    if kind == "unit":
        name = _text(value, "name")
        if not is_canonical_unit_name(name):
            raise ValueError(f"unknown unit logical type {name!r}")
        return UnitTypeDTO(name)
    if kind == "custom":
        return CustomTypeDTO(_text(value, "module"), _text(value, "qualname"))
    if kind == "struct":
        return StructTypeDTO(_text(value, "module"), _text(value, "qualname"))
    if kind == "array":
        return ArrayTypeDTO(type_from_document(_mapping(value, "item")))
    if kind == "nullable":
        inner = type_from_document(_mapping(value, "value"))
        if isinstance(inner, NullableTypeDTO):
            raise ValueError("canonical nullable types may not be nested")
        return NullableTypeDTO(cast(NonNullableLogicalTypeDTO, inner))
    raise ValueError(f"unknown logical type kind {kind!r}")


__all__ = [
    "type_from_document", "type_from_dto", "type_to_document", "type_to_dto",
]
