"""Authoring helpers for row-source values and derived-relation bases."""
from __future__ import annotations

from collections.abc import Callable
from typing import Literal, TypeVar, cast, overload

from kg_build_system.distribution.languages.expressions.model.public import (
    Selection,
)
from kg_build_system.kernel import JsonValue
from kg_build_system.kernel.model.public.types import Array, Nullable, Shape
from ...model.internal.dto.blueprint_dto import RowScanDTO
from ...model.public.row_operations import RelationOperation
from ...model.public.row_sources import (
    DerivedRowSource,
    GroupByKeys,
    JoinHow,
    OrderByKey,
    RowSource,
)
from ...model.public.shapes import (
    FullJoinedShape,
    GroupedShape,
    InnerJoinedShape,
    LeftJoinedShape,
    RightJoinedShape,
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
    derive_relation_operation as derive_relation_operation_impl,
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


def derive_unnest[S: Shape, I, Out: Shape](
    source: RowSource[S],
    selector: Callable[
        [S], Selection[Array[I]] | Selection[Nullable[Array[I]]],
    ],
    *,
    out: type[Out],
) -> DerivedRowSource[Out]:
    """Expand one array member into rows, narrowing that member to its item.

    The selected array must be a direct field read. A null or empty array
    produces no rows; every other field is preserved. ``out`` is the declared
    shape the generated row must match.
    """
    return derive_unnest_impl(source, selector, out=out)


def derive_where[S: Shape](
    source: RowSource[S], predicate: Callable[[S], Selection[bool]],
) -> DerivedRowSource[S]:
    """Add one validated filter over a value row source."""
    return derive_where_impl(source, predicate)


def derive_union[S: Shape](
    source: RowSource[S], other: RowSource[S], *, all: bool = True,
) -> DerivedRowSource[S]:
    """Stack two same-shaped sources; ``all=False`` removes duplicates."""
    return derive_union_impl(source, other, all=all)


@overload
def derive_join[S: Shape, S2: Shape, K](
    source: RowSource[S], other: RowSource[S2], *,
    on: Callable[[S, S2], tuple[Selection[K], Selection[K]]],
    how: Literal["inner"] = "inner",
) -> DerivedRowSource[InnerJoinedShape[S, S2, K]]: ...
@overload
def derive_join[S: Shape, S2: Shape, K](
    source: RowSource[S], other: RowSource[S2], *,
    on: Callable[[S, S2], tuple[Selection[K], Selection[K]]],
    how: Literal["left"],
) -> DerivedRowSource[LeftJoinedShape[S, S2, K]]: ...
@overload
def derive_join[S: Shape, S2: Shape, K](
    source: RowSource[S], other: RowSource[S2], *,
    on: Callable[[S, S2], tuple[Selection[K], Selection[K]]],
    how: Literal["right"],
) -> DerivedRowSource[RightJoinedShape[S, S2, K]]: ...
@overload
def derive_join[S: Shape, S2: Shape, K](
    source: RowSource[S], other: RowSource[S2], *,
    on: Callable[[S, S2], tuple[Selection[K], Selection[K]]],
    how: Literal["full"],
) -> DerivedRowSource[FullJoinedShape[S, S2, K]]: ...
def derive_join[S: Shape, S2: Shape, K](
    source: RowSource[S], other: RowSource[S2], *,
    on: Callable[[S, S2], tuple[Selection[K], Selection[K]] | Selection[bool]],
    how: JoinHow = "inner",
) -> DerivedRowSource[Shape]:
    """Equi-join two value row sources on one key expression from each side."""
    return cast(
        "DerivedRowSource[Shape]",
        derive_join_impl(source, other, on=on, how=how),
    )


def derive_group_by[S: Shape, K: Shape](
    source: RowSource[S], *, keys: type[K], by: Callable[[S], GroupByKeys],
) -> DerivedRowSource[GroupedShape[S, K]]:
    """Group rows by named key expressions; null keys are dropped."""
    return derive_group_by_impl(source, keys=keys, by=by)


def derive_relation_operation[S: Shape, Out: Shape](
    source: RowSource[S],
    operation: RelationOperation[S, Out],
    **parameters: JsonValue,
) -> DerivedRowSource[Out]:
    """Compose one project relation operation over one input row source.

    Example:
        ```python
        rows = derive_relation_operation(Row.row_source(), count_rows)
        ```
    """
    return derive_relation_operation_impl(source, operation, **parameters)


def derive_distinct[S: Shape](source: RowSource[S]) -> DerivedRowSource[S]:
    """Drop duplicate rows without changing the shape."""
    return derive_distinct_impl(source)


def derive_order_by[S: Shape](
    source: RowSource[S], *keys: OrderByKey[S], ascending: bool = True,
) -> DerivedRowSource[S]:
    """Order rows by expressions, selections, or column names."""
    return derive_order_by_impl(source, *keys, ascending=ascending)


__all__ = ["derived_relation_row_source", "shape_context"]
