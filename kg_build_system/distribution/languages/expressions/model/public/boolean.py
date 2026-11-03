"""Typed Boolean expressions and predicate combinators.

Example:
    ```python
    from kg_build_system import all_of, value_expression

    both = all_of(value_expression(True), value_expression(False))
    assert both.model.operator == "and"
    ```
"""
from __future__ import annotations

from kg_build_system.kernel.model.public.types import BOOL
from .values import ValueExpression


class BoolExpression(ValueExpression[bool]):
    def __init__(self, expression):
        if expression.logical_type != BOOL:
            raise TypeError("BoolExpression requires the bool logical type")
        super().__init__(expression)

    def not_(self) -> "BoolExpression":
        """Negate this Boolean expression.

        Example:
            ```python
            from kg_build_system import value_expression

            assert value_expression(True).not_().model.operator == "not"
            ```
        """
        from ...service._private.apply import apply_operation

        return BoolExpression(apply_operation("not", self.model).model)

    def and_(self, other: bool | ValueExpression[bool]) -> "BoolExpression":
        """Combine this predicate with another using logical and.

        Example:
            ```python
            from kg_build_system import value_expression

            predicate = value_expression(True).and_(value_expression(False))
            assert predicate.model.operator == "and"
            ```
        """
        from ...service._private.apply import apply_operation
        from ...service._private.coercion import expression_input

        return BoolExpression(
            apply_operation("and", self.model, expression_input(other, BOOL)).model
        )

    def or_(self, other: bool | ValueExpression[bool]) -> "BoolExpression":
        """Combine this predicate with another using logical or.

        Example:
            ```python
            from kg_build_system import value_expression

            predicate = value_expression(False).or_(value_expression(True))
            assert predicate.model.operator == "or"
            ```
        """
        from ...service._private.apply import apply_operation
        from ...service._private.coercion import expression_input

        return BoolExpression(
            apply_operation("or", self.model, expression_input(other, BOOL)).model
        )


__all__ = ["BoolExpression"]
