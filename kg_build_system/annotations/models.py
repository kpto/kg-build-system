"""Annotation domain models used by the authoring API."""
from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from typing import ClassVar


@dataclass(frozen=True)
class Annotation:
    """Portable metadata attached to authoring declarations."""

    namespace: ClassVar[str]
    annotation_id: ClassVar[str]


def annotation_tuple(values: Sequence[Annotation]) -> tuple[Annotation, ...]:
    result = tuple(values)
    if any(not isinstance(value, Annotation) for value in result):
        raise TypeError("annotations must contain only Annotation values")
    return result


__all__ = ["Annotation", "annotation_tuple"]
