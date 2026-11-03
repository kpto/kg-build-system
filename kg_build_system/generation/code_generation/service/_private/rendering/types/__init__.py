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


def field_annotation(value: GeneratedType, *, nullable: bool = False) -> str:
    """The declared type of a source field.

    A field whose source tier only defaults nullability is a nullable field;
    a required/declared source field is non-null. Array item and nested member
    nullability are carried by the value type itself.
    """
    if type(value) is GeneratedNullableType:
        value = value.value  # type: ignore[union-attr]
    rendered = render_type(value)
    return f"{rendered} | None" if nullable else rendered


__all__ = ["field_annotation", "render_type", "struct_references"]
