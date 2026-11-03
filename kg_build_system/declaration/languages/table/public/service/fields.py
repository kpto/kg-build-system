"""Authoring function wrappers for table fields."""
from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, TypeVar

from kg_build_system.declaration.foundations.annotations.internal import Annotation
from kg_build_system.declaration.foundations.expressions.public import ValueInput
from ..._private.descriptors import (
    AuthoringDataType,
    make_computed_field,
    make_field,
    make_projection_field,
)

if TYPE_CHECKING:
    from ..model.fields import Field

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
    return make_field(
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
    return make_computed_field(
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
    return make_projection_field(
        value, name=name, description=description, annotations=annotations,
    )


__all__ = ["computed_field", "field", "projection_field"]
