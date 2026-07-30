"""Interpret Python type annotations used by declarations and expressions."""
from __future__ import annotations

from dataclasses import dataclass
from types import UnionType
from typing import Any, get_args, get_origin


@dataclass(frozen=True)
class TypeShape:
    annotation: Any
    nullable: bool
    cardinality: str
    item_annotation: Any | None = None
    item_nullable: bool = False


def _optional(annotation: Any) -> tuple[Any, bool]:
    origin = get_origin(annotation)
    arguments = get_args(annotation)
    if origin in (UnionType,) or str(origin) == "typing.Union":
        non_null = tuple(argument for argument in arguments if argument is not type(None))
        if len(non_null) == 1 and len(non_null) != len(arguments):
            return non_null[0], True
    return annotation, False


def type_shape(annotation: Any, cardinality: str = "scalar") -> TypeShape:
    base, nullable = _optional(annotation)
    origin, arguments = get_origin(base), get_args(base)
    if origin is list:
        item, item_nullable = _optional(arguments[0] if arguments else Any)
        return TypeShape(base, nullable, "scalar" if cardinality == "expanded" else "collection", item, item_nullable)
    return TypeShape(base, nullable, cardinality)


def type_name(annotation: Any) -> str:
    return "unknown" if annotation is Any else getattr(annotation, "__name__", str(annotation))
