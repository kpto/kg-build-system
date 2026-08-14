"""Internal conversion of authoring inputs to canonical expression nodes."""
from __future__ import annotations

from typing import Any

from ..types import FLOAT, LogicalType, NullableType
from .ir import ExpressionNode
from .literals import literal
from .values import ValueExpression


def expression_input(value: Any, expected: LogicalType) -> ExpressionNode:
    if isinstance(value, ValueExpression):
        result = value.expression
    else:
        literal_type = expected
        if isinstance(expected, NullableType) and value is not None:
            literal_type = expected.value
        # Python's static numeric tower admits an int where a float is
        # requested. Canonical IR still records a genuine float literal.
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
