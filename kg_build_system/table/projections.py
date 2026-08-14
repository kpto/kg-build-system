"""Typed projection-output declarations built on canonical expressions."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any, Generic, TypeVar, overload

from .._support.naming import member_name
from ..annotations import Annotation, annotation_tuple
from ..expressions import (
    FieldReferenceExpression,
    Traversal,
    ValueExpression,
    field_reference,
    walk_expression,
    wrap_expression,
)
from ..types import ArrayType, LogicalType, NullableType, StructType


TExpression = TypeVar("TExpression", bound=ValueExpression[Any])


@dataclass(frozen=True, slots=True)
class ProjectionFieldMetadata:
    name: str | None = None
    description: str | None = None
    annotations: tuple[Annotation, ...] = ()
    attribute: str = ""


def _traversals(name: str, logical_type: LogicalType) -> tuple[Traversal, ...]:
    base = logical_type.value if isinstance(logical_type, NullableType) else logical_type
    if isinstance(base, StructType):
        return (Traversal("struct", (name,)),)
    if isinstance(base, ArrayType):
        return (Traversal("array", (name,)),)
    return ()


class ProjectionField(Generic[TExpression]):
    """A named projection output whose implementation is a typed expression.

    Reading the descriptor through its projection class produces a reference
    to the materialised projection output, not the source implementation.
    The implementation remains available to declaration compilation through
    :attr:`expression`.
    """

    __slots__ = ("_value", "_metadata", "_owner")

    def __init__(
        self,
        value: TExpression,
        metadata: ProjectionFieldMetadata = ProjectionFieldMetadata(),
    ) -> None:
        if not isinstance(value, ValueExpression):
            raise TypeError("projection fields require a typed ValueExpression")
        self._value = value
        self._metadata = metadata
        self._owner: type[Any] | None = None

    @property
    def value(self) -> TExpression:
        return self._value

    @property
    def expression(self):
        return self._value.expression

    @property
    def metadata(self) -> ProjectionFieldMetadata:
        return self._metadata

    def __set_name__(self, owner: type[Any], attribute: str) -> None:
        if self._owner is not None and self._owner is not owner:
            raise TypeError("one ProjectionField may not belong to multiple declarations")
        self._owner = owner
        self._metadata = ProjectionFieldMetadata(
            name=self._metadata.name or member_name(attribute),
            description=self._metadata.description,
            annotations=self._metadata.annotations,
            attribute=attribute,
        )

    @overload
    def __get__(self, instance: None, owner: type[Any]) -> TExpression: ...

    @overload
    def __get__(self, instance: object, owner: type[Any] | None = None) -> TExpression: ...

    def __get__(self, instance: object | None, owner: type[Any] | None = None) -> TExpression:
        if owner is None:
            if instance is None:
                raise TypeError("projection fields require a declaration owner")
            owner = type(instance)
        source = getattr(owner, "_projection_name", None)
        if not isinstance(source, str) or not source:
            raise TypeError("ProjectionField owners must be final Projection declarations")
        name = self._metadata.name
        assert name is not None
        return wrap_expression(field_reference(
            source=source,
            path=(name,),
            logical_type=self.expression.logical_type,
            traversals=_traversals(name, self.expression.logical_type),
        ))  # type: ignore[return-value]


def projection_field[T: ValueExpression[Any]](
    value: T,
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> ProjectionField[T]:
    if name is not None and not name:
        raise ValueError("projection field names must be non-empty")
    return ProjectionField(
        value,
        ProjectionFieldMetadata(
            name=name,
            description=description,
            annotations=annotation_tuple(list(annotations)),
        ),
    )


def declared_projection_fields(owner: type[Any]) -> dict[str, ProjectionField[Any]]:
    """Resolve inherited projection fields with Python shadowing semantics."""
    result: dict[str, ProjectionField[Any]] = {}
    for base in reversed(owner.__mro__):
        for attribute, value in vars(base).items():
            if isinstance(value, ProjectionField):
                result[attribute] = value
            elif attribute in result:
                del result[attribute]
    external: dict[str, str] = {}
    for attribute, value in result.items():
        name = value.metadata.name
        assert name is not None
        if name in external:
            raise TypeError(
                f"{owner.__name__} projection fields {external[name]!r} and "
                f"{attribute!r} share external name {name!r}"
            )
        external[name] = attribute
    return result


def referenced_sources(field: ProjectionField[Any]) -> frozenset[str]:
    return frozenset(
        node.source
        for node in walk_expression(field.expression)
        if isinstance(node, FieldReferenceExpression)
    )


__all__ = [
    "ProjectionField",
    "ProjectionFieldMetadata",
    "declared_projection_fields",
    "projection_field",
    "referenced_sources",
]
