"""Registry of generated-type renderers keyed by exact type, not an isinstance chain."""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from .....model._private.generated import (
    GeneratedArrayType, GeneratedNullableType, GeneratedScalarType,
    GeneratedStructType, GeneratedType,
)

from . import array, nullable, scalar, struct

Renderer = Callable[[Any, Callable[[GeneratedType], str]], str]
ReferenceCollector = Callable[[Any, Callable[[GeneratedType], tuple[object, ...]]], tuple[object, ...]]

_RENDERERS: dict[type[object], Renderer] = {
    GeneratedScalarType: scalar.render,
    GeneratedStructType: struct.render,
    GeneratedArrayType: array.render,
    GeneratedNullableType: nullable.render,
}

_REFERENCE_COLLECTORS: dict[type[object], ReferenceCollector] = {
    GeneratedScalarType: scalar.references,
    GeneratedStructType: struct.references,
    GeneratedArrayType: array.references,
    GeneratedNullableType: nullable.references,
}


def render_type(value: GeneratedType) -> str:
    """Render one normalized value type as its Python annotation."""
    renderer = _RENDERERS.get(type(value))
    if renderer is None:
        raise TypeError(f"unsupported generated type {value!r}")
    return renderer(value, render_type)


def struct_references(value: GeneratedType) -> tuple[GeneratedStructType, ...]:
    """Collect every struct reference carried by one value type."""
    collector = _REFERENCE_COLLECTORS.get(type(value))
    if collector is None:
        raise TypeError(f"unsupported generated type {value!r}")
    return collector(value, struct_references)  # type: ignore[return-value]


def field_annotation(value: GeneratedType) -> str:
    """The declared value type of a generated field.

    A source field's observed nullability is provenance, not part of the value
    type, so the annotation is the value type alone. Nullability that belongs
    to the value — an array item or an explicitly nullable computed result — is
    carried by ``GeneratedNullableType`` inside the value.
    """
    return render_type(value)


__all__ = ["field_annotation", "render_type", "struct_references"]
