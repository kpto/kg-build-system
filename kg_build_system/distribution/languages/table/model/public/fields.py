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

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar, overload

from kg_build_system.distribution.languages.annotations.model.public import (
    Annotation,
)
from kg_build_system.distribution.languages.expressions.model.public import (
    NullableDataType, SelectionUnit, ValueExpression, ValueInput,
)
from kg_build_system.kernel.model.public.types import Array, CustomDataType, Date, Struct, Time, Timestamp, Uuid

if TYPE_CHECKING:
    from kg_build_system.distribution.languages.expressions.model.public import (
        ArraySelection, NullableSelection, StructSelection, ValueSelection,
    )
    from kg_build_system.kernel.model.public.types import LogicalType

T = TypeVar("T")

type AuthoringDataType = (
    bool | int | float | str | Date | Time | Timestamp | Uuid
    | CustomDataType | Struct | Array[Any]
)


@dataclass(frozen=True, slots=True)
class FieldMetadata:
    """The name, description and annotations declared on one field."""

    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] = ()
    attribute: str = ""


class FieldDescriptor(Generic[T]):
    """The descriptor behind a declared ``Field``.

    The descriptor is immutable in use. The one mutable step is ``__set_name__``
    while the declaring class is being created; after that, resolved types live
    in the declaration's frozen ``DeclarationSpec``.
    """

    __slots__ = (
        "_expression", "_metadata", "_owner", "_generated_logical_type",
    )

    def __init__(
        self,
        expression: ValueExpression[T] | None = None,
        metadata: FieldMetadata = FieldMetadata(),
        *,
        generated_logical_type: LogicalType | None = None,
    ) -> None:
        self._expression = expression
        self._metadata = metadata
        self._owner: type[Any] | None = None
        self._generated_logical_type = generated_logical_type

    @property
    def expression(self) -> ValueExpression[T] | None:
        """The implementation of a computed field; source fields have none."""
        return self._expression

    @property
    def metadata(self) -> FieldMetadata:
        """The name, description and annotations declared on this field."""
        return self._metadata

    def __set_name__(self, owner: type[Any], attribute: str) -> None:
        from ...service._private.descriptors import field_set_name

        field_set_name(self, owner, attribute)

    def access_type(self, owner: type[Any]) -> LogicalType:
        """The type one read yields for ``owner``.

        Example:
            ```python
            from kg_build_system import Field, Table, field
            class Row(Table):
                text: Field[str] = field()
            Row.__dict__["text"].access_type(Row)
            ```
        """
        from ...service._private.descriptors import field_access_type

        return field_access_type(self, owner)

    @overload
    def __get__[I: NullableDataType](
        self: "FieldDescriptor[Array[I]]", instance: Any, owner: type[Any] | None = None,
    ) -> "ArraySelection[I]": ...
    @overload
    def __get__[I: NullableDataType](
        self: "FieldDescriptor[Array[I] | None]", instance: Any, owner: type[Any] | None = None,
    ) -> "NullableSelection[Array[I]]": ...
    @overload
    def __get__[S: Struct](
        self: "FieldDescriptor[S]", instance: Any, owner: type[Any] | None = None,
    ) -> "StructSelection[S]": ...
    @overload
    def __get__[S: Struct](
        self: "FieldDescriptor[S | None]", instance: Any, owner: type[Any] | None = None,
    ) -> "NullableSelection[S]": ...
    @overload
    def __get__[U: SelectionUnit](
        self: "FieldDescriptor[U]", instance: Any, owner: type[Any] | None = None,
    ) -> "ValueSelection[U]": ...
    @overload
    def __get__[U: SelectionUnit](
        self: "FieldDescriptor[U | None]", instance: Any, owner: type[Any] | None = None,
    ) -> "NullableSelection[U]": ...
    @overload
    def __get__(self, instance: Any, owner: type[Any] | None = None) -> Any: ...

    def __get__(self, instance: Any, owner: type[Any] | None = None) -> Any:
        from ...service._private.descriptors import field_get

        return field_get(self, instance, owner)


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


__all__ = [
    "AuthoringDataType", "Field", "FieldDescriptor", "FieldMetadata",
]
