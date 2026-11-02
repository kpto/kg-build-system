"""JSON codecs for logical types and their IR."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from ..internal.ir import (
    ArrayTypeIR, CustomTypeIR, LogicalTypeIR, NullableTypeIR, StructTypeIR,
    UnitTypeIR,
)
from ..public.models import (
    ArrayType, CustomType, LogicalType, NullableType, StructType, UnitType,
    is_canonical_unit_name,
)


def encode_type(value: LogicalType) -> dict[str, Any]:
    if isinstance(value, UnitType):
        return {"kind": "unit", "name": value.name}
    if isinstance(value, CustomType):
        return {"kind": "custom", "module": value.module, "qualname": value.qualname}
    if isinstance(value, StructType):
        return {"kind": "struct", "module": value.module, "qualname": value.qualname}
    if isinstance(value, ArrayType):
        return {"kind": "array", "item": encode_type(value.item)}
    if isinstance(value, NullableType):
        return {"kind": "nullable", "value": encode_type(value.value)}
    raise TypeError(f"unsupported logical type {value!r}")


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


def decode_type(value: Mapping[str, Any]) -> LogicalType:
    kind = value.get("kind")
    if kind == "unit":
        name = _text(value, "name")
        if not is_canonical_unit_name(name):
            raise ValueError(f"unknown unit logical type {name!r}")
        return UnitType(name)
    if kind == "custom":
        return CustomType(_text(value, "module"), _text(value, "qualname"))
    if kind == "struct":
        return StructType(_text(value, "module"), _text(value, "qualname"))
    if kind == "array":
        return ArrayType(decode_type(_mapping(value, "item")))
    if kind == "nullable":
        inner = decode_type(_mapping(value, "value"))
        if isinstance(inner, NullableType):
            raise ValueError("canonical nullable types may not be nested")
        return NullableType(inner)
    raise ValueError(f"unknown logical type kind {kind!r}")


def encode_type_ir(value: LogicalTypeIR) -> dict[str, Any]:
    if isinstance(value, UnitTypeIR):
        return {"kind": "unit", "name": value.name}
    if isinstance(value, CustomTypeIR):
        return {"kind": "custom", "module": value.module, "qualname": value.qualname}
    if isinstance(value, StructTypeIR):
        return {"kind": "struct", "module": value.module, "qualname": value.qualname}
    if isinstance(value, ArrayTypeIR):
        return {"kind": "array", "item": encode_type_ir(value.item)}
    if isinstance(value, NullableTypeIR):
        return {"kind": "nullable", "value": encode_type_ir(value.value)}
    raise TypeError(f"unsupported logical type IR {value!r}")


def decode_type_ir(value: Mapping[str, Any]) -> LogicalTypeIR:
    kind = value.get("kind")
    if kind == "unit":
        name = _text(value, "name")
        if not is_canonical_unit_name(name):
            raise ValueError(f"unknown unit logical type {name!r}")
        return UnitTypeIR(name)
    if kind == "custom":
        return CustomTypeIR(_text(value, "module"), _text(value, "qualname"))
    if kind == "struct":
        return StructTypeIR(_text(value, "module"), _text(value, "qualname"))
    if kind == "array":
        return ArrayTypeIR(decode_type_ir(_mapping(value, "item")))
    if kind == "nullable":
        inner = decode_type_ir(_mapping(value, "value"))
        if isinstance(inner, NullableTypeIR):
            raise ValueError("canonical nullable types may not be nested")
        return NullableTypeIR(inner)
    raise ValueError(f"unknown logical type kind {kind!r}")


__all__ = [
    "decode_type", "decode_type_ir", "encode_type", "encode_type_ir",
]
