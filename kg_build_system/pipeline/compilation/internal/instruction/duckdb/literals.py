"""Literal policy for DuckDB.

Only text-canonical units and arrays of them are frozen as text, so only those
need a cast back to their logical type. Every other literal freezes as JSON in
the shape SQL already understands.
"""
from __future__ import annotations

from typing import Any

from sqlglot import exp

from .sql import SqlNode

from ......kernel.internal.json import thaw_json
from ......kernel.internal.types import TEXT_CANONICAL_UNIT_NAMES
from ......declaration.foundations.expressions.internal import LiteralExpressionDTO
from ......kernel.internal.types.dto import ArrayTypeDTO, LogicalTypeDTO, NullableTypeDTO, UnitTypeDTO
from .types import ArraySqlType, SqlType, canonical_sql_type


def literal_cast_type(logical_type: LogicalTypeDTO) -> SqlType | None:
    """The SQL type a text-frozen literal carries, or ``None`` to leave it JSON."""
    value = (
        logical_type.value
        if isinstance(logical_type, NullableTypeDTO)
        else logical_type
    )
    if isinstance(value, UnitTypeDTO):
        return value.name if value.name in TEXT_CANONICAL_UNIT_NAMES else None
    if isinstance(value, ArrayTypeDTO):
        item = literal_cast_type(value.item)
        return ArraySqlType(item=item) if item is not None else None
    return None


def literal_sql(expression: LiteralExpressionDTO) -> SqlNode:
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


__all__ = ["literal_cast_type", "literal_sql"]
