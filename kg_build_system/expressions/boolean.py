"""Typed Boolean expression family."""
from __future__ import annotations

from ..types.interfaces import BOOL
from ._apply import apply_operation
from ._coercion import expression_input
from ._literals import literal
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
        return BoolExpression(
            apply_operation("or", self.model, expression_input(other, BOOL)).model
        )


def any_of(*predicates: BoolExpression) -> BoolExpression:
    """Or the predicates; the empty identity is false."""
    if not predicates:
        return BoolExpression(literal(False, logical_type=BOOL))
    result = predicates[0]
    for predicate in predicates[1:]:
        result = result.or_(predicate)
    return result


def all_of(*predicates: BoolExpression) -> BoolExpression:
    """And the predicates; the empty identity is true."""
    if not predicates:
        return BoolExpression(literal(True, logical_type=BOOL))
    result = predicates[0]
    for predicate in predicates[1:]:
        result = result.and_(predicate)
    return result


__all__ = ["BoolExpression", "all_of", "any_of"]
