"""Boolean predicate composition interface."""
from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ...model.public.boolean import BoolExpression


def all_of(*predicates: BoolExpression) -> BoolExpression:
    """Combine predicates with logical and; the empty identity is true."""
    from .._private.boolean import all_of as combine

    return combine(*predicates)


def any_of(*predicates: BoolExpression) -> BoolExpression:
    """Combine predicates with logical or; the empty identity is false."""
    from .._private.boolean import any_of as combine

    return combine(*predicates)


__all__ = ["all_of", "any_of"]
