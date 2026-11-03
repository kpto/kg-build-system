"""One renderer for generated struct references."""
from __future__ import annotations

from collections.abc import Callable

from .....model._private.generated import GeneratedStructType, GeneratedType


def render(value: GeneratedStructType, _render: Callable[[GeneratedType], str]) -> str:
    return value.declaration_name


def references(
    value: GeneratedStructType,
    _collect: Callable[[GeneratedType], tuple[object, ...]],
) -> tuple[object, ...]:
    return (value,)


__all__ = ["references", "render"]
