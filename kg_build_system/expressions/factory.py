"""Construct the most specific bindable expression family for a model."""
from __future__ import annotations

from typing import Any

from ..types import (
    ArrayType, CustomType, LogicalType, NullableType, StructType, UnitType,
)
from .arrays import ArrayExpression
from .boolean import BoolExpression
from .custom import CustomDataTypeExpression
from .models import ExpressionNode
from .literals import literal
from .nullable import NullableExpression
from .numeric import FloatExpression, IntExpression
from .structs import StructExpression
from .text import StrExpression
from .values import ValueExpression


def wrap_expression(expression: ExpressionNode) -> ValueExpression[Any]:
    """Wrap canonical IR in the most specific runtime authoring family."""
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
            # The temporal and identifier units carry no operations in this
            # vocabulary, so the generic expression is their most specific family.
            "date": ValueExpression,
            "time": ValueExpression,
            "timestamp": ValueExpression,
            "uuid": ValueExpression,
        }
        factory = factories.get(logical_type.name)
        if factory is not None:
            return factory(expression)
    raise TypeError(f"unsupported expression logical type {logical_type!r}")


def value_expression(
    value: Any, *, logical_type: LogicalType | None = None,
) -> ValueExpression[Any]:
    """Construct a typed authoring expression from a portable literal."""
    return wrap_expression(literal(value, logical_type=logical_type))


__all__ = ["value_expression", "wrap_expression"]
