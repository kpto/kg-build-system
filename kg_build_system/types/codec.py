"""Stable JSON-compatible encoding for canonical logical types."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .models import (
    ArrayType, CustomType, LogicalType, NullableType, StructType, UnitType, is_canonical_unit_name,
)


def encode_type(logical_type: LogicalType) -> dict[str, Any]:
    if isinstance(logical_type, UnitType):
        return {"kind": "unit", "name": logical_type.name}
    if isinstance(logical_type, CustomType):
        return {"kind": "custom", "module": logical_type.module, "qualname": logical_type.qualname}
    if isinstance(logical_type, StructType):
        return {"kind": "struct", "module": logical_type.module, "qualname": logical_type.qualname}
    if isinstance(logical_type, ArrayType):
        return {"kind": "array", "item": encode_type(logical_type.item)}
    if isinstance(logical_type, NullableType):
        return {"kind": "nullable", "value": encode_type(logical_type.value)}
    raise TypeError(f"unsupported canonical logical type: {logical_type!r}")


def _text(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"logical type field {key!r} must be a non-empty string")
    return result


def _mapping(value: Mapping[str, Any], key: str) -> Mapping[str, Any]:
    result = value.get(key)
    if not isinstance(result, Mapping):
        raise ValueError(f"logical type field {key!r} must be an object")
    return result


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


__all__ = ["decode_type", "encode_type"]
