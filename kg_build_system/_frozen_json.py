"""Immutable representation of JSON-compatible values."""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any


type JsonScalar = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class FrozenObject:
    items: tuple[tuple[str, "FrozenJson"], ...]


type FrozenJson = JsonScalar | tuple["FrozenJson", ...] | FrozenObject


def freeze_json(value: Any) -> FrozenJson:
    if isinstance(value, FrozenObject):
        return value
    if value is None or type(value) in {str, int, float, bool}:
        return value
    if isinstance(value, Mapping):
        items = tuple(sorted(
            ((str(key), freeze_json(item)) for key, item in value.items()),
            key=lambda item: item[0],
        ))
        return FrozenObject(items)
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return tuple(freeze_json(item) for item in value)
    raise TypeError(f"value must be JSON-compatible, not {value!r}")


def thaw_json(value: FrozenJson) -> Any:
    if isinstance(value, FrozenObject):
        return {key: thaw_json(item) for key, item in value.items}
    if isinstance(value, tuple):
        return [thaw_json(item) for item in value]
    return value


__all__ = [
    "FrozenJson", "FrozenObject", "JsonScalar", "freeze_json", "thaw_json",
]
