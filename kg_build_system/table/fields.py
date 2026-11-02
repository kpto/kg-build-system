"""Unified field declarations for source records and computed records.

A ``Field`` is authoring syntax, not a compiled fact. Its metadata and logical
type are resolved once, while the declaring class is created, into
``FieldSpec`` values. Reading a field later uses that resolved spec, so a read
never calls ``get_type_hints``.

``field()`` declares source backing (a table column or source struct member);
``computed_field()`` declares expression backing (a projection output or a
computed-struct member). ``projection_field()`` is the compatibility spelling
of ``computed_field()`` used by the older projection API.
"""
from __future__ import annotations

import types as pytypes
from collections.abc import Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Generic, TypeVar, Union, get_args, get_origin, get_type_hints, overload

from .._support.interfaces import (
    attribute_docstring, declaration_name, member_name,
)
from ..annotations.interfaces import Annotation, annotation_tuple
from ..expressions.interfaces import (
    NullableDataType, SelectionUnit, Traversal, ValueExpression, ValueInput,
    as_expression, field_reference, select_expression, select_member,
    wrap_expression,
)
from ..types.interfaces import (
    Array, ArrayType, CustomDataType, Date, LogicalType, Nullable, NullableType,
    Struct, StructType, Time, Timestamp, Uuid, normalize_type,
)

if TYPE_CHECKING:
    from ..expressions.interfaces import (
        ArraySelection, NullableSelection, StructSelection, ValueSelection,
    )

T = TypeVar("T")

type AuthoringDataType = (
    bool | int | float | str | Date | Time | Timestamp | Uuid
    | CustomDataType | Struct | Array[Any]
)


@dataclass(frozen=True, slots=True)
class FieldMetadata:
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] = ()
    attribute: str = ""


@dataclass(frozen=True, slots=True)
class FieldSpec:
    """A field resolved against one declaration class."""

    attribute: str
    name: str
    descriptor: Any
    logical_type: LogicalType
    access_type: LogicalType
    description: str | None = None
    annotations: tuple[Annotation, ...] = ()
    declaration: type[Any] | None = None


def _owner_kind(owner: type[Any]) -> str | None:
    """Classify a descriptor owner as source-backed, computed, or a view."""
    from .models import ComputedStruct, Projection, Struct as SourceStruct, Table

    if issubclass(owner, (Table, SourceStruct)):
        return "source"
    if issubclass(owner, (Projection, ComputedStruct)):
        return "computed"
    if vars(owner).get("_kg_shape_view", False) or "_kg_row_source_fields" in vars(owner):
        return "view"
    return None


def _source_name(owner: type[Any]) -> str:
    spec = vars(owner).get("_kg_declaration_spec")
    if spec is not None and spec.name:
        return spec.name
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


def _nullable(logical_type: LogicalType) -> LogicalType:
    if isinstance(logical_type, NullableType):
        return logical_type
    return NullableType(logical_type)


def _declaration_from_annotation(value: Any) -> type[Any] | None:
    origin = get_origin(value)
    if origin in (Union, pytypes.UnionType):
        for item in get_args(value):
            if item is not type(None):
                found = _declaration_from_annotation(item)
                if found is not None:
                    return found
        return None
    if origin is Array:
        arguments = get_args(value)
        return _declaration_from_annotation(arguments[0]) if arguments else None
    if origin is Nullable:
        arguments = get_args(value)
        return _declaration_from_annotation(arguments[0]) if arguments else None
    if isinstance(value, type) and issubclass(value, Struct):
        return value
    return None


def _field_annotation(hints: dict[str, Any], owner: type[Any], attribute: str) -> Any:
    try:
        annotation = hints[attribute]
    except KeyError as error:
        raise TypeError(
            f"{owner.__name__}.{attribute} must have a Field[T] annotation"
        ) from error
    if get_origin(annotation) is not Field:
        raise TypeError(f"{owner.__name__}.{attribute} must have a Field[T] annotation")
    arguments = get_args(annotation)
    if len(arguments) != 1:
        raise TypeError(f"{owner.__name__}.{attribute} must have a Field[T] annotation")
    return arguments[0]


def _validate_backing(field: "Field[Any]", owner: type[Any], attribute: str, kind: str | None) -> None:
    if kind == "source" and field.expression is not None:
        raise TypeError(
            f"{owner.__name__}.{attribute} is a source field and must be "
            "declared with field(), not computed_field()"
        )
    if kind in ("computed", "view") and field.expression is None:
        constructor = "field()" if kind == "view" else "computed_field()"
        raise TypeError(
            f"{owner.__name__}.{attribute} must be declared with {constructor}"
        )


def resolve_field_specs(owner: type[Any], kind: str | None) -> tuple[FieldSpec, ...]:
    """Resolve every member of ``owner`` once, at class-creation time."""
    fields: dict[str, Field[Any]] = {}
    for base in reversed(owner.__mro__):
        for attribute, value in vars(base).items():
            if isinstance(value, Field):
                fields[attribute] = value
            elif attribute in fields:
                del fields[attribute]

    hints = get_type_hints(owner) if fields else {}
    resolved: list[FieldSpec] = []
    external: dict[str, str] = {}
    for attribute, field in fields.items():
        _validate_backing(field, owner, attribute, kind)
        annotation = None
        if field.expression is not None:
            logical_type = field.expression.logical_type
            if attribute in hints and get_origin(hints[attribute]) is Field:
                annotation = _field_annotation(hints, owner, attribute)
        else:
            annotation = _field_annotation(hints, owner, attribute)
            logical_type = normalize_type(annotation)
        declaration = (
            _declaration_from_annotation(annotation)
            if annotation is not None else None
        )
        if declaration is not None:
            from .models import Projection, Table

            if issubclass(declaration, (Table, Projection)):
                raise TypeError(
                    f"{owner.__name__}.{attribute} is a row source, not a value "
                    "record; field types must be Struct or ComputedStruct "
                    "declarations"
                )
        access_type = logical_type
        name = field.metadata.name
        if name is None:
            name = member_name(attribute)
        if name in external:
            raise TypeError(
                f"{owner.__name__} fields {external[name]!r} and {attribute!r} "
                f"share external name {name!r}"
            )
        external[name] = attribute
        resolved.append(FieldSpec(
            attribute=attribute,
            name=name,
            descriptor=field,
            logical_type=logical_type,
            access_type=access_type,
            description=field.metadata.description,
            annotations=field.metadata.annotations,
            declaration=declaration,
        ))
    return tuple(resolved)


def _spec_for(owner: type[Any]) -> tuple[FieldSpec, ...]:
    spec = vars(owner).get("_kg_declaration_spec")
    if spec is not None:
        return tuple(spec.fields)
    return resolve_field_specs(owner, _owner_kind(owner))


def _field_spec(owner: type[Any], field: "Field[Any]") -> FieldSpec | None:
    attribute = field.metadata.attribute
    for spec in _spec_for(owner):
        if spec.attribute == attribute or spec.descriptor is field:
            return spec
    return None


class Field(Generic[T]):
    """A unified field: a source selection or an expression-backed output.

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
        return self._metadata

    def __set_name__(self, owner: type[Any], attribute: str) -> None:
        if self._owner is not None and self._owner is not owner:
            raise TypeError("one Field instance may not be assigned to multiple declarations")
        self._owner = owner
        name = self._metadata.name or member_name(attribute)
        description = self._metadata.description or attribute_docstring(owner, attribute)
        self._metadata = FieldMetadata(
            name=name,
            description=description,
            annotations=self._metadata.annotations,
            attribute=attribute,
        )

    def access_type(self, owner: type[Any]) -> LogicalType:
        """The type one read yields: source-backed fields are always nullable."""
        spec = _field_spec(owner, self)
        if spec is not None:
            return spec.access_type
        if self._generated_logical_type is not None:
            return self._generated_logical_type
        if self._expression is not None:
            return self._expression.logical_type
        raise TypeError(f"{owner.__name__}.{self.metadata.attribute} has no resolved field type")

    def _logical_type(self, owner: type[Any]) -> LogicalType:
        """The declared value type, before source access adds nullability."""
        spec = _field_spec(owner, self)
        if spec is not None:
            return spec.logical_type
        if self._generated_logical_type is not None:
            return self._generated_logical_type
        if self._expression is not None:
            return self._expression.logical_type
        raise TypeError(f"{owner.__name__}.{self.metadata.attribute} has no resolved field type")

    @overload
    def __get__[I: NullableDataType](
        self: "Field[Array[I]]", instance: Any, owner: type[Any] | None = None,
    ) -> "ArraySelection[I]": ...
    @overload
    def __get__[I: NullableDataType](
        self: "Field[Array[I] | None]", instance: Any, owner: type[Any] | None = None,
    ) -> "NullableSelection[Array[I]]": ...
    @overload
    def __get__[S: Struct](
        self: "Field[S]", instance: Any, owner: type[Any] | None = None,
    ) -> "StructSelection[S]": ...
    @overload
    def __get__[S: Struct](
        self: "Field[S | None]", instance: Any, owner: type[Any] | None = None,
    ) -> "NullableSelection[S]": ...
    @overload
    def __get__[U: SelectionUnit](
        self: "Field[U]", instance: Any, owner: type[Any] | None = None,
    ) -> "ValueSelection[U]": ...
    @overload
    def __get__[U: SelectionUnit](
        self: "Field[U | None]", instance: Any, owner: type[Any] | None = None,
    ) -> "NullableSelection[U]": ...
    @overload
    def __get__(self, instance: Any, owner: type[Any] | None = None) -> Any: ...

    def __get__(self, instance: Any, owner: type[Any] | None = None) -> Any:
        if owner is None:
            if instance is None:
                raise TypeError("fields require a declaration owner")
            owner = type(instance)
        kind = _owner_kind(owner)
        spec = _field_spec(owner, self)
        name = self._metadata.name
        if name is None:
            raise TypeError("field descriptor has not been named")
        if kind == "source":
            from .models import Table

            access_type = spec.access_type if spec is not None else self.access_type(owner)
            if issubclass(owner, Table):
                return select_expression(wrap_expression(field_reference(
                    source=_source_name(owner),
                    path=(name,),
                    logical_type=access_type,
                    traversals=_traversals(name, access_type),
                )))
            return select_member(
                name, access_type,
                StructType(owner.__module__, owner.__qualname__),
            )
        if kind == "computed":
            from .models import Projection

            if issubclass(owner, Projection):
                access_type = spec.access_type if spec is not None else self.access_type(owner)
                return select_expression(wrap_expression(field_reference(
                    source=_source_name(owner),
                    path=(name,),
                    logical_type=access_type,
                    traversals=_traversals(name, access_type),
                )))
            access_type = spec.access_type if spec is not None else self.access_type(owner)
            return select_member(
                name, access_type,
                StructType(owner.__module__, owner.__qualname__),
            )
        if kind == "view":
            if self._expression is None:
                raise TypeError("shape views require expression-backed fields")
            return select_expression(self._expression)
        if self._expression is not None:
            return select_expression(self._expression)
        raise TypeError(
            "Field owners must be a Table, source Struct, Projection or ComputedStruct"
        )


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


def projection_field[T](
    value: ValueInput[T],
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]:
    """Compatibility spelling of :func:`computed_field` for old projections.

    The older API declares an unpinned ``Projection`` and marks each output with
    ``projection_field``. The backing and resolved type are identical; only the
    constructor name and its error text differ.
    """
    if name is not None and not name:
        raise ValueError("projection field names must be non-empty")
    return Field(
        as_expression(value),
        FieldMetadata(
            name=name,
            description=description,
            annotations=annotation_tuple(list(annotations)),
        ),
    )


def declared_fields(owner: type[Any]) -> dict[str, Any]:
    """The resolved member set of a declaration, resolved at class creation."""
    spec = vars(owner).get("_kg_declaration_spec")
    if spec is not None:
        return {item.attribute: item.descriptor for item in spec.fields}
    return {
        item.attribute: item.descriptor
        for item in resolve_field_specs(owner, _owner_kind(owner))
    }


__all__ = [
    "AuthoringDataType", "Field", "FieldMetadata", "FieldSpec",
    "computed_field", "declared_fields", "field", "projection_field",
    "resolve_field_specs",
]
