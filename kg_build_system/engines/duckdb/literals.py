"""Literal policy for DuckDB.

Only text-canonical units and arrays of them are frozen as text, so only those
need a cast back to their logical type. Every other literal freezes as JSON in
the shape SQL already understands.
"""
from __future__ import annotations

from typing import Any

from sqlglot import exp

from .sql import SqlNode

from ..._frozen_json import thaw_json
from ...types.interfaces import TEXT_CANONICAL_UNIT_NAMES
from ...expressions.ir import LiteralExpressionIR
from ...types.ir import ArrayTypeIR, LogicalTypeIR, NullableTypeIR, UnitTypeIR
from .types import ArraySqlType, SqlType, canonical_sql_type


def literal_cast_type(logical_type: LogicalTypeIR) -> SqlType | None:
    """The SQL type a text-frozen literal carries, or ``None`` to leave it JSON."""
    value = (
        logical_type.value
        if isinstance(logical_type, NullableTypeIR)
        else logical_type
    )
    if isinstance(value, UnitTypeIR):
        return value.name if value.name in TEXT_CANONICAL_UNIT_NAMES else None
    if isinstance(value, ArrayTypeIR):
        item = literal_cast_type(value.item)
        return ArraySqlType(item=item) if item is not None else None
    return None


def lower_literal(expression: LiteralExpressionIR) -> SqlNode:
    value: Any = thaw_json(expression.value)
    canonical = literal_cast_type(expression.logical_type)
    if canonical is not None and isinstance(value, (str, list)):
        # An array cast applies element-wise and is checked, so items stay plain
        # text literals and one outer cast names the type of the whole value.
        return exp.cast(
            exp.convert(value),
            exp.DataType.build(canonical_sql_type(canonical)),
        )
    return exp.convert(value)


__all__ = ["literal_cast_type", "lower_literal"]
