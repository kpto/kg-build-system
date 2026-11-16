"""Authoring helpers for row-source values and derived-relation bases."""
from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

from kg_build_system.distribution.languages.expressions.model.public import (
    Selection,
)
from kg_build_system.kernel.model.public.types import Array, Nullable, Shape
from ...model.internal.dto.blueprint_dto import RowScanDTO
from ...model.public.fields import ScalarValue
from ...model.public.row_sources import (
    DerivedRowSource,
    GroupByKeys,
    JoinHow,
    OrderByKey,
    RowSource,
)
from ..internal.declarations import (
    derived_relation_row_source as derived_relation_row_source_impl,
    relation_plan_dto as relation_plan_dto_impl,
)
from ..internal.rows import (
    derive_distinct as derive_distinct_impl,
    derive_group_by as derive_group_by_impl,
    derive_join as derive_join_impl,
    derive_order_by as derive_order_by_impl,
    derive_union as derive_union_impl,
    derive_unnest as derive_unnest_impl,
    derive_where as derive_where_impl,
    shape_context as shape_context_impl,
)

S = TypeVar("S", bound=Shape)


def shape_context(shape: type[S]) -> S:
    """A symbolic instance of a shape, used as the subject of authoring lambdas.

    Example:
        ```python
        from kg_build_system import SourceRelation, field
        from kg_build_system.distribution.languages.data import shape_context

        class Site(SourceRelation):
            site_id = field()

        site = shape_context(Site)
        ```
    """
    return shape_context_impl(shape)


def derived_relation_row_source(
    declaration: type[object],
) -> RowSource[Shape] | None:
    """Return the pinned plan or the plan derived from an old-style derived relation.

    Example:
        ```python
        from kg_build_system import SourceRelation, field

        class Site(SourceRelation):
            site_id = field()

        plan = Site.row_source()
        ```
    """
    return derived_relation_row_source_impl(declaration)


def relation_plan_dto(source: type[Shape]) -> RowScanDTO:
    """Return the scan plan for one named source or derived relation."""
    return relation_plan_dto_impl(source)


def derive_unnest[S: Shape, I](
    source: RowSource[S],
    selector: Callable[
        [S], Selection[Array[I]] | Selection[Nullable[Array[I]]],
    ],
) -> DerivedRowSource[S]:
    """Expand one array member into rows, narrowing that member to its item.

    The selected array must be a direct field read. A null or empty array
    produces no rows; every other field is preserved.
    """
    return derive_unnest_impl(source, selector)


def derive_where[S: Shape](
    source: RowSource[S], predicate: Callable[[S], Selection[bool]],
) -> DerivedRowSource[S]:
    """Add one validated filter over a value row source."""
    return derive_where_impl(source, predicate)


def derive_union[S: Shape, S2: Shape](
    source: RowSource[S], other: RowSource[S2], *, all: bool = True,
) -> DerivedRowSource[S]:
    """Stack two same-shaped sources; ``all=False`` removes duplicates."""
    return derive_union_impl(source, other, all=all)


def derive_join[
    S: Shape, S2: Shape, K1: Nullable[ScalarValue], K2: Nullable[ScalarValue],
](
    source: RowSource[S], other: RowSource[S2], *,
    on: Callable[[S, S2], tuple[Selection[K1], Selection[K2]]],
    how: JoinHow = "inner",
) -> DerivedRowSource[Shape]:
    """Equi-join two value row sources on one key expression from each side."""
    return derive_join_impl(source, other, on=on, how=how)


def derive_group_by[S: Shape](
    source: RowSource[S], *, by: Callable[[S], GroupByKeys],
) -> DerivedRowSource[Shape]:
    """Group rows by named key expressions; null keys are dropped."""
    return derive_group_by_impl(source, by=by)


def derive_distinct[S: Shape](source: RowSource[S]) -> DerivedRowSource[S]:
    """Drop duplicate rows without changing the shape."""
    return derive_distinct_impl(source)


def derive_order_by[S: Shape](
    source: RowSource[S], *keys: OrderByKey[S], ascending: bool = True,
) -> DerivedRowSource[S]:
    """Order rows by expressions, selections, or column names."""
    return derive_order_by_impl(source, *keys, ascending=ascending)


__all__ = ["derived_relation_row_source", "shape_context"]
