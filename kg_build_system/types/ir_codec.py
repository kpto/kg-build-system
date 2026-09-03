"""Stable JSON codec for compilation logical-type IR."""
from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .ir import (
    ArrayTypeIR, CustomTypeIR, LogicalTypeIR, NullableTypeIR, StructTypeIR,
    UnitTypeIR,
)
from .models import is_canonical_unit_name


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


def _text(value: Mapping[str, Any], key: str) -> str:
    result = value.get(key)
    if not isinstance(result, str) or not result:
        raise ValueError(f"logical type field {key!r} must be a non-empty string")
    return result


def _object(value: Any, key: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(f"logical type field {key!r} must be an object")
    return value


def decode_type_ir(value: Mapping[str, Any]) -> LogicalTypeIR:
    kind = value.get("kind")
    if kind == "unit":
        name = _text(value, "name")
        if not is_canonical_unit_name(name):
            raise ValueError(f"unknown unit type {name!r}")
        return UnitTypeIR(name)
    if kind == "custom":
        return CustomTypeIR(_text(value, "module"), _text(value, "qualname"))
    if kind == "struct":
        return StructTypeIR(_text(value, "module"), _text(value, "qualname"))
    if kind == "array":
        return ArrayTypeIR(decode_type_ir(_object(value.get("item"), "item")))
    if kind == "nullable":
        inner = decode_type_ir(_object(value.get("value"), "value"))
        if isinstance(inner, NullableTypeIR):
            raise ValueError("nullable type IRs may not be nested")
        return NullableTypeIR(inner)
    raise ValueError(f"unknown logical type kind {kind!r}")


__all__ = ["decode_type_ir", "encode_type_ir"]
