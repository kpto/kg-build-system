"""Selection construction interface used by the public service."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...model.public.selection import Selection
    from ...model.public.values import ValueExpression


def select_expression(expression: Any) -> "Selection[Any]":
    """Wrap a bindable expression in the single authoring type."""
    from .._private.selections import select_expression as select

    return select(expression)


def select_member(
    name: str, logical_type: Any, declaration: Any,
) -> "Selection[Any]":
    """Create the temporary selection returned by a field on a struct proxy."""
    from .._private.selections import select_member as member

    return member(name, logical_type, declaration)


def as_expression(value: Any) -> "ValueExpression[Any]":
    """Normalize a terminal authoring input to its private expression."""
    from .._private.selections import as_expression as expression

    return expression(value)


__all__ = ["as_expression", "select_expression", "select_member"]
