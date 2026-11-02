"""One renderer for generated array annotations."""
from __future__ import annotations

from collections.abc import Callable

from ...ir import GeneratedArrayType, GeneratedType


def render(value: GeneratedArrayType, render_type: Callable[[GeneratedType], str]) -> str:
    return f"Array[{render_type(value.item)}]"


def references(
    value: GeneratedArrayType,
    collect: Callable[[GeneratedType], tuple[object, ...]],
) -> tuple[object, ...]:
    return collect(value.item)


__all__ = ["references", "render"]
