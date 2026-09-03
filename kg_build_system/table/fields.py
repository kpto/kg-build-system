"""Unified field declarations producing shape-specialized selections."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, get_args, get_origin, get_type_hints, overload

from .._support.docstrings import attribute_docstring
from .._support.naming import declaration_name, member_name
from ..annotations import Annotation, annotation_tuple
from ..expressions import (
    ArraySelection, NullableDataType, NullableSelection, SelectionUnit,
    StructSelection, Traversal, ValueSelection, field_reference, select_expression,
    select_member, wrap_expression,
)
from ..types import (
    Array, ArrayType, CustomDataType, Date, LogicalType, Nullable, NullableType, Struct,
    StructType, Time, Timestamp, Uuid, normalize_type,
)
from .models import Table


type AuthoringDataType = (
    bool | int | float | str | Date | Time | Timestamp | Uuid
    | CustomDataType | Struct | Array[Any] | None
)
T = TypeVar("T", bound=AuthoringDataType)


@dataclass(frozen=True, slots=True)
class FieldMetadata:
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] = ()
    attribute: str = ""


def _table_owner(owner: type[Any]) -> bool:
    return issubclass(owner, Table)


def _source_name(owner: type[Any]) -> str:
    configured = getattr(owner, "_table_name", None)
    if isinstance(configured, str) and configured:
        return configured
    return declaration_name(owner.__name__, suffixes=("Table",))


def _traversals(name: str, logical_type: LogicalType) -> tuple[Traversal, ...]:
    base = logical_type.value if isinstance(logical_type, NullableType) else logical_type
    if isinstance(base, StructType):
        return (Traversal("struct", (name,)),)
    if isinstance(base, ArrayType):
        return (Traversal("array", (name,)),)
    return ()


class Field(Generic[T]):
    """A logical field whose access returns a selection, never a calculation."""

    __slots__ = ("_metadata", "_owner")

    def __init__(self, metadata: FieldMetadata = FieldMetadata()) -> None:
        self._metadata = metadata
        self._owner: type[Any] | None = None

    @property
    def metadata(self) -> FieldMetadata:
        return self._metadata

    def __set_name__(self, owner: type[Any], attribute: str) -> None:
        if self._owner is not None and self._owner is not owner:
            raise TypeError("one Field instance may not be assigned to multiple declarations")
        self._owner = owner
        self._metadata = FieldMetadata(
            name=self._metadata.name or member_name(attribute),
            # An explicit description wins; otherwise a documentation string
            # written directly below the field describes it.
            description=self._metadata.description
            or attribute_docstring(owner, attribute),
            annotations=self._metadata.annotations,
            attribute=attribute,
        )

    def _logical_type(self, owner: type[Any]) -> LogicalType:
        attribute = self._metadata.attribute
        try:
            annotation = get_type_hints(owner)[attribute]
        except KeyError as error:
            raise TypeError(f"{owner.__name__}.{attribute} must have a Field[T] annotation") from error
        if get_origin(annotation) is not Field:
            raise TypeError(f"{owner.__name__}.{attribute} must have a Field[T] annotation")
        arguments = get_args(annotation)
        if len(arguments) != 1:
            raise TypeError(f"{owner.__name__}.{attribute} must have a Field[T] annotation")
        return normalize_type(arguments[0])

    @overload
    def __get__[U: SelectionUnit](self: "Field[U]", instance: Any, owner: type[Struct]) -> ValueSelection[U]: ...
    @overload
    def __get__[U: SelectionUnit](self: "Field[U | None]", instance: Any, owner: type[Struct]) -> NullableSelection[U]: ...
    @overload
    def __get__[I: NullableDataType](self: "Field[Array[I]]", instance: Any, owner: type[Struct]) -> ArraySelection[I]: ...
    @overload
    def __get__[U: SelectionUnit](self: "Field[Array[U | None]]", instance: Any, owner: type[Struct]) -> ArraySelection[Nullable[U]]: ...  # pyright: ignore[reportInvalidTypeArguments]
    @overload
    def __get__[S: Struct](self: "Field[Array[S | None]]", instance: Any, owner: type[Struct]) -> ArraySelection[Nullable[S]]: ...  # pyright: ignore[reportInvalidTypeArguments]
    @overload
    def __get__[I: NullableDataType](self: "Field[Array[I] | None]", instance: Any, owner: type[Struct]) -> NullableSelection[Array[I]]: ...
    @overload
    def __get__[U: SelectionUnit](self: "Field[Array[U | None] | None]", instance: Any, owner: type[Struct]) -> NullableSelection[Array[Nullable[U]]]: ...  # pyright: ignore[reportInvalidTypeArguments]
    @overload
    def __get__[S: Struct](self: "Field[Array[S | None] | None]", instance: Any, owner: type[Struct]) -> NullableSelection[Array[Nullable[S]]]: ...  # pyright: ignore[reportInvalidTypeArguments]
    @overload
    def __get__[S: Struct](self: "Field[S]", instance: Any, owner: type[Struct]) -> StructSelection[S]: ...
    @overload
    def __get__[S: Struct](self: "Field[S | None]", instance: Any, owner: type[Struct]) -> NullableSelection[S]: ...

    def __get__(self, instance: Any, owner: type[Any] | None = None) -> ValueSelection[Any]:
        owner = owner or type(instance)
        logical_type = self._logical_type(owner)
        name = self._metadata.name
        assert name is not None
        if _table_owner(owner):
            return select_expression(wrap_expression(field_reference(
                source=_source_name(owner),
                path=(name,),
                logical_type=logical_type,
                traversals=_traversals(name, logical_type),
            )))
        if issubclass(owner, Struct):
            return select_member(
                name, logical_type, StructType(owner.__module__, owner.__qualname__)
            )
        raise TypeError("Field owners must derive from Table or Struct")


def field[T: AuthoringDataType](  # pyright: ignore[reportInvalidTypeVarUse]
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]:  # pyright: ignore[reportInvalidTypeVarUse]
    if name is not None and not name:
        raise ValueError("field names must be non-empty")
    return Field(FieldMetadata(
        name=name,
        description=description,
        annotations=annotation_tuple(list(annotations)),
    ))


def declared_fields(owner: type[Any]) -> dict[str, Field[Any]]:
    result: dict[str, Field[Any]] = {}
    for base in reversed(owner.__mro__):
        for attribute, value in vars(base).items():
            if isinstance(value, Field):
                result[attribute] = value
            elif attribute in result:
                del result[attribute]
    external: dict[str, str] = {}
    for attribute, value in result.items():
        value._logical_type(owner)
        name = value.metadata.name
        assert name is not None
        if name in external:
            raise TypeError(
                f"{owner.__name__} fields {external[name]!r} and {attribute!r} "
                f"share external name {name!r}"
            )
        external[name] = attribute
    return result


__all__ = ["AuthoringDataType", "Field", "FieldMetadata", "declared_fields", "field"]
