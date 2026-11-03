"""Predicate combinators over the Boolean expression family."""
from __future__ import annotations

from ..._private.boolean import all_of as _all_of
from ..._private.boolean import any_of as _any_of
from ..model.boolean import BoolExpression


def all_of(*predicates: BoolExpression) -> BoolExpression:
    """Combine predicates with logical and; the empty identity is true.

    Example:
        ```python
        from kg_build_system import all_of, value_expression

        both = all_of(value_expression(True), value_expression(False))
        assert both.model.operator == "and"
        ```
    """
    return _all_of(*predicates)


def any_of(*predicates: BoolExpression) -> BoolExpression:
    """Combine predicates with logical or; the empty identity is false.

    Example:
        ```python
        from kg_build_system import any_of, value_expression

        either = any_of(value_expression(False), value_expression(True))
        assert either.model.operator == "or"
        ```
    """
    return _any_of(*predicates)


__all__ = ["all_of", "any_of"]
