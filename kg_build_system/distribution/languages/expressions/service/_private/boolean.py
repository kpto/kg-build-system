"""Boolean predicate combinators over compiler expressions."""
from __future__ import annotations

from typing import Any

from kg_build_system.kernel.model.public.types import BOOL
from .apply import apply_operation
from .literals import literal
from ...model.public.values import ValueExpression


def any_of(*predicates: ValueExpression[Any]) -> ValueExpression[Any]:
    """Combine predicates with logical or."""
    if not predicates:
        return ValueExpression(literal(False, logical_type=BOOL))
    result = predicates[0]
    for predicate in predicates[1:]:
        result = ValueExpression(apply_operation("or", result.model, predicate.model).model)
    return result


def all_of(*predicates: ValueExpression[Any]) -> ValueExpression[Any]:
    """Combine predicates with logical and."""
    if not predicates:
        return ValueExpression(literal(True, logical_type=BOOL))
    result = predicates[0]
    for predicate in predicates[1:]:
        result = ValueExpression(apply_operation("and", result.model, predicate.model).model)
    return result


__all__ = ["all_of", "any_of"]
