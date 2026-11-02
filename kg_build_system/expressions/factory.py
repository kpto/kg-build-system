"""Construct the most specific bindable expression family for a model."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, overload

from ..types.interfaces import (
    ArrayType, CustomType, LogicalType, NullableType, StructType, UnitType,
)
from ._literals import literal
from ._model import ExpressionNode
from .values import ValueExpression

if TYPE_CHECKING:
    from .boolean import BoolExpression
    from .numeric import FloatExpression, IntExpression
    from .text import StrExpression


def wrap_expression(expression: ExpressionNode) -> ValueExpression[Any]:
    """Wrap canonical data in the most specific runtime authoring family."""
    from .arrays import ArrayExpression
    from .boolean import BoolExpression
    from .custom import CustomDataTypeExpression
    from .nullable import NullableExpression
    from .numeric import FloatExpression, IntExpression
    from .structs import StructExpression
    from .text import StrExpression

    logical_type = expression.logical_type
    if isinstance(logical_type, NullableType):
        inner = logical_type.value
        if isinstance(inner, ArrayType):
            return NullableExpression(expression, ArrayExpression)
        if isinstance(inner, StructType):
            return NullableExpression(expression, StructExpression)
        return NullableExpression(expression, wrap_expression)
    if isinstance(logical_type, ArrayType):
        return ArrayExpression(expression)
    if isinstance(logical_type, StructType):
        return StructExpression(expression)
    if isinstance(logical_type, CustomType):
        return CustomDataTypeExpression(expression)
    if isinstance(logical_type, UnitType):
        factories = {
            "bool": BoolExpression,
            "int": IntExpression,
            "float": FloatExpression,
            "str": StrExpression,
            # Temporal and identifier units carry no typed operations in this
            # vocabulary, so the generic expression is their family.
            "date": ValueExpression,
            "time": ValueExpression,
            "timestamp": ValueExpression,
            "uuid": ValueExpression,
        }
        factory = factories.get(logical_type.name)
        if factory is not None:
            return factory(expression)
    raise TypeError(f"unsupported expression logical type {logical_type!r}")


@overload
def value_expression(value: bool, *, logical_type: None = None) -> "BoolExpression": ...
@overload
def value_expression(value: int, *, logical_type: None = None) -> "IntExpression": ...
@overload
def value_expression(value: float, *, logical_type: None = None) -> "FloatExpression": ...
@overload
def value_expression(value: str, *, logical_type: None = None) -> "StrExpression": ...
@overload
def value_expression(value: Any, *, logical_type: LogicalType | None = None) -> ValueExpression[Any]: ...


def value_expression(
    value: Any, *, logical_type: LogicalType | None = None,
) -> ValueExpression[Any]:
    """Construct a typed authoring expression from a portable literal."""
    return wrap_expression(literal(value, logical_type=logical_type))


__all__ = ["value_expression", "wrap_expression"]
