"""Authoring function wrappers for relation fields."""
from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from kg_build_system.distribution.languages.annotations.model.public import (
    Annotation,
)
from ...model.public.fields import DeclaredValue
from ..internal.fields import computed_field as computed_field_impl
from ..internal.fields import field as field_impl

if TYPE_CHECKING:
    from kg_build_system.distribution.languages.expressions.model.public import Selection
    from kg_build_system.distribution.languages.meaning.model.public import (
        Meaning,
    )
    from ...model.public.fields import Field, FieldDefinition


def field[T: DeclaredValue](  # pyright: ignore[reportInvalidTypeVarUse]
    *,
    definition: FieldDefinition | None = None,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
    meaning: Meaning | None = None,
) -> "Field[T]":  # pyright: ignore[reportInvalidTypeVarUse]
    """Declare a source-backed field: a source relation column or source struct member.

    Example:
        ```python
        from kg_build_system import Field, SourceRelation, field

        class Site(SourceRelation):
            site_id: Field[str] = field()
        ```
    """
    return field_impl(
        definition=definition, name=name, description=description,
        annotations=annotations, meaning=meaning,
    )


def computed_field[T: DeclaredValue](
    value: "Selection[T]",
    *,
    definition: FieldDefinition | None = None,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
    meaning: Meaning | None = None,
) -> "Field[T]":
    """Declare an expression-backed field: an output or computed member.

    Example:
        ```python
        from kg_build_system import DerivedRelation, computed_field

        class SiteLabels(DerivedRelation(SiteTable.row_source())):
            label = computed_field(SiteTable.name.alter_rows().drop_null())
        ```
    """
    return computed_field_impl(
        value, definition=definition, name=name, description=description,
        annotations=annotations, meaning=meaning,
    )


__all__ = ["computed_field", "field"]
