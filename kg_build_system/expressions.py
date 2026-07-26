"""Portable expression IR, including type and cardinality metadata."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar, get_args, get_origin

T = TypeVar("T")

def item_type(type_hint: Any) -> Any:
    """Return the element type for list[T], otherwise None."""
    origin = get_origin(type_hint)
    return get_args(type_hint)[0] if origin is list and get_args(type_hint) else None

@dataclass(frozen=True)
class Expression(Generic[T]):
    op: str
    args: tuple[Any, ...]
    type_hint: Any = None
    cardinality: str = "scalar"


@dataclass(frozen=True)
class FieldPath(Generic[T]):
    table: type
    path: tuple[str, ...]
    type_hint: Any = None
    cardinality: str = "scalar"

    def __getattr__(self, part: str) -> "FieldPath[Any]":
        if part.startswith("_"): raise AttributeError(part)
        fields = getattr(self.type_hint, "_fields", {})
        if part not in fields:
            raise AttributeError(f"{self.type_hint!r} has no declared field {part!r}")
        field = fields[part]
        return FieldPath[Any](self.table, self.path + (field.name,), field.type_hint)
