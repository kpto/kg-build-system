"""Predicate folding for the Boolean authoring family."""
from __future__ import annotations

from typing import TYPE_CHECKING

from ...types.internal import BOOL
from .literals import literal

if TYPE_CHECKING:
    from ..public.boolean import BoolExpression


def any_of(*predicates: BoolExpression) -> BoolExpression:
    """Combine predicates with logical or; the empty identity is false."""
    from ..public.boolean import BoolExpression

    if not predicates:
        return BoolExpression(literal(False, logical_type=BOOL))
    result = predicates[0]
    for predicate in predicates[1:]:
        result = result.or_(predicate)
    return result


def all_of(*predicates: BoolExpression) -> BoolExpression:
    """Combine predicates with logical and; the empty identity is true."""
    from ..public.boolean import BoolExpression

    if not predicates:
        return BoolExpression(literal(True, logical_type=BOOL))
    result = predicates[0]
    for predicate in predicates[1:]:
        result = result.and_(predicate)
    return result


__all__ = ["all_of", "any_of"]
