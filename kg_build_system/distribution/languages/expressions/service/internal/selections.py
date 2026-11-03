"""Selection construction interface used by the public service."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ...model.public.selections.value import ValueInput, ValueSelection
    from ...model.public.values import ValueExpression


def select_expression[T](expression: ValueExpression[T]) -> ValueSelection[T]:
    """Wrap a bindable expression in the selection matching its logical shape."""
    from .._private.selections import select_expression as select

    return select(expression)


def select_member(
    name: str, logical_type: Any, declaration: Any,
) -> ValueSelection[Any]:
    """Create the temporary selection returned by a field on a struct proxy."""
    from .._private.selections import select_member as member

    return member(name, logical_type, declaration)


def as_expression[T](value: ValueInput[T]) -> ValueExpression[T]:
    """Normalize a terminal authoring input to its bindable expression."""
    from .._private.selections import as_expression as expression

    return expression(value)


__all__ = ["as_expression", "select_expression", "select_member"]
