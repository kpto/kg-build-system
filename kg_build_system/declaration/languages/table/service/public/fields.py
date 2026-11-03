"""Authoring function wrappers for table fields."""
from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, TypeVar

from kg_build_system.declaration.foundations.annotations.model.public import (
    Annotation,
)
from kg_build_system.declaration.foundations.expressions.model.public import (
    ValueInput,
)
from ...model.public.fields import AuthoringDataType
from ..internal.fields import computed_field as computed_field_impl
from ..internal.fields import field as field_impl
from ..internal.fields import projection_field as projection_field_impl

if TYPE_CHECKING:
    from ...model.public.fields import Field

T = TypeVar("T")


def field[T: AuthoringDataType](  # pyright: ignore[reportInvalidTypeVarUse]
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> "Field[T]":  # pyright: ignore[reportInvalidTypeVarUse]
    """Declare a source-backed field: a table column or source struct member.

    Example:
        ```python
        from kg_build_system import Field, Table, field

        class Site(Table):
            site_id: Field[str] = field()
        ```
    """
    return field_impl(
        name=name, description=description, annotations=annotations,
    )


def computed_field[T](  # pyright: ignore[reportInvalidTypeVarUse]
    value: ValueInput[T],
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> "Field[T]":
    """Declare an expression-backed field: an output or computed member.

    Example:
        ```python
        from kg_build_system import Projection, computed_field

        class SiteLabels(Projection(SiteTable.row_source())):
            label = computed_field(SiteTable.name)
        ```
    """
    return computed_field_impl(
        value, name=name, description=description, annotations=annotations,
    )


def projection_field[T](  # pyright: ignore[reportInvalidTypeVarUse]
    value: ValueInput[T],
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> "Field[T]":
    """Declare the older unpinned spelling of :func:`computed_field`.

    Example:
        ```python
        from kg_build_system import Projection, projection_field

        class SiteLabels(Projection):
            label = projection_field(SiteTable.name)
        ```
    """
    return projection_field_impl(
        value, name=name, description=description, annotations=annotations,
    )


__all__ = ["computed_field", "field", "projection_field"]
