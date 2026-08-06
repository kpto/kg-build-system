"""Normalize author-facing values into portable expressions."""
from typing import Any, TypeVar, overload

from ..data_types import validate_literal
from .core import Expression, ValueRef

type ExpressionInput[T] = T | ValueRef[T] | Expression[T]
T = TypeVar("T")


@overload
def to_expression(value: ValueRef[T] | Expression[T]) -> Expression[T]: ...

@overload
def to_expression(value: T) -> Expression[T]: ...

def to_expression(value: Any) -> Expression[Any]:
    if isinstance(value, Expression):
        return value
    if isinstance(value, ValueRef):
        return Expression("value_ref", (value,), value.type_hint, value.cardinality)
    validate_literal(value)
    return Expression("literal", (value,), type(value))
