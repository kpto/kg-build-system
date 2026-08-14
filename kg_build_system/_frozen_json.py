"""Internal immutable representation of JSON-compatible values."""
from __future__ import annotations

from dataclasses import dataclass


type JsonScalar = str | int | float | bool | None


@dataclass(frozen=True, slots=True)
class FrozenObject:
    items: tuple[tuple[str, "FrozenJson"], ...]


type FrozenJson = JsonScalar | tuple["FrozenJson", ...] | FrozenObject


__all__ = ["FrozenJson", "FrozenObject", "JsonScalar"]
