"""Normalize author-facing values into portable expressions."""
from typing import Any

from .core import Expression, ValueRef

type ExpressionInput[T] = T | ValueRef[T] | Expression[T]


def to_expression(value: Any) -> Expression[Any]:
    if isinstance(value, Expression):
        return value
    if isinstance(value, ValueRef):
        return Expression("value_ref", (value,), value.type_hint, value.cardinality)
    return Expression("literal", (value,), type(value))
