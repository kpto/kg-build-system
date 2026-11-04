"""Normalisation and validation helpers for asset option values.

The authoring dataclasses state their own invariants; these helpers keep the
mapping and string rules identical across them without putting mechanism into
``model.public``.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from types import MappingProxyType

FrozenMapping = Mapping[str, str]


def required_text(value: str, context: str) -> str:
    """Return a required non-empty string."""
    if not isinstance(value, str) or not value:
        raise ValueError(f"{context} must be a non-empty string")
    return value


def optional_text(value: str | None, context: str) -> str | None:
    """Return an optional non-empty string."""
    if value is None:
        return None
    return required_text(value, context)


def text_tuple(
    value: Sequence[str], context: str,
) -> tuple[str, ...]:
    """Return a tuple of non-empty strings."""
    if isinstance(value, (str, bytes, bytearray)):
        raise TypeError(f"{context} must be a sequence of strings")
    result = tuple(value)
    for item in result:
        required_text(item, context)
    return result


def frozen_mapping(value: Mapping[str, str], context: str) -> FrozenMapping:
    """Return a sorted, read-only mapping of non-empty string pairs."""
    if not isinstance(value, Mapping):
        raise TypeError(f"{context} must be a mapping")
    result: dict[str, str] = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key:
            raise ValueError(f"{context} keys must be non-empty strings")
        if not isinstance(item, str) or not item:
            raise ValueError(f"{context} values must be non-empty strings")
        result[key] = item
    return MappingProxyType(dict(sorted(result.items())))


__all__ = [
    "FrozenMapping", "frozen_mapping", "optional_text", "required_text",
    "text_tuple",
]
