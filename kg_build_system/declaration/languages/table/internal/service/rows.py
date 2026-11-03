"""Row-source plan construction for authored row-source values.

The algebra lives in the package's private zone; each name here is a thin
delegation kept for the internal service path.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from kg_build_system.declaration.foundations.expressions.public import (
    BoolExpression,
)


def derive_where(
    source: Any, predicate: Callable[[Any], BoolExpression],
) -> Any:
    """Add one validated filter over a value row source."""
    from ..._private.rows import derive_where as derive

    return derive(source, predicate)


def derive_row_source(
    parent: Any, predicate: BoolExpression, *, shape: Any | None = None,
) -> Any:
    """Add one filter over a row source, preserving its shape by default."""
    from ..._private.rows import derive_row_source as derive

    return derive(parent, predicate, shape=shape)


def derive_union(source: Any, other: Any, *, all: bool = True) -> Any:
    """Stack two same-shaped sources; ``all=False`` removes duplicates."""
    from ..._private.rows import derive_union as derive

    return derive(source, other, all=all)


def derive_join(
    source: Any, other: Any, *,
    on: Callable[[Any, Any], tuple[Any, Any]],
    how: str = "inner",
) -> Any:
    """Equi-join two value row sources on one key expression from each side."""
    from ..._private.rows import derive_join as derive

    return derive(source, other, on=on, how=how)


def derive_group_by(source: Any, *, by: Callable[[Any], Any]) -> Any:
    """Group rows by named key expressions; null keys are dropped."""
    from ..._private.rows import derive_group_by as derive

    return derive(source, by=by)


def derive_distinct(source: Any) -> Any:
    """Drop duplicate rows without changing the shape."""
    from ..._private.rows import derive_distinct as derive

    return derive(source)


def derive_order_by(
    source: Any, *keys: Any, ascending: bool = True,
) -> Any:
    """Order rows by expressions, selections, or column names."""
    from ..._private.rows import derive_order_by as derive

    return derive(source, *keys, ascending=ascending)


def row_source_plan_dto(value: Any) -> Any:
    """Return the plan a value row source authors."""
    from ..._private.rows import row_source_plan_dto as plan

    return plan(value)


__all__ = [
    "derive_distinct", "derive_group_by", "derive_join", "derive_order_by",
    "derive_row_source", "derive_union", "derive_where", "row_source_plan_dto",
]
