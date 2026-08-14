"""Typed Boolean expression family."""
from __future__ import annotations

from ..types import BOOL
from ._coercion import expression_input
from .base import operation
from .values import ValueExpression


class BoolValueExpression(ValueExpression[bool]):
    def __init__(self, expression):
        if expression.logical_type != BOOL:
            raise TypeError("BoolValueExpression requires the bool logical type")
        super().__init__(expression)

    def not_(self) -> "BoolValueExpression":
        return BoolValueExpression(operation("not", self.expression, logical_type=BOOL))

    def and_(self, other: bool | ValueExpression[bool]) -> "BoolValueExpression":
        return BoolValueExpression(
            operation("and", self.expression, expression_input(other, BOOL), logical_type=BOOL)
        )

    def or_(self, other: bool | ValueExpression[bool]) -> "BoolValueExpression":
        return BoolValueExpression(
            operation("or", self.expression, expression_input(other, BOOL), logical_type=BOOL)
        )


__all__ = ["BoolValueExpression"]
