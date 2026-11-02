"""Composition of DuckDB expression lowerers, one module per operation.

Each operation module exports its lowerer. Composition happens once, at import,
and rejects a duplicate operator name so two implementations cannot silently
shadow one another.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from collections.abc import Iterable, Mapping


if TYPE_CHECKING:
    from ....internal.protocols import ExpressionLowerer
from . import (
    add, after_separator, and_, append, array_at, array_slice, before_separator,
    coalesce, concat, distinct, drop_null_items, equals, expand, join, not_,
    or_, replace, sort, struct_field, subtract, to_string, transform_items,
    where_if, where_present,
)

OPERATORS = (
    add.ADD,
    subtract.SUBTRACT,
    equals.EQUALS,
    and_.AND,
    or_.OR,
    not_.Not(),
    concat.Concat(),
    append.Append(),
    replace.Replace(),
    to_string.ToString(),
    before_separator.BeforeSeparator(),
    after_separator.AfterSeparator(),
    array_at.ArrayAt(),
    array_slice.ArraySlice(),
    transform_items.TransformItems(),
    drop_null_items.DropNullItems(),
    sort.Sort(),
    distinct.Distinct(),
    join.ArrayJoin(),
    struct_field.StructField(),
    expand.Expand(),
    where_present.WherePresent(),
    where_if.WhereIf(),
    coalesce.Coalesce(),
)


def compose_operators(
    *groups: Iterable[ExpressionLowerer],
) -> Mapping[str, ExpressionLowerer]:
    registry: dict[str, ExpressionLowerer] = {}
    for group in groups:
        for lowerer in group:
            if not lowerer.operator:
                raise ValueError("expression lowerers require a non-empty operator")
            if lowerer.operator in registry:
                raise ValueError(
                    f"duplicate expression operator {lowerer.operator!r}"
                )
            registry[lowerer.operator] = lowerer
    return registry


DEFAULT_OPERATORS = compose_operators(OPERATORS)

__all__ = ["DEFAULT_OPERATORS", "OPERATORS", "compose_operators"]
