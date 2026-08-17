"""Typed text expression family."""
from __future__ import annotations

from ..types import STR
from ._coercion import expression_input
from .base import operation
from .values import ValueExpression


class StrExpression(ValueExpression[str]):
    def __init__(self, expression):
        if expression.logical_type != STR:
            raise TypeError("StrExpression requires the str logical type")
        super().__init__(expression)

    def prepend(self, value: str | ValueExpression[str]) -> "StrExpression":
        return StrExpression(
            operation("concat", expression_input(value, STR), self.model, logical_type=STR)
        )

    def append(self, value: str | ValueExpression[str]) -> "StrExpression":
        return StrExpression(
            operation("concat", self.model, expression_input(value, STR), logical_type=STR)
        )


__all__ = ["StrExpression"]
