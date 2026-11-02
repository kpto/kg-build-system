"""Validated literal construction for the canonical expression model."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .._frozen_json import FrozenJson, freeze_json
from ..types.interfaces import (
    BOOL, DATE, FLOAT, INT, STR, TIME, TIMESTAMP, UUID, ArrayType, CustomType,
    Date, LogicalType, NullableType, StructType, TEXT_CANONICAL_UNIT_NAMES,
    Time, Timestamp, UnitType, Uuid, canonical_value_text,
)
from ._model import LiteralExpression


# A literal is accepted as exactly one Python class: the representative type of
# the unit. Identity is the test, so Timestamp stays distinct from Date and bool
# from int.
_UNITS_BY_CLASS: dict[type[Any], UnitType] = {
    bool: BOOL,
    int: INT,
    float: FLOAT,
    str: STR,
    Date: DATE,
    Time: TIME,
    Timestamp: TIMESTAMP,
    Uuid: UUID,
}
_CLASSES_BY_UNIT_NAME: dict[str, type[Any]] = {
    unit.name: value for value, unit in _UNITS_BY_CLASS.items()
}


def _infer(value: Any) -> LogicalType:
    unit = _UNITS_BY_CLASS.get(type(value))
    if unit is not None:
        return unit
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
        first = first.value if isinstance(first, NullableType) else first
        item_type: LogicalType = (
            NullableType(first) if any(item is None for item in value) else first
        )
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
    expected = _CLASSES_BY_UNIT_NAME.get(logical_type.name)
    if expected is None:
        raise TypeError(f"{context} has unsupported unit logical type {logical_type.name!r}")
    if type(value) is not expected:
        raise TypeError(f"{context} must be {logical_type.name}, not {type(value).__name__}")


def _freeze(value: Any, logical_type: LogicalType) -> FrozenJson:
    """Freeze a validated literal, storing a text-canonical unit as canonical text."""
    if isinstance(logical_type, NullableType):
        return None if value is None else _freeze(value, logical_type.value)
    if isinstance(logical_type, UnitType):
        if logical_type.name in TEXT_CANONICAL_UNIT_NAMES:
            return canonical_value_text(value)
        return freeze_json(value)
    if isinstance(logical_type, ArrayType):
        return tuple(_freeze(item, logical_type.item) for item in value)
    return freeze_json(value)


def literal(value: Any, *, logical_type: LogicalType | None = None) -> LiteralExpression:
    """Build a literal expression, inferring the type when it is unambiguous."""
    resolved_type = logical_type or _infer(value)
    _validate(value, resolved_type)
    return LiteralExpression(value=_freeze(value, resolved_type), logical_type=resolved_type)


__all__ = ["literal"]
