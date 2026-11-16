"""Author-facing field declarations for source relations, structs and derived relations.

A field is written as a class attribute: ``field()`` for a source-backed member
and ``computed_field(selection)`` for an expression-backed output. A source
``Field[T]`` reads as ``NullableSelection[T]``; a computed field reads as the
type of its expression.

Example:
    ```python
    from kg_build_system import Field, SourceRelation, field

    class Site(SourceRelation):
        site_id: Field[str] = field()
        names: Field[Array[str]] = field(name="name")
    ```
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, TypeVar, overload

from kg_build_system.distribution.languages.annotations.model.public import (
    Annotation,
)
from kg_build_system.distribution.languages.meaning.model.public import (
    Omitted,
    require_declaration_meaning,
)
from kg_build_system.kernel.model.public.types import (
    Array,
    CustomDataType,
    Date,
    Nullable,
    Struct,
    Time,
    Timestamp,
    Uuid,
)

if TYPE_CHECKING:
    from kg_build_system.distribution.languages.expressions.model.public import (
        Selection,
    )
    from kg_build_system.distribution.languages.meaning.model.public import (
        Meaning,
    )
    from kg_build_system.kernel.model.public.types import LogicalType
    from .declarations import (
        ComputedStruct, DerivedRelation, Stage, Struct as SourceStruct,
        SourceRelation,
    )

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class FieldDefinition:
    """What one field's value, unit and absence mean.

    It carries only what the declaration cannot derive: the value's meaning, the
    unit it is expressed in and the meaning of an absent value. The field name,
    logical type, source and provenance are read from the declaration.

    Example:
        ```python
        from kg_build_system import FieldDefinition

        definition = FieldDefinition(
            value="The site's stable identifier.",
            null_meaning="The register holds no identifier for the site.",
        )
        ```
    """

    value: str
    unit: str | None = None
    null_meaning: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.value, str) or not self.value.strip():
            raise ValueError("field definitions must state what the value means")
        for name, text in (
            ("unit", self.unit),
            ("null_meaning", self.null_meaning),
        ):
            if text is not None and (
                not isinstance(text, str) or not text.strip()
            ):
                raise ValueError(
                    f"field definition {name} must be non-empty text"
                )


# The closed value vocabulary a field may declare. A bound keeps the actual
# subtype (`Address`, `Array[Address]`) instead of promoting it to the bound.
type DeclaredValue = (
    bool | int | float | str
    | Date | Time | Timestamp | Uuid
    | CustomDataType
    | Struct | Array[Any] | Nullable[Any]
)


@dataclass(frozen=True, slots=True)
class FieldMetadata:
    """The name, annotations and meaning declared on one field."""

    name: str | None = None
    annotations: tuple[Annotation, ...] = ()
    attribute: str = ""
    meaning: Meaning | type[Omitted] = Omitted
    definition: FieldDefinition | None = None

    def __post_init__(self) -> None:
        require_declaration_meaning(self.meaning)


class Field[T: DeclaredValue]:
    """One field class with source and computed backings.

    The descriptor overloads are keyed on the owner shape, never on a nullable
    annotation. ``T`` is bounded by the canonical value roots, so
    ``Field[str | None]`` and ``Field[SomeSourceRelation]`` are rejected.

    Example:
        ```python
        from kg_build_system import Field, SourceRelation, field

        class Site(SourceRelation):
            site_id: Field[str] = field()
        ```
    """

    __slots__ = (
        "_expression", "_generated_logical_type", "_metadata", "_owner",
    )

    def __init__(
        self,
        expression: Any | None = None,
        metadata: FieldMetadata = FieldMetadata(),
        *,
        generated_logical_type: "LogicalType | None" = None,
    ) -> None:
        self._expression = expression
        self._metadata = metadata
        self._owner: type[Any] | None = None
        self._generated_logical_type = generated_logical_type

    @property
    def expression(self) -> Any | None:
        """The private implementation of a computed field; source fields have none."""
        return self._expression

    @property
    def metadata(self) -> FieldMetadata:
        """The name and annotations declared on this field."""
        return self._metadata

    def __set_name__(self, owner: type[Any], attribute: str) -> None:
        from ...service._private.descriptors import field_set_name

        field_set_name(self, owner, attribute)

    def access_type(self, owner: type[Any]) -> "LogicalType":
        """The type one read yields for ``owner``.

        Example:
            ```python
            from kg_build_system import Field, SourceRelation, field
            class Row(SourceRelation):
                text: Field[str] = field()
            Row.__dict__["text"].access_type(Row)
            ```
        """
        from ...service._private.descriptors import field_access_type

        return field_access_type(self, owner)

    @overload
    def __get__(
        self, instance: None, owner: type["SourceRelation"] | type["SourceStruct"],
    ) -> "Selection[Nullable[T]]": ...
    @overload
    def __get__(
        self, instance: None,
        owner: type["DerivedRelation"] | type["Stage"] | type["ComputedStruct"],
    ) -> "Selection[T]": ...
    @overload
    def __get__(
        self, instance: "SourceRelation | SourceStruct", owner: type[Any],
    ) -> "Selection[Nullable[T]]": ...
    @overload
    def __get__(
        self, instance: "DerivedRelation | Stage | ComputedStruct", owner: type[Any],
    ) -> "Selection[T]": ...
    def __get__(self, instance: Any, owner: type[Any] | None = None) -> Any:
        from ...service._private.descriptors import field_get

        return field_get(self, instance, owner)


# The private machinery and older service code refer to the descriptor base by
# name; the single class is the base.
FieldDescriptor = Field


__all__ = [
    "DeclaredValue", "Field", "FieldDefinition", "FieldDescriptor",
    "FieldMetadata",
]
