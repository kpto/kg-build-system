"""Authoring helpers for row-source values and projection bases."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypeVar

from kg_build_system.distribution.languages.expressions.model.public import (
    Selection,
)
from kg_build_system.kernel.model.public.types import Shape
from ..internal.declarations import (
    projection_row_source as projection_row_source_impl,
    relation_plan_dto as relation_plan_dto_impl,
)
from ..internal.rows import (
    derive_distinct as derive_distinct_impl,
    derive_group_by as derive_group_by_impl,
    derive_join as derive_join_impl,
    derive_order_by as derive_order_by_impl,
    derive_union as derive_union_impl,
    derive_where as derive_where_impl,
    shape_context as shape_context_impl,
)

S = TypeVar("S", bound=Shape)


def shape_context(shape: type[S]) -> S:
    """A symbolic instance of a shape, used as the subject of authoring lambdas.

    Example:
        ```python
        from kg_build_system import Table, field
        from kg_build_system.distribution.languages.data import shape_context

        class Site(Table):
            site_id = field()

        site = shape_context(Site)
        ```
    """
    return shape_context_impl(shape)


def projection_row_source(declaration: type[Any]) -> Any | None:
    """Return the pinned plan or the plan derived from an old-style projection.

    Example:
        ```python
        from kg_build_system import Table, field

        class Site(Table):
            site_id = field()

        plan = Site.row_source()
        ```
    """
    return projection_row_source_impl(declaration)


def relation_plan_dto(source: type[Any]) -> Any:
    """Return the scan plan for one named table or projection relation."""
    return relation_plan_dto_impl(source)


def derive_where(
    source: Any, predicate: Callable[[Any], Selection[bool]],
) -> Any:
    """Add one validated filter over a value row source."""
    return derive_where_impl(source, predicate)


def derive_union(source: Any, other: Any, *, all: bool = True) -> Any:
    """Stack two same-shaped sources; ``all=False`` removes duplicates."""
    return derive_union_impl(source, other, all=all)


def derive_join(
    source: Any, other: Any, *,
    on: Callable[[Any, Any], tuple[Any, Any]],
    how: str = "inner",
) -> Any:
    """Equi-join two value row sources on one key expression from each side."""
    return derive_join_impl(source, other, on=on, how=how)


def derive_group_by(source: Any, *, by: Callable[[Any], Any]) -> Any:
    """Group rows by named key expressions; null keys are dropped."""
    return derive_group_by_impl(source, by=by)


def derive_distinct(source: Any) -> Any:
    """Drop duplicate rows without changing the shape."""
    return derive_distinct_impl(source)


def derive_order_by(
    source: Any, *keys: Any, ascending: bool = True,
) -> Any:
    """Order rows by expressions, selections, or column names."""
    return derive_order_by_impl(source, *keys, ascending=ascending)


__all__ = ["projection_row_source", "shape_context"]
