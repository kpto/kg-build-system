"""Bindable struct expression family."""
from __future__ import annotations

from typing import Generic, TypeVar

from ..types import Struct, StructType
from .values import ValueExpression


TStruct = TypeVar("TStruct", bound=Struct)


class StructExpression(ValueExpression[TStruct], Generic[TStruct]):
    def __init__(self, model) -> None:
        if not isinstance(model.logical_type, StructType):
            raise TypeError("StructExpression requires a struct logical type")
        super().__init__(model)


__all__ = ["StructExpression"]
