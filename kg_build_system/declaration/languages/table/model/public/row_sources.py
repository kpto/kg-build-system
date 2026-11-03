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

    class ActiveSiteLabels(active.projection_base()):
        label = computed_field(SiteTable.name)
    ```
"""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Generic, Literal, TypeVar

from kg_build_system.declaration.foundations.expressions.model.public import (
    BoolExpression,
)
from kg_build_system.kernel.model.public.types import Shape
from ..internal.dto.blueprint_dto import RowScanDTO, RowSourcePlanDTO
from .shapes import ShapeField

S = TypeVar("S", bound=Shape)
JoinHow = Literal["inner", "left", "right", "full"]


class RowSource(Generic[S]):
    """A source of rows whose shape is ``S``; declarations satisfy it by subclassing."""

    shape: type[S]

    def where(self, predicate: Callable[[S], BoolExpression]) -> "DerivedRowSource[S]":
        """Keep rows whose predicate is true.

        The predicate receives a symbolic shape instance and must return a
        ``BoolExpression``.

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

    def union(self, other: Any, *, all: bool = True) -> "DerivedRowSource[S]":
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

    def join(
        self, other: Any, *, on: Callable[[Any, Any], tuple[Any, Any]],
        how: JoinHow = "inner",
    ) -> "DerivedRowSource[Any]":
        """Equi-join two sources on one expression from each side.

        ``on`` receives one shape instance per side and returns the two key
        selections. A null key never matches in any join mode.

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

        return derive_join(self, other, on=on, how=how)

    def group_by(self, *, by: Callable[[S], Any]) -> "DerivedRowSource[Any]":
        """Group rows by named key expressions; null keys are dropped.

        Example:
            ```python
            by_region = SiteTable.row_source().group_by(
                by=lambda site: {"region": site.region},
            )
            ```
        """
        from ...service.public.rows import derive_group_by

        return derive_group_by(self, by=by)

    def distinct(self) -> "DerivedRowSource[S]":
        """Drop duplicate rows without changing the shape.

        Example:
            ```python
            unique_sites = SiteTable.row_source().distinct()
            ```
        """
        from ...service.public.rows import derive_distinct

        return derive_distinct(self)

    def order_by(self, *keys: Any, ascending: bool = True) -> "DerivedRowSource[S]":
        """Order rows by expressions, selections, or column names.

        Example:
            ```python
            ordered = SiteTable.row_source().order_by("region", "name")
            ```
        """
        from ...service.public.rows import derive_order_by

        return derive_order_by(self, *keys, ascending=ascending)


@dataclass(frozen=True, slots=True)
class RelationRowSource(RowSource[S], Generic[S]):
    """A row source over one named table or projection relation."""

    source: type[Any]
    shape: type[S]
    filters: tuple[BoolExpression, ...] = ()

    @property
    def plan_dto(self) -> RowScanDTO:
        """The scan plan this relation reads."""
        from ...service.public.rows import relation_plan_dto

        return relation_plan_dto(self.source)

    def projection_base(self) -> type:
        """Return a projection base over this relation.

        Example:
            ```python
            from kg_build_system import computed_field

            base = SiteTable.row_source().projection_base()

            class SiteLabels(base):
                label = computed_field(SiteTable.name)
            ```
        """
        from ...service.public.rows import projection_base

        return projection_base(self)


@dataclass(frozen=True, slots=True)
class DerivedRowSource(RowSource[S], Generic[S]):
    """A row source derived by filtering or by the relational algebra."""

    shape: type[S]
    source: type[Any]
    filters: tuple[BoolExpression, ...] = ()
    plan_dto: RowSourcePlanDTO | None = None

    def projection_base(self) -> type:
        """Return a projection base over this derived row source.

        Example:
            ```python
            from kg_build_system import computed_field

            active = SiteTable.row_source().where(
                lambda site: site.name.alter_rows().drop_null()
                .expression.equals("Depot")
            )
            base = active.projection_base()

            class ActiveSiteLabels(base):
                label = computed_field(SiteTable.name)
            ```
        """
        from ...service.public.rows import projection_base

        return projection_base(self)


__all__ = [
    "DerivedRowSource", "RelationRowSource", "RowSource", "ShapeField",
    "JoinHow",
]
