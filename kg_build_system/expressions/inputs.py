"""Normalize author-facing values into portable expressions."""
from typing import Any

from ..data_types import validate_literal
from .core import Expression, PermittedExpressionValue, ValueRef

type ExpressionInput[T: PermittedExpressionValue] = T | ValueRef[T] | Expression[T]


def to_expression[T: PermittedExpressionValue](value: T | ValueRef[T] | Expression[T]) -> Expression[T]:
    if isinstance(value, Expression):
        return value
    if isinstance(value, ValueRef):
        return Expression("value_ref", (value,), value.type_hint, value.cardinality)
    validate_literal(value)
    return Expression("literal", (value,), type(value))
