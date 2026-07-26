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

    def sql(self, aliases: dict[type, str]) -> str:
        def render(value: Any) -> str:
            if isinstance(value, (Expression, FieldPath)): return value.sql(aliases)
            if value is None: return "NULL"
            if isinstance(value, str): return "'" + value.replace("'", "''") + "'"
            if isinstance(value, bool): return "TRUE" if value else "FALSE"
            return str(value)
        if self.op == "literal": return render(self.args[0])
        if self.op == "concat": return "concat(" + ", ".join(render(a) for a in self.args) + ")"
        if self.op == "coalesce": return "coalesce(" + ", ".join(render(a) for a in self.args) + ")"
        if self.op == "cast": return "CAST(" + render(self.args[0]) + " AS " + self.args[1] + ")"
        if self.op == "uuid": return "md5(" + render(self.args[0]) + ")"
        if self.op == "expand": return "item"
        raise ValueError(f"Unsupported expression operation: {self.op}")

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

    def sql(self, aliases: dict[type, str]) -> str:
        alias = aliases.get(self.table, self.table.__name__.lower())
        return alias + "." + ".".join('"' + p + '"' for p in self.path)
