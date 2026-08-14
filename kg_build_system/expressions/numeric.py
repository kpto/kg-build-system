"""Typed numeric expression families."""
from __future__ import annotations

from typing import Generic, TypeVar

from ..types import FLOAT, INT
from ._coercion import expression_input
from .base import operation
from .values import AuthoringValueExpression, ValueExpression


TNumber = TypeVar("TNumber", int, float)


class NumberValueExpression(
    ValueExpression[TNumber], AuthoringValueExpression[TNumber], Generic[TNumber]
):
    """Shared numeric operations with a family-preserving result."""

    def _binary(self, operator: str, other: TNumber | ValueExpression[TNumber]):
        right = expression_input(other, self.logical_type)
        return type(self)(
            operation(operator, self.expression, right, logical_type=self.logical_type)
        )

    def add(self, other: TNumber | ValueExpression[TNumber]) -> "NumberValueExpression[TNumber]":
        return self._binary("add", other)

    def sub(self, other: TNumber | ValueExpression[TNumber]) -> "NumberValueExpression[TNumber]":
        return self._binary("subtract", other)


class IntValueExpression(NumberValueExpression[int]):
    def __init__(self, expression):
        if expression.logical_type != INT:
            raise TypeError("IntValueExpression requires the int logical type")
        super().__init__(expression)

    def add(self, other: int | ValueExpression[int]) -> "IntValueExpression":
        return self._binary("add", other)

    def sub(self, other: int | ValueExpression[int]) -> "IntValueExpression":
        return self._binary("subtract", other)


class FloatValueExpression(NumberValueExpression[float]):
    def __init__(self, expression):
        if expression.logical_type != FLOAT:
            raise TypeError("FloatValueExpression requires the float logical type")
        super().__init__(expression)

    def add(self, other: float | ValueExpression[float]) -> "FloatValueExpression":
        return self._binary("add", other)

    def sub(self, other: float | ValueExpression[float]) -> "FloatValueExpression":
        return self._binary("subtract", other)


__all__ = ["FloatValueExpression", "IntValueExpression", "NumberValueExpression"]
