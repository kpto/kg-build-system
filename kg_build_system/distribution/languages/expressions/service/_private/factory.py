"""Runtime construction of the compiler expression wrapper."""
from __future__ import annotations

from typing import Any

from kg_build_system.kernel.model.public.types import LogicalType
from ...model.internal.model import ExpressionNode
from .literals import literal as _literal
from ...model.public.values import ValueExpression


def wrap_expression(expression: ExpressionNode) -> ValueExpression[Any]:
    """Wrap one expression node in the compiler-facing wrapper."""
    return ValueExpression(expression)


def value_expression(
    value: Any, *, logical_type: LogicalType | None = None,
) -> ValueExpression[Any]:
    """Construct a compiler expression for a portable literal."""
    return wrap_expression(_literal(value, logical_type=logical_type))


__all__ = ["value_expression", "wrap_expression"]
