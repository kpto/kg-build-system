"""Bindable nullable expression family.

Null policy belongs to selections. Nullable expressions are terminal
calculations and deliberately expose no narrowing operations.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar

from ..types.interfaces import Nullable, NullableType
from .models import ExpressionNode
from .values import NullableAuthoringInput, ValueExpression


TData = TypeVar("TData")
TNonNullExpr = TypeVar("TNonNullExpr", bound=ValueExpression)


class NullableExpression(
    ValueExpression[Nullable[TData]], NullableAuthoringInput[TData | None],
    Generic[TData, TNonNullExpr]
):
    """Bindable nullable calculation with a known non-null expression family."""

    __slots__ = ("_non_null_factory",)

    def __init__(
        self,
        model: ExpressionNode,
        non_null_factory: Callable[[ExpressionNode], TNonNullExpr],
    ) -> None:
        if not isinstance(model.logical_type, NullableType):
            raise TypeError("NullableExpression requires a nullable logical type")
        super().__init__(model)
        self._non_null_factory = non_null_factory

    @property
    def non_null_logical_type(self):
        logical_type = self.logical_type
        assert isinstance(logical_type, NullableType)
        return logical_type.value

    def _non_null(self, model: ExpressionNode) -> TNonNullExpr:
        return self._non_null_factory(model)


__all__ = ["NullableExpression"]
