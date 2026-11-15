"""Field-construction interface for the data language."""
from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from kg_build_system.distribution.languages.annotations.model.public import (
    Annotation,
)
from ...model.public.fields import DeclaredValue

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
    """Create a source-backed field descriptor; an empty name is rejected."""
    from .._private.descriptors import make_field

    return make_field(
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
    """Create an expression-backed field descriptor."""
    from .._private.descriptors import make_computed_field

    return make_computed_field(
        value, definition=definition, name=name, description=description,
        annotations=annotations, meaning=meaning,
    )


__all__ = ["computed_field", "field"]
