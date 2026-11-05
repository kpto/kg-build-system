"""Authoring function wrappers for table fields."""
from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from kg_build_system.distribution.languages.annotations.model.public import (
    Annotation,
)
from ...model.public.fields import DeclaredValue
from ..internal.fields import computed_field as computed_field_impl
from ..internal.fields import field as field_impl

if TYPE_CHECKING:
    from kg_build_system.distribution.languages.expressions.model.public import Selection
    from ...model.public.fields import Field


def field[T: DeclaredValue](  # pyright: ignore[reportInvalidTypeVarUse]
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


def computed_field[T: DeclaredValue](
    value: "Selection[T]",
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
            label = computed_field(SiteTable.name.alter_rows().drop_null())
        ```
    """
    return computed_field_impl(
        value, name=name, description=description, annotations=annotations,
    )


__all__ = ["computed_field", "field"]
