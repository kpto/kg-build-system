"""Core portable value expressions and typed value references."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Generic, TypeVar

from .._support.annotations import type_shape

T = TypeVar("T")


@dataclass(frozen=True)
class Expression(Generic[T]):
    op: str
    args: tuple[Any, ...]
    type_hint: Any = None
    cardinality: str = "scalar"


@dataclass(frozen=True)
class ValueRef(Generic[T]):
    """A typed value supplied by another declaration layer.

    This deliberately contains no source/table or field-navigation metadata.
    Data-contract declarations may provide specialised references by extending
    it, while expression constructors only depend on this portable shape.
    """

    type_hint: Any = None
    cardinality: str = "scalar"


def item_type(type_hint: Any) -> Any:
    return type_shape(type_hint).item_annotation


__all__ = ["Expression", "ValueRef", "item_type"]
