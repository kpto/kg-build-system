"""Shape derivation for declared and generated row sources."""
from __future__ import annotations

import json
import sys
from collections.abc import Sequence
from hashlib import sha256
from typing import Any, TypeVar, cast

from kg_build_system.distribution.languages.expressions.model.internal import Traversal; from kg_build_system.distribution.languages.expressions.service.internal import field_reference
from kg_build_system.distribution.languages.expressions.service.internal import select_member, wrap_expression
from kg_build_system.kernel.model.public.types import ArrayType, LogicalType, NullableType, Shape, Struct, StructType; from kg_build_system.kernel.service.internal.types import type_from_dto, type_to_document, type_to_dto
from kg_build_system.kernel.model.internal.types.dto import ArrayTypeDTO, CustomTypeDTO, LogicalTypeDTO, NullableTypeDTO, StructTypeDTO, UnitTypeDTO
from ...model.public.fields import Field, FieldMetadata
from ...model.public.shapes import ShapeField


_TYPE_MODULE = "kg_build_system.distribution.languages.table"

S = TypeVar("S", bound=Shape)


def make_shape_context(shape: type[S]) -> S:
    """Return a symbolic shape instance used as an authoring-lambda subject."""
    return object.__new__(shape)


def _base(logical_type: Any) -> Any:
    if isinstance(logical_type, (NullableType, NullableTypeDTO)):
        return logical_type.value
    return logical_type


def _is_nullable(logical_type: Any) -> bool:
    return isinstance(logical_type, (NullableType, NullableTypeDTO))


def _is_dto_type(logical_type: Any) -> bool:
    return isinstance(logical_type, (
        UnitTypeDTO, CustomTypeDTO, StructTypeDTO, ArrayTypeDTO, NullableTypeDTO,
    ))


def _canonical(logical_type: Any) -> LogicalType:
    if _is_dto_type(logical_type):
        return type_from_dto(cast(LogicalTypeDTO, logical_type))
    return cast(LogicalType, logical_type)


def _encode_logical_type(logical_type: Any) -> Any:
    if _is_dto_type(logical_type):
        return type_to_document(logical_type)
    return type_to_document(type_to_dto(cast(LogicalType, logical_type)))


def _nullable_dto(logical_type: Any) -> Any:
    if _is_nullable(logical_type):
        return logical_type
    if _is_dto_type(logical_type):
        return NullableTypeDTO(cast(Any, logical_type))
    return NullableType(cast(Any, logical_type))


def _traversals(name: str, logical_type: Any) -> tuple[Traversal, ...]:
    base = _base(logical_type)
    if isinstance(base, (StructType, StructTypeDTO)):
        return (Traversal("struct", (name,)),)
    if isinstance(base, (ArrayType, ArrayTypeDTO)):
        return (Traversal("array", (name,)),)
    return ()


def _identifier(name: str) -> str:
    if not name.isidentifier() or name.startswith("_"):
        raise ValueError(
            f"generated shape member {name!r} must be a public Python identifier"
        )
    return name


def _shape_signature(fields: Sequence[ShapeField]) -> tuple[tuple[str, Any], ...]:
    return tuple((field.name, field.logical_type) for field in fields)


def _field_digest(fields: Sequence[ShapeField]) -> str:
    return sha256(json.dumps(
        [
            {
                "attribute": field.attribute,
                "name": field.name,
                "logical_type": _encode_logical_type(field.logical_type),
            }
            for field in fields
        ],
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")).hexdigest()


def _register_shape(shape: type[Struct]) -> None:
    """Make a generated record importable from its declaring module."""
    module = sys.modules.get(shape.__module__)
    if module is not None:
        setattr(module, shape.__qualname__, shape)


class _RecordField:
    """One structural member of a generated record shape."""

    __slots__ = ("name", "logical_type")

    def __init__(self, name: str, logical_type: Any) -> None:
        self.name = name
        self.logical_type = logical_type

    def __get__(self, instance: Any, owner: type[Any] | None = None) -> Any:
        if owner is None:
            if instance is None:
                raise TypeError("record fields require a declaration owner")
            owner = type(instance)
        declaration = StructType(owner.__module__, owner.__qualname__)
        return select_member(self.name, self.logical_type, declaration)


def record_shape(fields: Sequence[ShapeField]) -> type[Struct]:
    """A ``Struct`` mirror of a row shape, named from its members."""
    logical = StructType(
        _TYPE_MODULE, f"RowSourceRecord_{_field_digest(fields)[:24]}",
    )
    namespace: dict[str, Any] = {
        "__module__": logical.module,
        "__qualname__": logical.qualname,
    }
    for field in fields:
        namespace[_identifier(field.attribute)] = _RecordField(
            field.name, _canonical(field.logical_type),
        )
    shape = type(logical.qualname, (Struct,), namespace)
    _register_shape(shape)
    return shape


def record_shape_type(fields: Sequence[ShapeField]) -> Any:
    """The struct type identity of a row shape used as a nested record."""
    shape = record_shape(fields)
    if fields and _is_dto_type(fields[0].logical_type):
        return StructTypeDTO(shape.__module__, shape.__qualname__)
    return StructType(shape.__module__, shape.__qualname__)


def make_row_shape(
    source_name: str, fields: Sequence[ShapeField], *, allow_empty: bool = False,
) -> type[Shape]:
    """A generated row shape whose fields read one physical row-source key."""
    if not fields and not allow_empty:
        raise ValueError("row-source shapes require at least one field")
    used: set[str] = set()
    attrs: dict[str, Any] = {
        "_kg_row_source_name": source_name,
        "_projection_name": source_name,
        "_kg_shape_view": True,
        "_kg_row_source_fields": tuple(fields),
    }
    for field in fields:
        attribute = _identifier(field.attribute)
        if attribute in used:
            raise ValueError(f"duplicate generated shape attribute {attribute!r}")
        used.add(attribute)
        logical_type = _canonical(field.logical_type)
        attrs[attribute] = Field(
            wrap_expression(field_reference(
                source=source_name,
                path=(field.name,),
                logical_type=logical_type,
                traversals=_traversals(field.name, logical_type),
            )),
            FieldMetadata(name=field.name, attribute=attribute),
            generated_logical_type=logical_type,
        )
    name = "RowSourceShape_" + sha256(
        (source_name + _field_digest(fields)).encode("utf-8")
    ).hexdigest()[:24]
    return type(name, (Shape,), attrs)


def projection_attrs(shape: type[Shape]) -> dict[str, Any]:
    """Projection-field descriptors for every member of a shape."""
    source_name = shape_source_name(shape)
    attrs: dict[str, Any] = {}
    for field in shape_fields(shape):
        logical_type = _canonical(field.logical_type)
        attrs[field.attribute] = Field(
            wrap_expression(field_reference(
                source=source_name,
                path=(field.name,),
                logical_type=logical_type,
                traversals=_traversals(field.name, logical_type),
            )),
            FieldMetadata(name=field.name, attribute=field.attribute),
            generated_logical_type=logical_type,
        )
    return attrs


def shape_fields(shape: type[Shape]) -> tuple[ShapeField, ...]:
    """The members of a shape, whether declared or generated."""
    recorded = vars(shape).get("_kg_row_source_fields")
    if recorded is not None:
        return cast(tuple[ShapeField, ...], tuple(recorded))
    spec = vars(shape).get("_kg_declaration_spec")
    if spec is not None:
        return tuple(
            ShapeField(
                attribute=item.attribute,
                name=item.name,
                logical_type=item.access_type,
            )
            for item in spec.fields
        )
    fields = vars(shape).get("_fields")
    if fields is not None:
        return tuple(
            ShapeField(
                attribute=attribute,
                name=field.metadata.name or attribute,
                logical_type=field.access_type(shape),
            )
            for attribute, field in fields.items()
        )
    raise TypeError(f"{shape.__name__} is not a row shape with readable fields")


def shape_source_name(shape: type[Shape]) -> str:
    """The expression source the shape's own fields read."""
    recorded = vars(shape).get("_kg_row_source_name")
    if isinstance(recorded, str) and recorded:
        return recorded
    spec = vars(shape).get("_kg_declaration_spec")
    if spec is not None and spec.name and spec.kind in {"table", "projection"}:
        return spec.name
    table_name = getattr(shape, "_table_name", None)
    if isinstance(table_name, str) and table_name:
        return table_name
    projection_name = getattr(shape, "_projection_name", None)
    if isinstance(projection_name, str) and projection_name:
        return projection_name
    raise TypeError(f"{shape.__name__} is not a row shape with a logical source")


def shape_view(source: type[Shape]) -> type[Shape]:
    """A row shape carrying the fields of a declaration under its own name."""
    return make_row_shape(
        shape_source_name(source), shape_fields(source), allow_empty=True,
    )


def union_shape_fields(left: type[Shape], right: type[Shape]) -> tuple[ShapeField, ...]:
    """Validate two union operands and return their shared shape."""
    left_fields = shape_fields(left)
    right_fields = shape_fields(right)
    if _shape_signature(left_fields) != _shape_signature(right_fields):
        raise TypeError("union row sources must have the same shape")
    return left_fields


__all__ = [
    "ShapeField", "make_row_shape", "make_shape_context", "projection_attrs",
    "record_shape", "record_shape_type", "shape_fields", "shape_source_name",
    "shape_view", "union_shape_fields",
]
