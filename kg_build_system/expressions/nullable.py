"""Null-aware typed expression family."""
from __future__ import annotations

from collections.abc import Callable
from typing import Generic, TypeVar

from ..types import Nullable, NullableType
from ._coercion import expression_input
from .base import operation
from .ir import ExpressionNode, RowSemantics
from .values import ValueExpression


TData = TypeVar("TData")
TNonNullExpr = TypeVar("TNonNullExpr", bound=ValueExpression)


class NullableValueExpression(
    ValueExpression[Nullable[TData]], Generic[TData, TNonNullExpr]
):
    """A nullable value exposing only explicit null-handling operations."""

    __slots__ = ("_non_null_factory",)

    def __init__(
        self,
        expression: ExpressionNode,
        non_null_factory: Callable[[ExpressionNode], TNonNullExpr],
    ) -> None:
        if not isinstance(expression.logical_type, NullableType):
            raise TypeError("NullableValueExpression requires a nullable logical type")
        super().__init__(expression)
        self._non_null_factory = non_null_factory

    @property
    def non_null_logical_type(self):
        logical_type = self.logical_type
        assert isinstance(logical_type, NullableType)
        return logical_type.value

    def or_else(
        self, value: TData | ValueExpression[TData]
    ) -> TNonNullExpr:
        fallback = expression_input(value, self.non_null_logical_type)
        return self._non_null_factory(
            operation(
                "coalesce",
                self.expression,
                fallback,
                logical_type=self.non_null_logical_type,
            )
        )

    def when_present(self) -> TNonNullExpr:
        """Suppress the containing mapping when this value is null."""
        return self._non_null_factory(
            operation(
                "when_present",
                self.expression,
                logical_type=self.non_null_logical_type,
                row_semantics=RowSemantics("filter"),
            )
        )


__all__ = ["NullableValueExpression"]
