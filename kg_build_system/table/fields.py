"""Unified typed field declarations for tables and structs.

This module is the new declaration boundary.  It intentionally coexists with
the legacy table descriptors until the table/projection migration is complete.
Every supported logical value is declared with ``Field[T]``; descriptor access
turns table fields into typed value expressions and struct fields into typed
``PickedField`` path tokens.
"""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, get_args, get_origin, get_type_hints, overload

from .._support.naming import declaration_name, member_name
from ..annotations import Annotation, annotation_tuple
from ..expressions import (
    ArrayNullableValueExpression,
    ArrayValueExpression,
    BoolValueExpression,
    CustomDataTypeValueExpression,
    FloatValueExpression,
    IntValueExpression,
    NullableValueExpression,
    PickedField,
    StrValueExpression,
    StructNullableValueExpression,
    StructValueExpression,
    Traversal,
    ValueExpression,
    field_reference,
    wrap_expression,
)
from ..types import (
    Array,
    ArrayType,
    CustomDataType,
    LogicalType,
    Nullable,
    NullableType,
    Struct,
    StructType,
    normalize_type,
)
from .models import Table


type AuthoringDataType = (
    bool | int | float | str | CustomDataType | Struct | Array[Any] | None
)
T = TypeVar("T", bound=AuthoringDataType)


@dataclass(frozen=True, slots=True)
class FieldMetadata:
    """Portable author-facing metadata belonging to one declared field."""

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
    """A single descriptor for scalar, custom, struct, and array fields."""

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
            description=self._metadata.description,
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

    # Table-owner scalar results.
    @overload
    def __get__(self: "Field[bool]", instance: Any, owner: type[Table]) -> BoolValueExpression: ...
    @overload
    def __get__(self: "Field[int]", instance: Any, owner: type[Table]) -> IntValueExpression: ...
    @overload
    def __get__(self: "Field[float]", instance: Any, owner: type[Table]) -> FloatValueExpression: ...
    @overload
    def __get__(self: "Field[str]", instance: Any, owner: type[Table]) -> StrValueExpression: ...
    @overload
    def __get__[C: CustomDataType](self: "Field[C]", instance: Any, owner: type[Table]) -> CustomDataTypeValueExpression[C]: ...

    # Nullable table-owner scalars.
    @overload
    def __get__(self: "Field[bool | None]", instance: Any, owner: type[Table]) -> NullableValueExpression[bool, BoolValueExpression]: ...
    @overload
    def __get__(self: "Field[int | None]", instance: Any, owner: type[Table]) -> NullableValueExpression[int, IntValueExpression]: ...
    @overload
    def __get__(self: "Field[float | None]", instance: Any, owner: type[Table]) -> NullableValueExpression[float, FloatValueExpression]: ...
    @overload
    def __get__(self: "Field[str | None]", instance: Any, owner: type[Table]) -> NullableValueExpression[str, StrValueExpression]: ...
    @overload
    def __get__[C: CustomDataType](self: "Field[C | None]", instance: Any, owner: type[Table]) -> NullableValueExpression[C, CustomDataTypeValueExpression[C]]: ...

    # Arrays exposed by tables.  The expression family's second parameter is
    # inferred for common scalar and struct items; nullable items retain their
    # explicit Nullable marker internally.
    @overload
    def __get__(self: "Field[Array[bool]]", instance: Any, owner: type[Table]) -> ArrayValueExpression[bool, BoolValueExpression]: ...
    @overload
    def __get__(self: "Field[Array[int]]", instance: Any, owner: type[Table]) -> ArrayValueExpression[int, IntValueExpression]: ...
    @overload
    def __get__(self: "Field[Array[float]]", instance: Any, owner: type[Table]) -> ArrayValueExpression[float, FloatValueExpression]: ...
    @overload
    def __get__(self: "Field[Array[str]]", instance: Any, owner: type[Table]) -> ArrayValueExpression[str, StrValueExpression]: ...
    @overload
    def __get__[S: Struct](self: "Field[Array[S]]", instance: Any, owner: type[Table]) -> ArrayValueExpression[S, StructValueExpression[S]]: ...
    @overload
    def __get__(self: "Field[Array[int | None]]", instance: Any, owner: type[Table]) -> ArrayValueExpression[Nullable[int], NullableValueExpression[int, IntValueExpression]]: ...  # pyright: ignore[reportInvalidTypeArguments]
    @overload
    def __get__(self: "Field[Array[str | None]]", instance: Any, owner: type[Table]) -> ArrayValueExpression[Nullable[str], NullableValueExpression[str, StrValueExpression]]: ...  # pyright: ignore[reportInvalidTypeArguments]
    @overload
    def __get__(self: "Field[Array[int] | None]", instance: Any, owner: type[Table]) -> ArrayNullableValueExpression[int, IntValueExpression, NullableValueExpression[int, IntValueExpression]]: ...
    @overload
    def __get__(self: "Field[Array[str] | None]", instance: Any, owner: type[Table]) -> ArrayNullableValueExpression[str, StrValueExpression, NullableValueExpression[str, StrValueExpression]]: ...
    @overload
    def __get__[S: Struct](self: "Field[Array[S] | None]", instance: Any, owner: type[Table]) -> ArrayNullableValueExpression[S, StructValueExpression[S], StructNullableValueExpression[S]]: ...

    # Structs exposed by tables.
    @overload
    def __get__[S: Struct](self: "Field[S]", instance: Any, owner: type[Table]) -> StructValueExpression[S]: ...
    @overload
    def __get__[S: Struct](self: "Field[S | None]", instance: Any, owner: type[Table]) -> StructNullableValueExpression[S]: ...

    # Fields read through a Struct proxy are path tokens.  Each token carries
    # both the direct result family and the family produced when a nullable
    # parent propagates null through the selection.
    @overload
    def __get__[S: Struct](self: "Field[bool]", instance: S, owner: type[S]) -> PickedField[S, BoolValueExpression, NullableValueExpression[bool, BoolValueExpression]]: ...
    @overload
    def __get__[S: Struct](self: "Field[int]", instance: S, owner: type[S]) -> PickedField[S, IntValueExpression, NullableValueExpression[int, IntValueExpression]]: ...
    @overload
    def __get__[S: Struct](self: "Field[float]", instance: S, owner: type[S]) -> PickedField[S, FloatValueExpression, NullableValueExpression[float, FloatValueExpression]]: ...
    @overload
    def __get__[S: Struct](self: "Field[str]", instance: S, owner: type[S]) -> PickedField[S, StrValueExpression, NullableValueExpression[str, StrValueExpression]]: ...
    @overload
    def __get__[S: Struct, C: CustomDataType](self: "Field[C]", instance: S, owner: type[S]) -> PickedField[S, CustomDataTypeValueExpression[C], NullableValueExpression[C, CustomDataTypeValueExpression[C]]]: ...
    @overload
    def __get__[S: Struct](self: "Field[bool | None]", instance: S, owner: type[S]) -> PickedField[S, NullableValueExpression[bool, BoolValueExpression], NullableValueExpression[bool, BoolValueExpression]]: ...
    @overload
    def __get__[S: Struct](self: "Field[int | None]", instance: S, owner: type[S]) -> PickedField[S, NullableValueExpression[int, IntValueExpression], NullableValueExpression[int, IntValueExpression]]: ...
    @overload
    def __get__[S: Struct](self: "Field[float | None]", instance: S, owner: type[S]) -> PickedField[S, NullableValueExpression[float, FloatValueExpression], NullableValueExpression[float, FloatValueExpression]]: ...
    @overload
    def __get__[S: Struct](self: "Field[str | None]", instance: S, owner: type[S]) -> PickedField[S, NullableValueExpression[str, StrValueExpression], NullableValueExpression[str, StrValueExpression]]: ...
    @overload
    def __get__[S: Struct, C: CustomDataType](self: "Field[C | None]", instance: S, owner: type[S]) -> PickedField[S, NullableValueExpression[C, CustomDataTypeValueExpression[C]], NullableValueExpression[C, CustomDataTypeValueExpression[C]]]: ...
    @overload
    def __get__[S: Struct, Inner: Struct](self: "Field[Inner]", instance: S, owner: type[S]) -> PickedField[S, StructValueExpression[Inner], StructNullableValueExpression[Inner]]: ...
    @overload
    def __get__[S: Struct, Inner: Struct](self: "Field[Inner | None]", instance: S, owner: type[S]) -> PickedField[S, StructNullableValueExpression[Inner], StructNullableValueExpression[Inner]]: ...
    @overload
    def __get__[S: Struct](self: "Field[Array[int]]", instance: S, owner: type[S]) -> PickedField[S, ArrayValueExpression[int, IntValueExpression], ArrayNullableValueExpression[int, IntValueExpression, NullableValueExpression[int, IntValueExpression]]]: ...
    @overload
    def __get__[S: Struct](self: "Field[Array[str]]", instance: S, owner: type[S]) -> PickedField[S, ArrayValueExpression[str, StrValueExpression], ArrayNullableValueExpression[str, StrValueExpression, NullableValueExpression[str, StrValueExpression]]]: ...
    @overload
    def __get__[S: Struct, Inner: Struct](self: "Field[Array[Inner]]", instance: S, owner: type[S]) -> PickedField[S, ArrayValueExpression[Inner, StructValueExpression[Inner]], ArrayNullableValueExpression[Inner, StructValueExpression[Inner], StructNullableValueExpression[Inner]]]: ...

    # Runtime implementation.  Struct proxy access returns a path token;
    # table access returns a fully typed field-reference expression.
    def __get__(self, instance: Any, owner: type[Any] | None = None) -> Any:
        owner = owner or type(instance)
        logical_type = self._logical_type(owner)
        name = self._metadata.name
        assert name is not None
        if issubclass(owner, Struct):
            return PickedField(name, logical_type)
        if not _table_owner(owner):
            raise TypeError("Field owners must derive from Table or Struct")
        return wrap_expression(
            field_reference(
                source=_source_name(owner),
                path=(name,),
                logical_type=logical_type,
                traversals=_traversals(name, logical_type),
            )
        )


def field[T: AuthoringDataType](  # pyright: ignore[reportInvalidTypeVarUse]
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]:  # pyright: ignore[reportInvalidTypeVarUse]
    """Declare one logical field; its type is supplied by ``Field[T]``."""
    if name is not None and not name:
        raise ValueError("field names must be non-empty")
    return Field(
        FieldMetadata(
            name=name,
            description=description,
            annotations=annotation_tuple(list(annotations)),
        )
    )


def declared_fields(owner: type[Any]) -> dict[str, Field[Any]]:
    """Resolve inherited fields with ordinary Python shadowing semantics."""
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
