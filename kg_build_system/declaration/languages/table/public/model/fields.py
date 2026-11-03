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

from typing import Generic, TypeVar

from ..._private.descriptors import FieldDescriptor
from ..service.fields import computed_field, field, projection_field

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


__all__ = ["Field", "computed_field", "field", "projection_field"]
