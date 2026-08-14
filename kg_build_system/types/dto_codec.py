"""Stable JSON codec for compilation logical-type DTOs."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any, cast

from .dto import (
    ArrayTypeDTO, CustomTypeDTO, LogicalTypeDTO, NullableTypeDTO, StructTypeDTO,
    UnitTypeDTO,
)


def encode_type_dto(value: LogicalTypeDTO) -> dict[str, Any]:
    if isinstance(value, UnitTypeDTO):
        return {"kind": "unit", "name": value.name}
    if isinstance(value, CustomTypeDTO):
        return {"kind": "custom", "module": value.module, "qualname": value.qualname}
    if isinstance(value, StructTypeDTO):
        return {"kind": "struct", "module": value.module, "qualname": value.qualname}
    if isinstance(value, ArrayTypeDTO):
        return {"kind": "array", "item": encode_type_dto(value.item)}
    if isinstance(value, NullableTypeDTO):
        return {"kind": "nullable", "value": encode_type_dto(value.value)}
    raise TypeError(f"unsupported logical type DTO {value!r}")


def _text(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"logical type field {key!r} must be a non-empty string")
    return result


def _object(value: Any, key: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"logical type field {key!r} must be an object")
    return value


def decode_type_dto(value: Mapping[str, Any]) -> LogicalTypeDTO:
    kind = value.get("kind")
    if kind == "unit":
        name = _text(value, "name")
        if name not in {"bool", "int", "float", "str"}:
            raise ValueError(f"unknown unit type {name!r}")
        return UnitTypeDTO(cast(Any, name))
    if kind == "custom":
        return CustomTypeDTO(_text(value, "module"), _text(value, "qualname"))
    if kind == "struct":
        return StructTypeDTO(_text(value, "module"), _text(value, "qualname"))
    if kind == "array":
        return ArrayTypeDTO(decode_type_dto(_object(value.get("item"), "item")))
    if kind == "nullable":
        inner = decode_type_dto(_object(value.get("value"), "value"))
        if isinstance(inner, NullableTypeDTO):
            raise ValueError("nullable type DTOs may not be nested")
        return NullableTypeDTO(inner)
    raise ValueError(f"unknown logical type kind {kind!r}")


__all__ = ["decode_type_dto", "encode_type_dto"]
