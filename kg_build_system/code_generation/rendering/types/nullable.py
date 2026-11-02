"""One renderer for generated nullable annotations."""
from __future__ import annotations

from collections.abc import Callable

from ...ir import GeneratedNullableType, GeneratedType


def render(value: GeneratedNullableType, render_type: Callable[[GeneratedType], str]) -> str:
    return f"{render_type(value.value)} | None"


def references(
    value: GeneratedNullableType,
    collect: Callable[[GeneratedType], tuple[object, ...]],
) -> tuple[object, ...]:
    return collect(value.value)


__all__ = ["references", "render"]
