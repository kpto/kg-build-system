"""Bindable typed calculations backed by expression domain models."""
from __future__ import annotations

from typing import Generic, TypeVar

from ..types import LogicalType
from .models import ExpressionNode


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

    def __repr__(self) -> str:
        return f"{type(self).__name__}({self._model!r})"


__all__ = ["NullableAuthoringInput", "ValueExpression"]
