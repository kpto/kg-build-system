"""Text operation mechanics for the authoring string family."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .....kernel.internal.types import STR
from .apply import apply_operation
from .coercion import expression_input

if TYPE_CHECKING:
    from ..public.model.values import ValueExpression


def separator_cut(
    expression: ValueExpression[Any],
    separator: str,
    occurrence: int,
    side: str,
    *,
    include_separator: bool,
):
    if not separator:
        raise ValueError("separator must be non-empty")
    if occurrence < 1:
        raise ValueError("occurrence must be at least 1")
    operator = {
        "before": "before_separator",
        "after": "after_separator",
    }[side]
    from ..public.model.text import StrExpression

    return StrExpression(
        apply_operation(
            operator,
            expression.model,
            expression_input(separator, STR),
            occurrence=occurrence,
            include_separator=include_separator,
        ).model
    )


__all__ = ["separator_cut"]
