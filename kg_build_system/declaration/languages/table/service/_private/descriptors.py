"""Field descriptor mechanics and resolution into frozen ``FieldSpec`` values."""
from __future__ import annotations

import types as pytypes
from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, TypeVar, Union, get_args, get_origin, get_type_hints

from .docstrings import attribute_docstring
from .naming import declaration_name, member_name
from kg_build_system.declaration.foundations.annotations.model.public import Annotation; from kg_build_system.declaration.foundations.annotations.service.internal import annotation_tuple
from kg_build_system.declaration.foundations.expressions.model.internal import Traversal; from kg_build_system.declaration.foundations.expressions.service.internal import field_reference
from kg_build_system.declaration.foundations.expressions.model.public import NullableDataType, SelectionUnit, ValueExpression, ValueInput; from kg_build_system.declaration.foundations.expressions.service.internal import as_expression, select_expression, select_member, wrap_expression
from kg_build_system.kernel.model.public.types import Array, ArrayType, LogicalType, Nullable, NullableType, Struct, StructType; from kg_build_system.kernel.service.internal.types import normalize_type

if TYPE_CHECKING:
    from kg_build_system.declaration.foundations.expressions.model.public import ArraySelection, NullableSelection, StructSelection, ValueSelection

from ...model.internal.model.fields import FieldSpec
from ...model.public.fields import (
    AuthoringDataType, Field, FieldDescriptor, FieldMetadata,
)

T = TypeVar("T")


def make_field[T: AuthoringDataType](  # pyright: ignore[reportInvalidTypeVarUse]
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]:  # pyright: ignore[reportInvalidTypeVarUse]
    """Create a source-backed field descriptor; an empty name is rejected."""
    if name is not None and not name:
        raise ValueError("field names must be non-empty")
    return Field(metadata=FieldMetadata(
        name=name,
        description=description,
        annotations=annotation_tuple(list(annotations)),
    ))


def make_computed_field[T](
    value: ValueInput[T],
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]:
    """Create an expression-backed field descriptor; an empty name is rejected."""
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


def make_projection_field[T](
    value: ValueInput[T],
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> Field[T]:
    """Create the old-projection spelling of an expression-backed field."""
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


def _owner_kind(owner: type[Any]) -> str | None:
    """Classify a descriptor owner as source-backed, computed, or a view."""
    from ...model.public.declarations import ComputedStruct, Projection, Struct as SourceStruct, Table

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


def _validate_backing(
    field: "FieldDescriptor[Any]", owner: type[Any], attribute: str, kind: str | None,
) -> None:
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
    fields: dict[str, FieldDescriptor[Any]] = {}
    for base in reversed(owner.__mro__):
        for attribute, value in vars(base).items():
            if isinstance(value, FieldDescriptor):
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
            from ...model.public.declarations import Projection, Table

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


def _field_spec(
    owner: type[Any], field: "FieldDescriptor[Any]",
) -> FieldSpec | None:
    attribute = field.metadata.attribute
    for spec in _spec_for(owner):
        if spec.attribute == attribute or spec.descriptor is field:
            return spec
    return None


def field_set_name(
    field: FieldDescriptor[Any], owner: type[Any], attribute: str,
) -> None:
    """Resolve the descriptor's name and documentation at class creation."""
    if field._owner is not None and field._owner is not owner:
        raise TypeError("one Field instance may not be assigned to multiple declarations")
    field._owner = owner
    name = field._metadata.name or member_name(attribute)
    description = field._metadata.description or attribute_docstring(owner, attribute)
    field._metadata = FieldMetadata(
        name=name,
        description=description,
        annotations=field._metadata.annotations,
        attribute=attribute,
    )


def field_access_type(
    field: FieldDescriptor[Any], owner: type[Any],
) -> LogicalType:
    """The type one read yields for ``owner``."""
    spec = _field_spec(owner, field)
    if spec is not None:
        return spec.access_type
    if field._generated_logical_type is not None:
        return field._generated_logical_type
    if field._expression is not None:
        return field._expression.logical_type
    raise TypeError(f"{owner.__name__}.{field.metadata.attribute} has no resolved field type")


def field_logical_type(
    field: FieldDescriptor[Any], owner: type[Any],
) -> LogicalType:
    """The declared value type, before source access adds nullability."""
    spec = _field_spec(owner, field)
    if spec is not None:
        return spec.logical_type
    if field._generated_logical_type is not None:
        return field._generated_logical_type
    if field._expression is not None:
        return field._expression.logical_type
    raise TypeError(f"{owner.__name__}.{field.metadata.attribute} has no resolved field type")


def field_get(
    field: FieldDescriptor[Any], instance: Any, owner: type[Any] | None = None,
) -> Any:
    """Evaluate one descriptor read against its declaration owner."""
    if owner is None:
        if instance is None:
            raise TypeError("fields require a declaration owner")
        owner = type(instance)
    kind = _owner_kind(owner)
    spec = _field_spec(owner, field)
    name = field._metadata.name
    if name is None:
        raise TypeError("field descriptor has not been named")
    if kind == "source":
        from ...model.public.declarations import Table

        access_type = (
            spec.access_type if spec is not None else field_access_type(field, owner)
        )
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
        from ...model.public.declarations import Projection

        if issubclass(owner, Projection):
            access_type = (
                spec.access_type if spec is not None else field_access_type(field, owner)
            )
            return select_expression(wrap_expression(field_reference(
                source=_source_name(owner),
                path=(name,),
                logical_type=access_type,
                traversals=_traversals(name, access_type),
            )))
        access_type = (
            spec.access_type if spec is not None else field_access_type(field, owner)
        )
        return select_member(
            name, access_type,
            StructType(owner.__module__, owner.__qualname__),
        )
    if kind == "view":
        if field._expression is None:
            raise TypeError("shape views require expression-backed fields")
        return select_expression(field._expression)
    if field._expression is not None:
        return select_expression(field._expression)
    raise TypeError(
        "Field owners must be a Table, source Struct, Projection or ComputedStruct"
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
    "AuthoringDataType", "FieldDescriptor", "FieldMetadata", "FieldSpec",
    "declared_fields", "field_access_type", "field_get", "field_logical_type",
    "field_set_name", "make_computed_field", "make_field",
    "make_projection_field", "resolve_field_specs",
]
