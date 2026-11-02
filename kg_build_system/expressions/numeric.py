"""Typed numeric expression families."""
from __future__ import annotations

from typing import Generic, TypeVar

from ..types.interfaces import FLOAT, INT
from ._apply import apply_operation
from ._coercion import expression_input
from .values import ValueExpression


TNumber = TypeVar("TNumber", int, float)


class NumberExpression(ValueExpression[TNumber], Generic[TNumber]):
    """Shared numeric operations with a family-preserving result."""

    def _binary(self, operator: str, other: TNumber | ValueExpression[TNumber]):
        right = expression_input(other, self.logical_type)
        return type(self)(apply_operation(operator, self.model, right).model)

    def add(self, other: TNumber | ValueExpression[TNumber]) -> "NumberExpression[TNumber]":
        """Add another number of the same logical type.

        Example:
            ```python
            from kg_build_system import value_expression
            from kg_build_system.expressions import NumberExpression

            number = NumberExpression(value_expression(1).model)
            assert number.add(2).model.operator == "add"
            ```
        """
        return self._binary("add", other)

    def sub(self, other: TNumber | ValueExpression[TNumber]) -> "NumberExpression[TNumber]":
        """Subtract another number of the same logical type.

        Example:
            ```python
            from kg_build_system import value_expression
            from kg_build_system.expressions import NumberExpression

            number = NumberExpression(value_expression(1).model)
            assert number.sub(2).model.operator == "subtract"
            ```
        """
        return self._binary("subtract", other)


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
        return self._binary("add", other)

    def sub(self, other: int | ValueExpression[int]) -> "IntExpression":
        """Subtract another integer or integer expression.

        Example:
            ```python
            from kg_build_system import value_expression

            assert value_expression(1).sub(2).model.operator == "subtract"
            ```
        """
        return self._binary("subtract", other)


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
        return self._binary("add", other)

    def sub(self, other: float | ValueExpression[float]) -> "FloatExpression":
        """Subtract another float or float expression.

        Example:
            ```python
            from kg_build_system import value_expression

            assert value_expression(1.5).sub(0.5).model.operator == "subtract"
            ```
        """
        return self._binary("subtract", other)


__all__ = ["FloatExpression", "IntExpression", "NumberExpression"]
