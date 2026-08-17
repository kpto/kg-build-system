"""Typed numeric expression families."""
from __future__ import annotations

from typing import Generic, TypeVar

from ..types import FLOAT, INT
from ._coercion import expression_input
from .base import operation
from .values import ValueExpression


TNumber = TypeVar("TNumber", int, float)


class NumberExpression(ValueExpression[TNumber], Generic[TNumber]):
    """Shared numeric operations with a family-preserving result."""

    def _binary(self, operator: str, other: TNumber | ValueExpression[TNumber]):
        right = expression_input(other, self.logical_type)
        return type(self)(
            operation(operator, self.model, right, logical_type=self.logical_type)
        )

    def add(self, other: TNumber | ValueExpression[TNumber]) -> "NumberExpression[TNumber]":
        return self._binary("add", other)

    def sub(self, other: TNumber | ValueExpression[TNumber]) -> "NumberExpression[TNumber]":
        return self._binary("subtract", other)


class IntExpression(NumberExpression[int]):
    def __init__(self, expression):
        if expression.logical_type != INT:
            raise TypeError("IntExpression requires the int logical type")
        super().__init__(expression)

    def add(self, other: int | ValueExpression[int]) -> "IntExpression":
        return self._binary("add", other)

    def sub(self, other: int | ValueExpression[int]) -> "IntExpression":
        return self._binary("subtract", other)


class FloatExpression(NumberExpression[float]):
    def __init__(self, expression):
        if expression.logical_type != FLOAT:
            raise TypeError("FloatExpression requires the float logical type")
        super().__init__(expression)

    def add(self, other: float | ValueExpression[float]) -> "FloatExpression":
        return self._binary("add", other)

    def sub(self, other: float | ValueExpression[float]) -> "FloatExpression":
        return self._binary("subtract", other)


__all__ = ["FloatExpression", "IntExpression", "NumberExpression"]
