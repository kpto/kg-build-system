"""Bindable struct expression family.

Example:
    ```python
    from kg_build_system.expressions import StructExpression

    assert StructExpression.__name__ == "StructExpression"
    ```
"""
from __future__ import annotations

from typing import Generic, TypeVar

from ...types.internal import Struct, StructType
from .values import ValueExpression


TStruct = TypeVar("TStruct", bound=Struct)


class StructExpression(ValueExpression[TStruct], Generic[TStruct]):
    def __init__(self, model) -> None:
        if not isinstance(model.logical_type, StructType):
            raise TypeError("StructExpression requires a struct logical type")
        super().__init__(model)


__all__ = ["StructExpression"]
