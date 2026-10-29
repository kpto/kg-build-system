"""Unified field declarations for source records and computed records."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar, get_args, get_origin, get_type_hints, overload

from .._support.docstrings import attribute_docstring
from .._support.naming import declaration_name, member_name
from ..annotations import Annotation, annotation_tuple
from ..expressions import (
    ArraySelection, NullableDataType, NullableSelection, SelectionUnit,
    StructSelection, Traversal, ValueExpression, ValueInput, ValueSelection,
    as_expression, field_reference, select_expression, select_member, wrap_expression,
)
from ..types import (
    Array, ArrayType, CustomDataType, Date, LogicalType, Nullable, NullableType,
    Struct, StructType, Time, Timestamp, Uuid, normalize_type,
)

if TYPE_CHECKING:
    from .models import ComputedStruct, Projection, Struct as SourceStruct, Table


type AuthoringDataType = (
    bool | int | float | str | Date | Time | Timestamp | Uuid
    | CustomDataType | Struct | Array[Any]
)
T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class FieldMetadata:
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] = ()
    attribute: str = ""


def _owner_kind(owner: type[Any]) -> str | None:
    """Classify a descriptor owner as source-backed, computed, or a view.

    A mixin that is not yet mixed into a concrete declaration has no kind; the
    final declaration validates it through :func:`declared_fields`.
    """
    from .models import ComputedStruct, Projection, Struct as SourceStruct, Table

    if issubclass(owner, (Table, SourceStruct)):
        return "source"
    if issubclass(owner, (Projection, ComputedStruct)):
        return "computed"
    if vars(owner).get("_kg_shape_view", False):
        return "view"
    return None


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
    """A unified field: a source selection or an expression-backed output.

    ``field()`` declares source backing (a table column or a source struct
    member). ``computed_field(value)`` declares expression backing (a
    projection output or a computed struct member). Reading the descriptor
    returns the right selection for its owner: a source field is always
    nullable on access, while a computed field carries its expression's type.
    """

    __slots__ = ("_expression", "_metadata", "_owner")

    def __init__(
        self,
        expression: ValueExpression[T] | None = None,
        metadata: FieldMetadata = FieldMetadata(),
    ) -> None:
        self._expression = expression
        self._metadata = metadata
        self._owner: type[Any] | None = None

    @property
    def expression(self) -> ValueExpression[T] | None:
        """The implementation of a computed field; declared fields have none."""
        return self._expression

    @property
    def metadata(self) -> FieldMetadata:
        return self._metadata

    def _validate_owner(self, owner: type[Any], attribute: str, kind: str | None) -> None:
        if kind == "source" and self._expression is not None:
            raise TypeError(
                f"{owner.__name__}.{attribute} is a source field and must be "
                "declared with field(), not computed_field()"
            )
        if kind in ("computed", "view") and self._expression is None:
            constructor = "field()" if kind == "view" else "computed_field()"
            raise TypeError(
                f"{owner.__name__}.{attribute} must be declared with {constructor}"
            )

    def __set_name__(self, owner: type[Any], attribute: str) -> None:
        if self._owner is not None and self._owner is not owner:
            raise TypeError("one Field instance may not be assigned to multiple declarations")
        self._owner = owner
        self._validate_owner(owner, attribute, _owner_kind(owner))
        self._metadata = FieldMetadata(
            name=self._metadata.name or member_name(attribute),
            # An explicit description wins; otherwise a documentation string
            # written directly below the field describes it.
            description=self._metadata.description
            or attribute_docstring(owner, attribute),
            annotations=self._metadata.annotations,
            attribute=attribute,
        )

    def access_type(self, owner: type[Any]) -> LogicalType:
        """The type one read yields: source-backed fields are always nullable."""
        logical_type = self._logical_type(owner)
        if self._expression is not None or _owner_kind(owner) in ("computed", "view"):
            return logical_type
        if isinstance(logical_type, NullableType):
            return logical_type
        return NullableType(logical_type)

    def _logical_type(self, owner: type[Any]) -> LogicalType:
        if self._expression is not None:
            return self._expression.logical_type
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
        logical_type = normalize_type(arguments[0])
        # A source declaration names the value it holds. Nullability on access
        # is the owner kind's business, so a top-level ``T | None`` is stripped;
        # array item nullability remains a fact about the value.
        if isinstance(logical_type, NullableType):
            return logical_type.value
        return logical_type

    @overload
    def __get__[U: SelectionUnit](
        self: "Field[U | None]", instance: Any, owner: type[Table] | type[SourceStruct],
    ) -> NullableSelection[U]: ...
    @overload
    def __get__[S: Struct](
        self: "Field[S | None]", instance: Any, owner: type[Table] | type[SourceStruct],
    ) -> NullableSelection[S]: ...
    @overload
    def __get__[I: NullableDataType](
        self: "Field[Array[I] | None]", instance: Any, owner: type[Table] | type[SourceStruct],
    ) -> NullableSelection[Array[I]]: ...
    @overload
    def __get__[U: SelectionUnit](
        self: "Field[Array[U | None]]", instance: Any, owner: type[Table] | type[SourceStruct],
    ) -> NullableSelection[Array[Nullable[U]]]: ...
    @overload
    def __get__[S: Struct](
        self: "Field[Array[S | None]]", instance: Any, owner: type[Table] | type[SourceStruct],
    ) -> NullableSelection[Array[Nullable[S]]]: ...
    @overload
    def __get__[U: SelectionUnit](
        self: "Field[Array[U | None] | None]", instance: Any, owner: type[Table] | type[SourceStruct],
    ) -> NullableSelection[Array[Nullable[U]]]: ...
    @overload
    def __get__[S: Struct](
        self: "Field[Array[S | None] | None]", instance: Any, owner: type[Table] | type[SourceStruct],
    ) -> NullableSelection[Array[Nullable[S]]]: ...
    @overload
    def __get__[U: AuthoringDataType](
        self: "Field[U]", instance: Any, owner: type[Table] | type[SourceStruct],
    ) -> NullableSelection[U]: ...

    @overload
    def __get__[U: SelectionUnit](
        self: "Field[U]", instance: Any, owner: type[Projection] | type[ComputedStruct],
    ) -> ValueSelection[U]: ...
    @overload
    def __get__[U: SelectionUnit](
        self: "Field[Nullable[U]]", instance: Any, owner: type[Projection] | type[ComputedStruct],
    ) -> NullableSelection[U]: ...
    @overload
    def __get__[I: NullableDataType](
        self: "Field[Array[I]]", instance: Any, owner: type[Projection] | type[ComputedStruct],
    ) -> ArraySelection[I]: ...
    @overload
    def __get__[I: NullableDataType](
        self: "Field[Nullable[Array[I]]]", instance: Any, owner: type[Projection] | type[ComputedStruct],
    ) -> NullableSelection[Array[I]]: ...
    @overload
    def __get__[S: Struct](
        self: "Field[S]", instance: Any, owner: type[Projection] | type[ComputedStruct],
    ) -> StructSelection[S]: ...
    @overload
    def __get__[S: Struct](
        self: "Field[Nullable[S]]", instance: Any, owner: type[Projection] | type[ComputedStruct],
    ) -> NullableSelection[S]: ...

    @overload
    def __get__(self, instance: Any, owner: type[Any] | None = None) -> ValueSelection[Any]: ...

    def __get__(self, instance: Any, owner: type[Any] | None = None) -> Any:
        owner = owner or type(instance)
        kind = _owner_kind(owner)
        name = self._metadata.name
        assert name is not None
        if kind == "source":
            logical_type = self._logical_type(owner)
            nullable_type = (
                logical_type if isinstance(logical_type, NullableType)
                else NullableType(logical_type)
            )
            from .models import Table

            if issubclass(owner, Table):
                return select_expression(wrap_expression(field_reference(
                    source=_source_name(owner),
                    path=(name,),
                    logical_type=nullable_type,
                    traversals=_traversals(name, nullable_type),
                )))
            return select_member(
                name, nullable_type,
                StructType(owner.__module__, owner.__qualname__),
            )
        if kind == "computed":
            expression = self._expression
            if expression is None:
                raise TypeError("computed fields require an expression")
            from .models import Projection

            if issubclass(owner, Projection):
                source = getattr(owner, "_projection_name", None)
                if not isinstance(source, str) or not source:
                    raise TypeError("projection fields require a final Projection declaration")
                return select_expression(wrap_expression(field_reference(
                    source=source,
                    path=(name,),
                    logical_type=expression.logical_type,
                    traversals=_traversals(name, expression.logical_type),
                )))
            return select_member(
                name, expression.logical_type,
                StructType(owner.__module__, owner.__qualname__),
            )
        if kind == "view":
            expression = self._expression
            if expression is None:
                raise TypeError("shape views require expression-backed fields")
            return select_expression(expression)
        raise TypeError("Field owners must be a Table, source Struct, Projection or ComputedStruct")


def field[T: AuthoringDataType](  # pyright: ignore[reportInvalidTypeVarUse]
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]:  # pyright: ignore[reportInvalidTypeVarUse]
    """Declare a source-backed field: a table column or source struct member."""
    if name is not None and not name:
        raise ValueError("field names must be non-empty")
    return Field(metadata=FieldMetadata(
        name=name,
        description=description,
        annotations=annotation_tuple(list(annotations)),
    ))


def computed_field[T](
    value: ValueInput[T],
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]:
    """Declare an expression-backed field: a projection output or computed member."""
    if name is not None and not name:
        raise ValueError("computed field names must be non-empty")
    return Field(
        as_expression(value),
        FieldMetadata(
            name=name,
            description=description,
            annotations=annotation_tuple(list(annotations)),
        ),
    )


def declared_fields(owner: type[Any]) -> dict[str, Field[Any]]:
    result: dict[str, Field[Any]] = {}
    for base in reversed(owner.__mro__):
        for attribute, value in vars(base).items():
            if isinstance(value, Field):
                result[attribute] = value
            elif attribute in result:
                del result[attribute]
    kind = _owner_kind(owner)
    external: dict[str, str] = {}
    for attribute, value in result.items():
        value._validate_owner(owner, attribute, kind)
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


__all__ = [
    "AuthoringDataType", "Field", "FieldMetadata", "computed_field",
    "declared_fields", "field",
]
