"""Numeric operation mechanics for the authoring number family."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .apply import apply_operation
from .coercion import expression_input

if TYPE_CHECKING:
    from ...model.public.values import ValueExpression


def binary(expression: ValueExpression[Any], operator: str, other: Any) -> Any:
    right = expression_input(other, expression.logical_type)
    return type(expression)(apply_operation(operator, expression.model, right).model)


__all__ = ["binary"]
