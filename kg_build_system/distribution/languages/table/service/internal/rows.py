"""Row-source plan construction for authored row-source values.

The algebra lives in the package's private zone; each name here is a thin
delegation kept for the internal service path.
"""
from __future__ import annotations

from collections.abc import Callable, Mapping
from typing import Any

from kg_build_system.distribution.languages.expressions.model.public import (
    BoolExpression,
)


def as_row_source(value: Any) -> Any:
    """Require a value row source."""
    from .._private.rows import as_row_source as require

    return require(value)


def declaration_source_name(source: Any) -> str:
    """Return the logical name a table or projection writes."""
    from .._private.rows import declaration_source_name as name

    return name(source)


def derive_where(
    source: Any, predicate: Callable[[Any], BoolExpression],
) -> Any:
    """Add one validated filter over a value row source."""
    from .._private.rows import derive_where as derive

    return derive(source, predicate)


def derive_row_source(
    parent: Any, predicate: BoolExpression, *, shape: Any | None = None,
) -> Any:
    """Add one filter over a row source, preserving its shape by default."""
    from .._private.rows import derive_row_source as derive

    return derive(parent, predicate, shape=shape)


def derive_union(source: Any, other: Any, *, all: bool = True) -> Any:
    """Stack two same-shaped sources; ``all=False`` removes duplicates."""
    from .._private.rows import derive_union as derive

    return derive(source, other, all=all)


def derive_join(
    source: Any, other: Any, *,
    on: Callable[[Any, Any], tuple[Any, Any]],
    how: str = "inner",
) -> Any:
    """Equi-join two value row sources on one key expression from each side."""
    from .._private.rows import derive_join as derive

    return derive(source, other, on=on, how=how)


def derive_group_by(source: Any, *, by: Callable[[Any], Any]) -> Any:
    """Group rows by named key expressions; null keys are dropped."""
    from .._private.rows import derive_group_by as derive

    return derive(source, by=by)


def derive_distinct(source: Any) -> Any:
    """Drop duplicate rows without changing the shape."""
    from .._private.rows import derive_distinct as derive

    return derive(source)


def derive_order_by(
    source: Any, *keys: Any, ascending: bool = True,
) -> Any:
    """Order rows by expressions, selections, or column names."""
    from .._private.rows import derive_order_by as derive

    return derive(source, *keys, ascending=ascending)


def row_source_plan_dto(value: Any) -> Any:
    """Return the plan a value row source authors."""
    from .._private.rows import row_source_plan_dto as plan

    return plan(value)


def plan_fields(
    plan: Any, declarations: Mapping[str, Any],
) -> tuple[Any, ...]:
    """Return the row shape a plan produces from its plan and declarations."""
    from .._private.rows import plan_fields as fields

    return fields(plan, declarations)


def plan_inputs(plan: Any) -> tuple[Any, ...]:
    """Return the direct child plans a plan reads."""
    from .._private.rows import plan_inputs as inputs

    return inputs(plan)


def plan_scan_sources(plan: Any) -> tuple[str, ...]:
    """Return every named table or projection a plan reads."""
    from .._private.rows import plan_scan_sources as sources

    return sources(plan)


def plan_expressions(plan: Any) -> tuple[Any, ...]:
    """Return every expression a plan itself evaluates."""
    from .._private.rows import plan_expressions as expressions

    return expressions(plan)


def plan_shape_source_name(plan: Any) -> str:
    """Return the source the authoring shape's own fields refer to."""
    from .._private.rows import plan_shape_source_name as name

    return name(plan)


def retarget_expression_dto(
    expression: Any, mapping: Mapping[str, str],
) -> Any:
    """Rewrite field references from one logical source key to another."""
    from .._private.rows import retarget_expression_dto as retarget

    return retarget(expression, mapping)


def row_source_key(plan: Any) -> str:
    """Return the logical source key one plan's rows are read through."""
    from .._private.rows import row_source_key as key

    return key(plan)


def shape_context(shape: type[Any]) -> Any:
    """A symbolic instance of a shape, used as the subject of authoring lambdas."""
    from .._private.shapes import make_shape_context

    return make_shape_context(shape)


__all__ = [
    "as_row_source", "declaration_source_name", "derive_distinct",
    "derive_group_by", "derive_join", "derive_order_by", "derive_row_source",
    "derive_union", "derive_where", "plan_expressions", "plan_fields",
    "plan_inputs", "plan_scan_sources", "plan_shape_source_name",
    "retarget_expression_dto", "row_source_key", "row_source_plan_dto",
    "shape_context",
]
