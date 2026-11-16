"""Field-construction interface for the data language."""
from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, Any, overload

from kg_build_system.distribution.languages.annotations.model.public import (
    Annotation,
)
from ...model.public.fields import DeclaredValue

if TYPE_CHECKING:
    from kg_build_system.distribution.languages.expressions.model.public import Selection
    from kg_build_system.distribution.languages.meaning.model.public import (
        Meaning,
        Omitted,
    )
    from kg_build_system.kernel.model.public.types import Nullable
    from ...model.public.fields import (
        Field, FieldDefinition, NullableComputedField,
    )


def field[T: DeclaredValue](  # pyright: ignore[reportInvalidTypeVarUse]
    *,
    definition: FieldDefinition | None = None,
    name: str | None = None,
    annotations: Sequence[Annotation] = (),
    meaning: Meaning | type[Omitted],
) -> "Field[T]":  # pyright: ignore[reportInvalidTypeVarUse]
    """Create a source-backed field descriptor; an empty name is rejected."""
    from .._private.descriptors import make_field

    return make_field(
        definition=definition, name=name,
        annotations=annotations, meaning=meaning,
    )


@overload
def computed_field[T: DeclaredValue](
    value: "Selection[T]",
    *,
    definition: FieldDefinition | None = None,
    name: str | None = None,
    annotations: Sequence[Annotation] = (),
    meaning: Meaning | type[Omitted],
) -> "Field[T]": ...
@overload
def computed_field[T: DeclaredValue](
    value: "Selection[Nullable[T]]",
    *,
    definition: FieldDefinition | None = None,
    name: str | None = None,
    annotations: Sequence[Annotation] = (),
    meaning: Meaning | type[Omitted],
) -> "NullableComputedField[T]": ...
def computed_field(
    value: "Selection[DeclaredValue | None]",
    *,
    definition: FieldDefinition | None = None,
    name: str | None = None,
    annotations: Sequence[Annotation] = (),
    meaning: Meaning | type[Omitted],
) -> "Field[DeclaredValue] | NullableComputedField[DeclaredValue]":
    """Create an expression-backed field descriptor."""
    from .._private.descriptors import make_computed_field

    return make_computed_field(
        value, definition=definition, name=name,
        annotations=annotations, meaning=meaning,
    )


__all__ = ["computed_field", "field"]
