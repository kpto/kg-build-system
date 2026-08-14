"""Runtime selection of the most specific typed expression wrapper."""
from __future__ import annotations

from typing import Any

from ..types import ArrayType, CustomType, NullableType, StructType, UnitType
from .arrays import ArrayNullableValueExpression, ArrayValueExpression
from .boolean import BoolValueExpression
from .custom import CustomDataTypeValueExpression
from .ir import ExpressionNode
from .literals import literal
from .nullable import NullableValueExpression
from .numeric import FloatValueExpression, IntValueExpression
from .structs import StructNullableValueExpression, StructValueExpression
from .text import StrValueExpression
from .values import ValueExpression


def wrap_expression(expression: ExpressionNode) -> ValueExpression[Any]:
    """Wrap canonical IR in the most specific runtime authoring family."""
    logical_type = expression.logical_type
    if isinstance(logical_type, NullableType):
        inner = logical_type.value
        if isinstance(inner, ArrayType):
            return ArrayNullableValueExpression(expression)
        if isinstance(inner, StructType):
            return StructNullableValueExpression(expression)
        return NullableValueExpression(expression, wrap_expression)
    if isinstance(logical_type, ArrayType):
        return ArrayValueExpression(expression)
    if isinstance(logical_type, StructType):
        return StructValueExpression(expression)
    if isinstance(logical_type, CustomType):
        return CustomDataTypeValueExpression(expression)
    if isinstance(logical_type, UnitType):
        factories = {
            "bool": BoolValueExpression,
            "int": IntValueExpression,
            "float": FloatValueExpression,
            "str": StrValueExpression,
        }
        return factories[logical_type.name](expression)
    raise TypeError(f"unsupported expression logical type {logical_type!r}")


def value_expression(value: Any, *, logical_type=None) -> ValueExpression[Any]:
    """Construct a typed authoring expression from a portable literal."""
    return wrap_expression(literal(value, logical_type=logical_type))


__all__ = ["value_expression", "wrap_expression"]
