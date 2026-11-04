"""Field-construction interface for the data language."""
from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING, TypeVar

from kg_build_system.distribution.languages.annotations.model.public import (
    Annotation,
)
from kg_build_system.distribution.languages.expressions.model.public import (
    ValueInput,
)
from ...model.public.fields import AuthoringDataType

if TYPE_CHECKING:
    from ...model.public.fields import Field

T = TypeVar("T")


def field[T: AuthoringDataType](  # pyright: ignore[reportInvalidTypeVarUse]
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> "Field[T]":  # pyright: ignore[reportInvalidTypeVarUse]
    """Create a source-backed field descriptor; an empty name is rejected."""
    from .._private.descriptors import make_field

    return make_field(
        name=name, description=description, annotations=annotations,
    )


def computed_field[T](  # pyright: ignore[reportInvalidTypeVarUse]
    value: ValueInput[T],
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> "Field[T]":
    """Create an expression-backed field descriptor."""
    from .._private.descriptors import make_computed_field

    return make_computed_field(
        value, name=name, description=description, annotations=annotations,
    )


def projection_field[T](  # pyright: ignore[reportInvalidTypeVarUse]
    value: ValueInput[T],
    *,
    name: str | None = None,
    description: str | None = None,
    annotations: Sequence[Annotation] = (),
) -> "Field[T]":
    """Create the old-projection spelling of an expression-backed field."""
    from .._private.descriptors import make_projection_field

    return make_projection_field(
        value, name=name, description=description, annotations=annotations,
    )


__all__ = ["computed_field", "field", "projection_field"]
