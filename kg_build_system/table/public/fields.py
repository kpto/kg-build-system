"""Author-facing field declarations for tables, structs and projections.

A field is written as a class attribute: ``field()`` for a source-backed member,
``computed_field()`` for an expression-backed output, and ``projection_field()``
for the older unpinned-projection spelling of ``computed_field()``.

Example:
    ```python
    from kg_build_system import Field, Table, field

    class Site(Table):
        site_id: Field[str] = field()
        parent: Field[str | None] = field(name="parent_site")
    ```
"""
from __future__ import annotations

from collections.abc import Sequence
from typing import Generic, TypeVar

from ...annotations.internal import Annotation
from ...expressions.internal import ValueInput
from .._private.descriptors import (
    AuthoringDataType,
    FieldDescriptor,
    make_computed_field,
    make_field,
    make_projection_field,
)

T = TypeVar("T")


class Field(FieldDescriptor[T], Generic[T]):
    """A unified field: a source selection or an expression-backed output.

    The descriptor is immutable in use. The one mutable step is ``__set_name__``
    while the declaring class is being created; after that, resolved types live
    in the declaration's frozen ``DeclarationSpec``.

    Example:
        ```python
        from kg_build_system import Field, Table, field

        class Site(Table):
            site_id: Field[str] = field()
        ```
    """

    __slots__ = ()


def field[T: AuthoringDataType](  # pyright: ignore[reportInvalidTypeVarUse]
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]:  # pyright: ignore[reportInvalidTypeVarUse]
    """Declare a source-backed field: a table column or source struct member.

    A source field is read as ``Field[T]`` when present and
    ``Field[T | None]`` when the annotation is nullable. It has no expression
    backing.

    Example:
        ```python
        from kg_build_system import Field, Table, field

        class Site(Table):
            site_id: Field[str] = field()
            parent: Field[str | None] = field(name="parent_site")
        ```
    """
    return make_field(
        name=name, description=description, annotations=annotations,
    )


def computed_field[T](
    value: ValueInput[T],
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]:
    """Declare an expression-backed field: an output or computed member.

    The expression determines the field's logical type. ``value`` may be a
    selection or a value expression.

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


def projection_field[T](
    value: ValueInput[T],
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]:
    """Compatibility spelling of :func:`computed_field` for old projections.

    An unpinned ``Projection`` declares each output with ``projection_field``.
    The backing and resolved type are identical to ``computed_field``.

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


__all__ = ["Field", "computed_field", "field", "projection_field"]
