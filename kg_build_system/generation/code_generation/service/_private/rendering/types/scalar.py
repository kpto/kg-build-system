"""One renderer for generated scalar annotations."""
from __future__ import annotations

from collections.abc import Callable

from .....model._private.generated import GeneratedScalarType, GeneratedType
from ..constants import REPRESENTATIVE_TYPES


def render(value: GeneratedScalarType, _render: Callable[[GeneratedType], str]) -> str:
    return REPRESENTATIVE_TYPES.get(value.name, value.name)


def references(
    _value: GeneratedScalarType,
    _collect: Callable[[GeneratedType], tuple[object, ...]],
) -> tuple[object, ...]:
    return ()


__all__ = ["references", "render"]
