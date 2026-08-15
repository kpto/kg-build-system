"""Validated literal construction for the canonical expression IR."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .._frozen_json import freeze_json
from ..types import (
    ArrayType, BOOL, FLOAT, INT, LogicalType, NullableType, STR, StructType, CustomType,
)
from .models import LiteralExpression


def _infer(value: Any) -> LogicalType:
    if type(value) is bool:
        return BOOL
    if type(value) is int:
        return INT
    if type(value) is float:
        return FLOAT
    if type(value) is str:
        return STR
    if value is None:
        raise TypeError("a null literal requires an explicit nullable logical type")
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        if not value:
            raise TypeError("an empty array literal requires an explicit logical type")
        item_types = tuple(_infer(item) for item in value if item is not None)
        if not item_types:
            raise TypeError("an all-null array literal requires an explicit logical type")
        first = item_types[0]
        if any(item != first for item in item_types[1:]):
            raise TypeError("array literal items must have one logical type")
        item_type: LogicalType = (
            first if isinstance(first, NullableType) else NullableType(first)
        ) if any(item is None for item in value) else first
        return ArrayType(item_type)
    raise TypeError(f"unsupported expression literal {value!r}")


def _validate(value: Any, logical_type: LogicalType, *, context: str = "literal") -> None:
    if isinstance(logical_type, NullableType):
        if value is None:
            return
        _validate(value, logical_type.value, context=context)
        return
    if isinstance(logical_type, ArrayType):
        if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
            raise TypeError(f"{context} must be an array")
        for index, item in enumerate(value):
            _validate(item, logical_type.item, context=f"{context}[{index}]")
        return
    if isinstance(logical_type, (StructType, CustomType)):
        raise TypeError(f"{context} cannot embed struct or custom-type values")
    expected = {"bool": bool, "int": int, "float": float, "str": str}[logical_type.name]
    if type(value) is not expected:
        raise TypeError(f"{context} must be {logical_type.name}, not {type(value).__name__}")


def literal(value: Any, *, logical_type: LogicalType | None = None) -> LiteralExpression:
    resolved_type = logical_type or _infer(value)
    _validate(value, resolved_type)
    return LiteralExpression(value=freeze_json(value), logical_type=resolved_type)


__all__ = ["literal"]
