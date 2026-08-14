"""Typed authoring wrappers around the canonical expression IR."""
from __future__ import annotations

from typing import Generic, TypeVar

from ..types import LogicalType
from .ir import ExpressionNode


T_co = TypeVar("T_co", covariant=True)


class ValueExpression(Generic[T_co]):
    """Bindable typed value backed by one canonical expression node.

    This base deliberately exposes no value-specific operations. Concrete
    expression families add only the operations valid for their logical type.
    """

    __slots__ = ("_expression",)

    def __init__(self, expression: ExpressionNode) -> None:
        self._expression = expression

    @property
    def expression(self) -> ExpressionNode:
        return self._expression

    @property
    def logical_type(self) -> LogicalType:
        return self._expression.logical_type

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._expression!r})"


__all__ = ["ValueExpression"]
