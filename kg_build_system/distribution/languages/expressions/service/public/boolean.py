"""Predicate combinators over the Boolean expression family."""
from __future__ import annotations

from ...model.public.boolean import BoolExpression
from ..internal.boolean import all_of as all_of_impl
from ..internal.boolean import any_of as any_of_impl


def all_of(*predicates: BoolExpression) -> BoolExpression:
    """Combine predicates with logical and; the empty identity is true.

    Example:
        ```python
        from kg_build_system import all_of, value_expression

        both = all_of(value_expression(True), value_expression(False))
        assert both.model.operator == "and"
        ```
    """
    return all_of_impl(*predicates)


def any_of(*predicates: BoolExpression) -> BoolExpression:
    """Combine predicates with logical or; the empty identity is false.

    Example:
        ```python
        from kg_build_system import any_of, value_expression

        either = any_of(value_expression(False), value_expression(True))
        assert either.model.operator == "or"
        ```
    """
    return any_of_impl(*predicates)


__all__ = ["all_of", "any_of"]
