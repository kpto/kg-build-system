"""Typed text expression family."""
from __future__ import annotations

from ..types import STR
from ._coercion import expression_input
from .base import operation
from .values import ValueExpression


class StrValueExpression(ValueExpression[str]):
    def __init__(self, expression):
        if expression.logical_type != STR:
            raise TypeError("StrValueExpression requires the str logical type")
        super().__init__(expression)

    def prepend(self, value: str | ValueExpression[str]) -> "StrValueExpression":
        return StrValueExpression(
            operation("concat", expression_input(value, STR), self.expression, logical_type=STR)
        )

    def append(self, value: str | ValueExpression[str]) -> "StrValueExpression":
        return StrValueExpression(
            operation("concat", self.expression, expression_input(value, STR), logical_type=STR)
        )


__all__ = ["StrValueExpression"]
