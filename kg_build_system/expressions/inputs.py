"""Normalize author-facing values into portable expressions."""
from typing import Any

from .core import Expression, FieldPath

type ExpressionInput[T] = T | FieldPath[T] | Expression[T]


def to_expression(value: Any) -> Expression[Any]:
    if isinstance(value, Expression):
        return value
    if isinstance(value, FieldPath):
        return Expression("field", (value,), value.type_hint, value.cardinality)
    return Expression("literal", (value,), type(value))
