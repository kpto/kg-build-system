"""Typed numeric expression families.

Example:
    ```python
    from kg_build_system import value_expression

    assert value_expression(1).add(2).model.operator == "add"
    ```
"""
from __future__ import annotations

from typing import Generic, TypeVar

from kg_build_system.kernel.model.public.types import FLOAT, INT
from .values import ValueExpression


TNumber = TypeVar("TNumber", int, float)


class NumberExpression(ValueExpression[TNumber], Generic[TNumber]):
    """Shared numeric operations with a family-preserving result."""

    def add(self, other: TNumber | ValueExpression[TNumber]) -> "NumberExpression[TNumber]":
        """Add another number of the same logical type.

        Example:
            ```python
            from kg_build_system import value_expression
            from kg_build_system.distribution.languages.expressions.model.public import NumberExpression

            number = NumberExpression(value_expression(1).model)
            assert number.add(2).model.operator == "add"
            ```
        """
        from ...service._private.numeric import binary

        return binary(self, "add", other)

    def sub(self, other: TNumber | ValueExpression[TNumber]) -> "NumberExpression[TNumber]":
        """Subtract another number of the same logical type.

        Example:
            ```python
            from kg_build_system import value_expression
            from kg_build_system.distribution.languages.expressions.model.public import NumberExpression

            number = NumberExpression(value_expression(1).model)
            assert number.sub(2).model.operator == "subtract"
            ```
        """
        from ...service._private.numeric import binary

        return binary(self, "subtract", other)


class IntExpression(NumberExpression[int]):
    def __init__(self, expression):
        if expression.logical_type != INT:
            raise TypeError("IntExpression requires the int logical type")
        super().__init__(expression)

    def add(self, other: int | ValueExpression[int]) -> "IntExpression":
        """Add another integer or integer expression.

        Example:
            ```python
            from kg_build_system import value_expression

            assert value_expression(1).add(2).model.operator == "add"
            ```
        """
        from ...service._private.numeric import binary

        return binary(self, "add", other)

    def sub(self, other: int | ValueExpression[int]) -> "IntExpression":
        """Subtract another integer or integer expression.

        Example:
            ```python
            from kg_build_system import value_expression

            assert value_expression(1).sub(2).model.operator == "subtract"
            ```
        """
        from ...service._private.numeric import binary

        return binary(self, "subtract", other)


class FloatExpression(NumberExpression[float]):
    def __init__(self, expression):
        if expression.logical_type != FLOAT:
            raise TypeError("FloatExpression requires the float logical type")
        super().__init__(expression)

    def add(self, other: float | ValueExpression[float]) -> "FloatExpression":
        """Add another float or float expression.

        Example:
            ```python
            from kg_build_system import value_expression

            assert value_expression(1.5).add(0.5).model.operator == "add"
            ```
        """
        from ...service._private.numeric import binary

        return binary(self, "add", other)

    def sub(self, other: float | ValueExpression[float]) -> "FloatExpression":
        """Subtract another float or float expression.

        Example:
            ```python
            from kg_build_system import value_expression

            assert value_expression(1.5).sub(0.5).model.operator == "subtract"
            ```
        """
        from ...service._private.numeric import binary

        return binary(self, "subtract", other)


__all__ = ["FloatExpression", "IntExpression", "NumberExpression"]
