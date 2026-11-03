"""Typed expressions for application-defined scalar logical types.

Example:
    ```python
    from kg_build_system.distribution.languages.expressions.model.public import CustomDataTypeExpression

    assert CustomDataTypeExpression.__name__ == "CustomDataTypeExpression"
    ```
"""
from __future__ import annotations

from typing import Generic, TypeVar

from kg_build_system.kernel.model.public.types import CustomDataType, CustomType
from .values import ValueExpression


TCustom = TypeVar("TCustom", bound=CustomDataType)


class CustomDataTypeExpression(ValueExpression[TCustom], Generic[TCustom]):
    def __init__(self, expression):
        if not isinstance(expression.logical_type, CustomType):
            raise TypeError("CustomDataTypeExpression requires a custom logical type")
        super().__init__(expression)


__all__ = ["CustomDataTypeExpression"]
