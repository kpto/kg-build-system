"""Portable value expressions and typed table-field paths."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from ._types import type_shape

T = TypeVar("T")

@dataclass(frozen=True)
class Expression(Generic[T]):
    op: str
    args: tuple[Any, ...]
    type_hint: Any = None
    cardinality: str = "scalar"

def item_type(type_hint: Any) -> Any:
    return type_shape(type_hint).item_annotation

@dataclass(frozen=True)
class FieldPath(Generic[T]):
    table: type
    path: tuple[str, ...]
    type_hint: Any = None
    cardinality: str = "scalar"
    collection_paths: tuple[tuple[str, ...], ...] = ()

    def __getattr__(self, part: str) -> "FieldPath[Any]":
        if part.startswith("_"): raise AttributeError(part)
        item = item_type(self.type_hint)
        if part == "element":
            if item is None: raise AttributeError("element is only available on a collection field path")
            return FieldPath[Any](self.table, self.path, item, "collection", self.collection_paths)
        fields = getattr(item or type_shape(self.type_hint).annotation, "_fields", {})
        if part not in fields: raise AttributeError(f"{self.type_hint!r} has no declared field {part!r}")
        field = fields[part]; path = self.path + (field.name,)
        field_type = field.type_hint | None if type_shape(self.type_hint).nullable and field.type_hint is not Any else field.type_hint
        collection_paths = self.collection_paths + ((path,) if item_type(field_type) is not None else ())
        return FieldPath[Any](self.table, path, field_type, "collection" if collection_paths else "scalar", collection_paths)
