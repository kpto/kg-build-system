"""Internal conversion of authoring inputs to canonical expression nodes."""
from __future__ import annotations

from typing import TYPE_CHECKING, Any

from kg_build_system.kernel.model.public.types import FLOAT, LogicalType, NullableType
from .literals import literal
from ...model.internal.model import ExpressionNode

if TYPE_CHECKING:
    from ...model.public.values import ValueExpression


def expression_input(value: Any, expected: LogicalType) -> ExpressionNode:
    """Normalize a literal or typed expression and check its logical type."""
    from ...model.public.selection import Selection
    from ...model.public.values import ValueExpression

    if isinstance(value, Selection):
        from .selections import as_expression

        result = as_expression(value).model
    elif isinstance(value, ValueExpression):
        result = value.model
    else:
        literal_type = expected
        if isinstance(expected, NullableType) and value is not None:
            literal_type = expected.value
        # Python's static numeric tower admits an int where a float is
        # requested. The canonical DTO still records a genuine float literal.
        if literal_type == FLOAT and type(value) is int:
            value = float(value)
        result = literal(value, logical_type=literal_type)
    if result.logical_type != expected:
        if not (
            isinstance(expected, NullableType)
            and result.logical_type == expected.value
        ):
            raise TypeError(
                f"expression input has logical type {result.logical_type!r}; "
                f"expected {expected!r}"
            )
    return result


__all__ = ["expression_input"]
