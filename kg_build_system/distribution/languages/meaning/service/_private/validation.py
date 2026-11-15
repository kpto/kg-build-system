"""Invariant helpers for the meaning authoring units."""
from __future__ import annotations

from collections.abc import Iterable
from typing import TypeVar

T = TypeVar("T")


def required_text(value: object, subject: str) -> None:
    """Reject a value that is not a non-empty string."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{subject} must be a non-empty string")


def unit_tuple(
    values: Iterable[T], kind: type[T], subject: str,
) -> tuple[T, ...]:
    """Return the values as a tuple, rejecting units of another type."""
    result = tuple(values)
    if any(not isinstance(item, kind) for item in result):
        raise TypeError(f"{subject} must contain only {kind.__name__} values")
    return result


__all__ = ["required_text", "unit_tuple"]
