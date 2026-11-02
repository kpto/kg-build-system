"""Runtime dispatch for constructing typed authoring expressions."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any, overload

from ...types.internal import (
    ArrayType, CustomType, LogicalType, NullableType, StructType, UnitType,
)
from ..internal.model import ExpressionNode
from .literals import literal as _literal

if TYPE_CHECKING:
    from ..public.boolean import BoolExpression
    from ..public.numeric import FloatExpression, IntExpression
    from ..public.text import StrExpression
    from ..public.values import ValueExpression


def wrap_expression(expression: ExpressionNode) -> ValueExpression[Any]:
    """Wrap canonical data in the most specific runtime authoring family."""
    from ..public.arrays import ArrayExpression
    from ..public.boolean import BoolExpression
    from ..public.custom import CustomDataTypeExpression
    from ..public.nullable import NullableExpression
    from ..public.numeric import FloatExpression, IntExpression
    from ..public.structs import StructExpression
    from ..public.text import StrExpression
    from ..public.values import ValueExpression

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
    """Construct the most specific typed expression for a portable literal."""
    return wrap_expression(_literal(value, logical_type=logical_type))


__all__ = ["value_expression", "wrap_expression"]
