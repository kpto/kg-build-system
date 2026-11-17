"""Author-facing row-source values and their relational operations.

A row source is a value: a shape plus a plan. ``where``, ``union``, ``distinct``
and ``order_by`` preserve the shape; ``join`` and ``group_by`` generate a shape
because the row genuinely has new members.

Example:
    ```python
    from kg_build_system import computed_field

    active = SiteTable.row_source().where(
        lambda site: site.name.alter_rows().drop_null().expression.equals("Depot")
    )
    everyone = SiteTable.row_source().union(ArchivedSiteTable.row_source())

    class ActiveSiteLabels(DerivedRelation(active)):
        label = computed_field(SiteTable.name)
    ```
"""
from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Generic, Literal, Self, TypeVar, cast, overload

from kg_build_system.distribution.languages.expressions.model.public import (
    Selection,
)
from kg_build_system.kernel import JsonValue
from kg_build_system.kernel.model.public.types import Array, Nullable, Shape
from ..internal.dto.blueprint_dto import RowScanDTO, RowSourcePlanDTO
from .fields import ScalarValue
from .shapes import (
    FullJoinedShape, GroupedShape, InnerJoinedShape, LeftJoinedShape,
    RightJoinedShape, ShapeField,
)

if TYPE_CHECKING:
    from .row_operations import RelationOperation

S = TypeVar("S", bound=Shape, covariant=True)
JoinHow = Literal["inner", "left", "right", "full"]

type GroupByKeys = (
    Mapping[str, Selection[Nullable[ScalarValue]]]
    | Sequence[tuple[str, Selection[Nullable[ScalarValue]]]]
    | Selection[Nullable[ScalarValue]]
)
type OrderByKey[S: Shape] = str | Selection[object] | Callable[[S], Selection[object]]


class RowSourceProvider(Shape):
    """A declaration that provides a row source through ``row_source()``."""

    @classmethod
    def row_source(cls) -> "RowSource[Self]":
        """Return the relation row source for this declaration.

        Example:
            ```python
            from kg_build_system import SourceRelation, field

            class Site(SourceRelation):
                site_id = field()

            rows = Site.row_source()
            ```
        """
        raise NotImplementedError


class RowSource(Generic[S]):
    """A source of rows whose shape is ``S``; declarations satisfy it by subclassing."""

    shape: type[S]

    def where(self, predicate: Callable[[S], Selection[bool]]) -> "DerivedRowSource[S]":
        """Keep rows whose predicate is true.

        The predicate receives a symbolic shape instance and must return a
        ``Selection[bool]``.

        Example:
            ```python
            active = SiteTable.row_source().where(
                lambda site: site.name.alter_rows().drop_null()
                .expression.equals("Depot")
            )
            ```
        """
        from ...service.public.rows import derive_where

        return derive_where(self, predicate)

    def unnest[I, Out: Shape](
        self,
        selector: Callable[
            [S], Selection[Array[I]] | Selection[Nullable[Array[I]]],
        ],
        *,
        out: type[Out],
    ) -> "DerivedRowSource[Out]":
        """Expand one array member into rows, one row per item.

        The selected array must be a direct field read. The result keeps the
        other fields and narrows the selected field to its item shape. A null
        or empty array produces no rows. This is the row-source spelling of
        expansion; ``Selection.expand`` stays a selection row effect.

        ``out`` names the shape the expanded row has: every preserved member
        with its unchanged type and the selected member with the array's item
        type. The runtime shape must match it.

        Example:
            ```python
            from kg_build_system import (
                Array, Field, Nullable, Selection, Shape, SourceRelation, field,
            )

            class Site(SourceRelation):
                site_id: Field[str] = field(name="site_id")
                tags: Field[Array[str]] = field(name="tags")

            class TaggedSite(Shape):
                site_id: Selection[Nullable[str]]
                tags: Selection[str]

            one_tag_per_row = Site.row_source().unnest(
                lambda site: site.tags, out=TaggedSite,
            )
            ```
        """
        from ...service.public.rows import derive_unnest

        return derive_unnest(self, selector, out=out)

    def union(
        self, other: "RowSource[S]", *, all: bool = True,
    ) -> "DerivedRowSource[S]":
        """Stack two same-shaped sources; ``all=False`` removes duplicates.

        Example:
            ```python
            everyone = SiteTable.row_source().union(
                ArchivedSiteTable.row_source()
            )
            ```
        """
        from ...service.public.rows import derive_union

        return derive_union(self, other, all=all)

    @overload
    def join[S2: Shape, K](
        self, other: "RowSource[S2]", *,
        on: Callable[[S, S2], tuple[Selection[K], Selection[K]]],
        how: Literal["inner"] = "inner",
    ) -> "DerivedRowSource[InnerJoinedShape[S, S2, K]]": ...
    @overload
    def join[S2: Shape, K](
        self, other: "RowSource[S2]", *,
        on: Callable[[S, S2], tuple[Selection[K], Selection[K]]],
        how: Literal["left"],
    ) -> "DerivedRowSource[LeftJoinedShape[S, S2, K]]": ...
    @overload
    def join[S2: Shape, K](
        self, other: "RowSource[S2]", *,
        on: Callable[[S, S2], tuple[Selection[K], Selection[K]]],
        how: Literal["right"],
    ) -> "DerivedRowSource[RightJoinedShape[S, S2, K]]": ...
    @overload
    def join[S2: Shape, K](
        self, other: "RowSource[S2]", *,
        on: Callable[[S, S2], tuple[Selection[K], Selection[K]]],
        how: Literal["full"],
    ) -> "DerivedRowSource[FullJoinedShape[S, S2, K]]": ...
    def join[S2: Shape, K](
        self, other: "RowSource[S2]", *,
        on: Callable[
            [S, S2], tuple[Selection[K], Selection[K]] | Selection[bool],
        ],
        how: JoinHow = "inner",
    ) -> "DerivedRowSource[Shape]":
        """Equi-join two sources on one expression from each side.

        ``on`` receives one shape instance per side and returns the two key
        selections. A null key never matches in any join mode. The result's
        shape names the key and both rows, with the absent side nullable.

        Example:
            ```python
            site_readings = SiteTable.row_source().join(
                ReadingTable.row_source(),
                on=lambda site, reading: (site.site_id, reading.site_id),
                how="left",
            )
            ```
        """
        from ...service.public.rows import derive_join

        # The implementation accepts the broad key-or-predicate form; the
        # overloads publish only the precise tuple form.
        join = cast(
            "Callable[..., DerivedRowSource[Shape]]", derive_join,
        )
        return join(self, other, on=on, how=how)

    def group_by[K: Shape](
        self, *, keys: type[K], by: Callable[[S], GroupByKeys],
    ) -> "DerivedRowSource[GroupedShape[S, K]]":
        """Group rows by named key expressions; null keys are dropped.

        ``keys`` names the shape of the grouped key record; ``by`` returns the
        key expressions whose names and types must match that shape.

        Example:
            ```python
            from kg_build_system import Nullable, Selection, Shape

            class RegionKey(Shape):
                region_id: Selection[Nullable[str]]

            by_region = SiteTable.row_source().group_by(
                keys=RegionKey,
                by=lambda site: {"region_id": site.region_id},
            )
            ```
        """
        from ...service.public.rows import derive_group_by

        return derive_group_by(self, keys=keys, by=by)

    def distinct(self) -> "DerivedRowSource[S]":
        """Drop duplicate rows without changing the shape.

        Example:
            ```python
            unique_sites = SiteTable.row_source().distinct()
            ```
        """
        from ...service.public.rows import derive_distinct

        return derive_distinct(self)

    def order_by(
        self, *keys: OrderByKey[S], ascending: bool = True,
    ) -> "DerivedRowSource[S]":
        """Order rows by expressions, selections, or column names.

        Example:
            ```python
            ordered = SiteTable.row_source().order_by("region", "name")
            ```
        """
        from ...service.public.rows import derive_order_by

        return derive_order_by(self, *keys, ascending=ascending)

    def custom_op[Out: Shape](
        self,
        operation: "RelationOperation[S, Out]",
        **parameters: JsonValue,
    ) -> "DerivedRowSource[Out]":
        """Compose one project relation operation over this row source.

        The operation names its exact output shape and grain; ``parameters``
        are JSON values the project emitter receives with the plan.

        Example:
            ```python
            rows = Row.row_source().custom_op(count_rows)
            ```
        """
        from ...service.public.rows import derive_relation_operation

        return derive_relation_operation(self, operation, **parameters)


@dataclass(frozen=True, slots=True)
class RelationRowSource(RowSource[S], Generic[S]):
    """A row source over one named source or derived relation."""

    source: type[Shape]
    shape: type[S]
    filters: tuple[Selection[bool], ...] = ()

    @property
    def plan_dto(self) -> RowScanDTO:
        """The scan plan this relation reads."""
        from ...service.public.rows import relation_plan_dto

        return relation_plan_dto(self.source)



@dataclass(frozen=True, slots=True)
class StageRowSource(RowSource[S], Generic[S]):
    """A row source over one private stage; it is not bindable.

    A stage row source carries the same shape and scan plan as a relation row
    source, but only a derived relation that publishes the stage may read it.
    """

    source: type[Shape]
    shape: type[S]
    filters: tuple[Selection[bool], ...] = ()

    @property
    def plan_dto(self) -> RowScanDTO:
        """The scan plan this stage reads."""
        from ...service.public.rows import relation_plan_dto

        return relation_plan_dto(self.source)


@dataclass(frozen=True, slots=True)
class DerivedRowSource(RowSource[S], Generic[S]):
    """A row source derived by filtering or by the relational algebra."""

    shape: type[S]
    source: type[Shape]
    filters: tuple[Selection[bool], ...] = ()
    plan_dto: RowSourcePlanDTO | None = None



__all__ = [
    "DerivedRowSource", "GroupByKeys", "JoinHow", "OrderByKey",
    "RelationRowSource", "RowSource", "RowSourceProvider", "ShapeField",
    "StageRowSource",
]
