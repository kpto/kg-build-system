"""Validation helpers for annotation sequences."""
from __future__ import annotations

from collections.abc import Sequence

from ...model.public.base import Annotation


def annotation_tuple(values: Sequence[Annotation]) -> tuple[Annotation, ...]:
    """Return the values as a tuple, rejecting non-annotation values."""
    result = tuple(values)
    if any(not isinstance(value, Annotation) for value in result):
        raise TypeError("annotations must contain only Annotation values")
    return result


__all__ = ["annotation_tuple"]
