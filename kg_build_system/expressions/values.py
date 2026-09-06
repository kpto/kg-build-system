"""Bindable typed calculations backed by expression domain models."""
from __future__ import annotations

from typing import Generic, Self, TypeVar, cast

from ..types import BOOL, LogicalType
from .base import operation
from .models import ExpressionNode, RowSemantics


T_co = TypeVar("T_co", covariant=True)


class NullableAuthoringInput(Generic[T_co]):
    """Typing bridge from internal ``Nullable[T]`` to author-facing ``T | None``."""


class ValueExpression(Generic[T_co]):
    """Bindable calculation backed by one immutable expression model.

    This base deliberately exposes no value-specific operations. Concrete
    expression families add only the operations valid for their logical type.
    """

    __slots__ = ("_model",)

    def __init__(self, model: ExpressionNode) -> None:
        self._model = model

    @property
    def model(self) -> ExpressionNode:
        return self._model

    @property
    def logical_type(self) -> LogicalType:
        return self._model.logical_type

    def keep_if(self, predicate: ValueExpression[bool]) -> Self:
        """Keep the row only where a Boolean predicate holds, dropping the rest.

        The value passes through unchanged and keeps its family; the predicate
        records a local filter row effect, so — like ``where_present`` — a
        projection or binding owns it and it cannot change a sibling product.
        """
        from .factory import wrap_expression

        predicate_model = predicate.model
        if predicate_model.logical_type != BOOL:
            raise TypeError("keep_if requires a Boolean predicate")
        result = operation(
            "keep_if",
            self.model,
            predicate_model,
            logical_type=self.logical_type,
            row_semantics=RowSemantics("filter"),
        )
        return cast(Self, wrap_expression(result))

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._model!r})"


__all__ = ["NullableAuthoringInput", "ValueExpression"]
