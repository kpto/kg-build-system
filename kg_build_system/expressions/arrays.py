"""Bindable array expression family."""
from __future__ import annotations

from typing import Generic, TypeVar

from ..types import Array, ArrayType
from .values import ValueExpression


TItem = TypeVar("TItem")


class ArrayExpression(ValueExpression[Array[TItem]], Generic[TItem]):
    def __init__(self, model) -> None:
        if not isinstance(model.logical_type, ArrayType):
            raise TypeError("ArrayExpression requires an array logical type")
        super().__init__(model)


__all__ = ["ArrayExpression"]
