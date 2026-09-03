"""Validated literal construction for the canonical expression IR."""
from __future__ import annotations

from collections.abc import Sequence
from typing import Any

from .._frozen_json import FrozenJson, freeze_json
from ..types import (
    ArrayType, CustomType, LogicalType, NullableType, StructType, TEXT_CANONICAL_UNIT_NAMES,
    UNIT_BY_REPRESENTATIVE_CLASS, Date, Time, Timestamp, UnitType, Uuid, canonical_value_text,
)
from .models import LiteralExpression


# A literal is accepted as exactly one Python class: the representative type of the
# unit, which is an alias of the value class itself. Identity is the test, so
# Timestamp stays distinct from its Date supertype and bool from int. This is the
# normalization map itself, not a restatement of it.
_UNITS_BY_CLASS = UNIT_BY_REPRESENTATIVE_CLASS
_CLASSES_BY_UNIT_NAME: dict[str, type[Any]] = {
    unit.name: value for value, unit in _UNITS_BY_CLASS.items()
}


def _canonical_text(value: Date | Time | Timestamp | Uuid) -> str:
    """The one text form a literal of a text-canonical unit is frozen as.

    ``_validate`` has already pinned the exact class the unit admits and ``_freeze``
    has already rejected every unit with no text form, so this only delegates.
    """
    return canonical_value_text(value)


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
    expected = _CLASSES_BY_UNIT_NAME.get(logical_type.name)
    if expected is None:
        raise TypeError(f"{context} has unsupported unit logical type {logical_type.name!r}")
    if type(value) is not expected:
        raise TypeError(f"{context} must be {logical_type.name}, not {type(value).__name__}")


def _freeze(value: Any, logical_type: LogicalType) -> FrozenJson:
    """Freeze a validated literal, storing a text-canonical unit as its canonical text."""
    if isinstance(logical_type, NullableType):
        return None if value is None else _freeze(value, logical_type.value)
    if isinstance(logical_type, UnitType):
        if logical_type.name in TEXT_CANONICAL_UNIT_NAMES:
            return _canonical_text(value)
        return freeze_json(value)
    if isinstance(logical_type, ArrayType):
        return tuple(_freeze(item, logical_type.item) for item in value)
    return freeze_json(value)


def literal(value: Any, *, logical_type: LogicalType | None = None) -> LiteralExpression:
    resolved_type = logical_type or _infer(value)
    _validate(value, resolved_type)
    return LiteralExpression(value=_freeze(value, resolved_type), logical_type=resolved_type)


__all__ = ["literal"]
