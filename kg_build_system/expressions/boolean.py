"""Typed Boolean expression family."""
from __future__ import annotations

from ..types import BOOL
from ._coercion import expression_input
from .base import operation
from .values import ValueExpression


class BoolExpression(ValueExpression[bool]):
    def __init__(self, expression):
        if expression.logical_type != BOOL:
            raise TypeError("BoolExpression requires the bool logical type")
        super().__init__(expression)

    def not_(self) -> "BoolExpression":
        return BoolExpression(operation("not", self.model, logical_type=BOOL))

    def and_(self, other: bool | ValueExpression[bool]) -> "BoolExpression":
        return BoolExpression(
            operation("and", self.model, expression_input(other, BOOL), logical_type=BOOL)
        )

    def or_(self, other: bool | ValueExpression[bool]) -> "BoolExpression":
        return BoolExpression(
            operation("or", self.model, expression_input(other, BOOL), logical_type=BOOL)
        )


__all__ = ["BoolExpression"]
